from flask import Flask, request, jsonify
from flask import render_template
from morning_message import main
from form_submit import form_submit

app = Flask(__name__)

@app.route("/")
def hello_world():
    return render_template("index.html")


@app.route('/tally_form_submit', methods=['POST'])
def post_route():
    # Get JSON data from the request
    data = request.get_json()
    return form_submit(data)

@app.route("/morning_message")
def morning_message():
    return main({})
