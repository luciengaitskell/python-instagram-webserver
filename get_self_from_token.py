from flask import Flask, request, redirect
import instagram

app = Flask(__name__)
client = instagram.Client()


@app.route("/")
def hello():
    return """Click <a href="/token">here</a> for Instagram API"""


@app.route("/token")
def token_form():
    return """
<form action="/submit" method="post">
    Instagram API Token:<br>
    <input type="text" name="token" value="token"><br>
    <input type="submit" value="Submit">
</form>"""


@app.route("/submit", methods=['POST'])
def form_submit():
    token = str(request.form['token'])
    if token == "token":
        return redirect("/token", code=400)
    else:
        user = client.loop.run_until_complete(client.add_user(token=token))
        print(client.users)
        return str(client.loop.run_until_complete(user.get_self()))


if __name__ == "__main__":
    try:
        app.run()
    finally:
        client.loop.run_until_complete(client.close())
