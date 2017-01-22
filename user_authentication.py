import os
from flask import Flask, request, redirect
import instagram

client_id = os.environ['INSTAGRAM_CLIENT_ID']
client_secret = os.environ['INSTAGRAM_CLIENT_SECRET']
redirect_uri = os.environ['INSTAGRAM_REDIRECT_URI']

scopes = ['public_content', 'follower_list', 'basic', 'comments', 'likes']
scope_string = "+".join(scopes)

authentication_url = ('https://api.instagram.com/oauth/authorize/?client_id='
                      + client_id + '&redirect_uri=' + redirect_uri
                      + '&response_type=code&scope=' + scope_string)

app = Flask(__name__)
client = instagram.Client(client_id=client_id, client_secret=client_secret,
                          redirect_uri=redirect_uri)


@app.route("/")
def hello():
    return ('Click <a href="' + authentication_url + '">here</a> for Instagram'
            + ' authentication.')


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

    self_data = client.loop.run_until_complete(user.get_self())
    profile_picture_url = self_data['profile_picture']
    username = self_data['username']
    return ('<img src="' + profile_picture_url
            + '" alt="' + username + '">')


if __name__ == "__main__":
    try:
        app.run()
    finally:
        client.loop.run_until_complete(client.close())
