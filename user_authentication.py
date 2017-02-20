import os
from flask import Flask, request, redirect, session, url_for
import instagram
import threading
import time
from datetime import datetime, timedelta


client_id = os.environ['INSTAGRAM_CLIENT_ID']
client_secret = os.environ['INSTAGRAM_CLIENT_SECRET']
redirect_uri = os.environ['INSTAGRAM_REDIRECT_URI']

scopes = ['public_content', 'follower_list', 'basic', 'comments', 'likes']
scope_string = "+".join(scopes)

authentication_url = ('https://api.instagram.com/oauth/authorize/?client_id='
                      + client_id + '&redirect_uri=' + redirect_uri
                      + '&response_type=code&scope=' + scope_string)

app = Flask(__name__)
app.secret_key = os.environ['INSTAGRAM_WEBSERVER_SECRET_KEY']

client = instagram.Client(client_id=client_id, client_secret=client_secret,
                          redirect_uri=redirect_uri)


battle_update_wait = 5  # * 60  # 5 Minutes
battle_length = 10  # * 60  # 5 Minutes
current_battles = []
old_battles = []
battle_outcomes = {}

workers_running = True


def battle_worker():
    def update_user_outcome_count(user_id, new_wins, new_losses, new_ties):
        if not (user_id in battle_outcomes):
            battle_outcomes[str(user_id)] = {'wins': 0, 'losses': 0, 'ties': 0}

        battle_outcomes[str(user_id)]['wins'] += new_wins
        battle_outcomes[str(user_id)]['losses'] += new_losses
        battle_outcomes[str(user_id)]['ties'] += new_ties

    while workers_running:
        for index,btl in enumerate(current_battles[:]):
            user = btl['original_user']
            current_time = time.time()

            # Battle Archive:
            if current_time - btl['start_time'] > battle_length:
                print("ARCHIVED!")
                if btl['original_photo']['likes'] > btl['second_photo']['likes']:
                    update_user_outcome_count(btl['original_user']._id, 1, 0, 0)
                    update_user_outcome_count(btl['second_user_info']['id'], 0, 1, 0)
                elif btl['second_photo']['likes'] > btl['original_photo']['likes']:
                    update_user_outcome_count(btl['second_user_info']['id'], 1, 0, 0)
                    update_user_outcome_count(btl['original_user']._id, 0, 1, 0)
                else:
                    update_user_outcome_count(btl['original_user']._id, 0, 0, 1)
                    update_user_outcome_count(btl['second_user_info']['id'], 0, 0, 1)

                print(battle_outcomes)
                old_battles.append(btl)
                del current_battles[index]

            # like_update:
            elif current_time -btl['last_update_time'] > battle_update_wait:
                print("Update likes")
                btl['original_photo']['likes'] = client.loop.run_until_complete(user.get_likes(btl['original_photo']['id']))

                btl['second_photo']['likes'] = client.loop.run_until_complete(user.get_likes(btl['second_photo']['id']))
                btl['last_update_time'] = current_time

        time.sleep(1)


@app.route("/")
def hello():
    return ('Click <a href="' + authentication_url + '">here</a> for Instagram'
            + ' authentication [login].')


@app.route("/login/callback/")
def login_callback():
    code = str(request.args['code'])
    print("Code: " + code)
    try:
        user = client.loop.run_until_complete(client.get_user(code=code))
    except instagram.HTTPException as e:
        if e.code == 400:  # If login error:
            return "Login Error: Invalid code."
        else:  # Raise if other error:
            raise e

    session['user'] = user.client.token
    return redirect('/user/', code=307)


@app.route("/user/")
def user_main():
    return_html = """<a href=\"/user/profile_picture\">Profile Picture</a>
    </br>
    <a href=\"/user/media/recent\">Recent Media</a>
    </br></br> </hr>
    """

    user = client.loop.run_until_complete(client.get_user(token=session['user']))

    # Add wins and losses:
    if user._id in battle_outcomes:
        outcomes = battle_outcomes[user._id]
        return_html += "{} wins, {} losses, {} ties".format(outcomes['wins'], outcomes['losses'], outcomes['ties'])

    # Add current battles:
    for btl in current_battles:
        first_user = btl['original_user']
        second_user_info = btl['second_user_info']

        if user._id == first_user._id or user._id == second_user_info['id']:
            return_html += "<hr>"
            return_html += "<img src=\"" + str(btl['original_photo']['url']) + "\"></img>"
            return_html += "<img src=\"" + str(btl['second_photo']['url']) + "\"></img></br>"
            return_html += (str(len(btl['original_photo']['likes'])) + " likes vs "
                            + str(len(btl['second_photo']['likes'])) + " likes")

            time_left = datetime(1, 1, 1) + timedelta(seconds=int(battle_length -(time.time() - btl['start_time'])))
            return_html += ("</br> {} days, {} hours, {} minutes, and {} seconds left</br>"
                            .format(time_left.day-1, time_left.hour, time_left.minute, time_left.second))

    return return_html


@app.route("/user/profile_picture/")
def display_profile_picture():
    user = client.loop.run_until_complete(
            client.get_user(token=session['user']))
    self_data = client.loop.run_until_complete(user.get_self())
    profile_picture_url = self_data['profile_picture']
    username = self_data['username']
    return ('<img src="' + profile_picture_url
            + '" alt="' + username + '">')


@app.route("/user/media/recent/")
def display_recent_media():
    user = client.loop.run_until_complete(client.get_user(token=session['user']))
    self_media = client.loop.run_until_complete(user.get_self_recent_media())

    return_html = "<h1>Choose one of your photos!</h1>"
    for mda in self_media:
        return_html += ("<a href=\"/user/media/" + mda['id'] + "/\"><img src=\""
                        + mda['images']['standard_resolution']['url'] + "\"></img></br></a>")

    return str(return_html)


@app.route("/user/media/pictobattle/<media_id>/")
def show_users_for_pictobattle(media_id):
    user = client.loop.run_until_complete(client.get_user(token=session['user']))

    followers = client.loop.run_until_complete(user.get_self_followed_by())
    print(followers)
    follows = client.loop.run_until_complete(user.get_self_follows())
    print(follows)

    both_users = [i for i in followers for j in follows if i['id']==j['id']]

    return_html = "<h1>Select a user!</h1>"
    for usr in both_users:
        return_html += ("<a href=\"/user/media/pictobattle/" + media_id + "/" + usr['id'] + "/\"><img src=\""
                        + usr['profile_picture'] + "\"></img></br>" + usr['username'] + "</br></br></a>")

    return return_html


@app.route("/user/media/pictobattle/<media_id>/<user_id>/")
def select_user_media_for_pictobattle(media_id, user_id):
    user = client.loop.run_until_complete(client.get_user(token=session['user']))

    other_user_media = client.loop.run_until_complete(user.get_user_recent_media(user_id))
    print(other_user_media)

    return_html = "<h1>Select one of their photos!</h1>"
    for mda in other_user_media:
        return_html += ("<a href=\"/user/media/pictobattle/" + media_id + "/" + user_id + "/" + mda['id']
                        + "/\"><img src=\"" + mda['images']['standard_resolution']['url'] + "\"></img></br></a>")

    return str(return_html)


@app.route("/user/media/pictobattle/<media_id>/<user_id>/<user_media_id>/", methods=['GET', 'POST'])
def final_pictobattle_confirm(media_id, user_id, user_media_id):
    user = client.loop.run_until_complete(client.get_user(token=session['user']))

    original_mda = client.loop.run_until_complete(user.get_media(media_id=media_id))
    other_user_mda = client.loop.run_until_complete(user.get_media(media_id=user_media_id))
    print(other_user_mda)

    return_html = ""
    if request.method == 'GET':
        if 'videos' in other_user_mda:
            video_link = other_user_mda['videos']['standard_resolution']['url']
            return_html += ("<video width=\"320\" height=\"240\" controls><source src=\"" + video_link
                            + "\" type=\"video/mp4\"></video>")
            return_html += "</br></br><strong>You can't battle videos</strong>"
        else:
            image_link = other_user_mda['images']['standard_resolution']['url']
            return_html += ("<img src=\"" + image_link + "\"></img></br>")
            return_html += ("<form action=\"" + request.url + "\" method=\"POST\">"
                            + "<input type=\"submit\" value=\"Finish!\"></form>")
    elif request.method == 'POST':
        current_time = time.time()
        new_battle = dict()
        new_battle['original_user'] = user
        new_battle['original_photo'] = {}
        new_battle['original_photo']['id'] = media_id
        new_battle['original_photo']['likes'] = client.loop.run_until_complete(user.get_likes(media_id))
        new_battle['original_photo']['url'] = original_mda['images']['standard_resolution']['url']
        new_battle['second_user_info'] = other_user_mda['user']
        new_battle['second_photo'] = {}
        new_battle['second_photo']['id'] = user_media_id
        new_battle['second_photo']['likes'] = client.loop.run_until_complete(user.get_likes(user_media_id))
        new_battle['second_photo']['url'] = other_user_mda['images']['standard_resolution']['url']
        new_battle['last_update_time'] = current_time
        new_battle['start_time'] = current_time
        current_battles.append(new_battle)
        print("Started!")
        return redirect(url_for('user_main'))

    return str(return_html)


@app.route("/user/media/<media_id>/")
def display_media_id(media_id):
    user = client.loop.run_until_complete(client.get_user(token=session['user']))
    self_media = client.loop.run_until_complete(user.get_media(media_id=media_id))

    return_html = "<h1>Here's the "
    if 'videos' in self_media:
        return_html += "video!</h1>"
        video_link = self_media['videos']['standard_resolution']['url']
        return_html += ("<video width=\"320\" height=\"240\" controls><source src=\"" + video_link
                        + "\" type=\"video/mp4\"></video>")
        return_html += "</br></br><strong>You can't battle videos</strong>"
    else:
        return_html += "image!</h1>"
        image_link = self_media['images']['standard_resolution']['url']
        return_html += ("<img src=\"" + image_link + "\"></img></br>")
        return_html += "</br></br><a href=\"/user/media/pictobattle/" + self_media['id'] + "/\">Start a battle!</a>"

    return str(return_html)


if __name__ == "__main__":
    try:
        battle_thread = threading.Thread(target=battle_worker)
        battle_thread.start()
        app.run()
    finally:
        client.loop.run_until_complete(client.close())
        workers_running = False
