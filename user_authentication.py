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
    user = client.loop.run_until_complete(client.add_user(
            code=code))
    return str(client.loop.run_until_complete(user.get_self()))


if __name__ == "__main__":
    try:
        app.run()
    finally:
        client.loop.run_until_complete(client.close())
