from flask import Flask, send_file

app = Flask(__name__)


@app.route("/flag")
def serve_flag():
    try:
        flag = open("/home/ctf-user/flag.txt", "r").read()
        return flag
    except Exception as e:
        return str(e), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
