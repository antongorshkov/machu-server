from flask import Flask
from flask import render_template
from morning_message import main

app = Flask(__name__)

@app.route("/")
def hello_world():
    return render_template("index.html")

@app.route("/morning_message")
def morning_message():
    return main({})
