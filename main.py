from flask import Flask, request, redirect, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
import os
import random
import time
import configparser


app = Flask(__name__)


confparser = configparser.ConfigParser()
confparser.read("creds.ini")
section = confparser["creds"]
user, pw, host, db = section.get("user"), section.get("pw"), section.get("host"), section.get("db")
connect_string = "mysql+pymysql://{}:{}@{}/{}".format(user, pw, host, db)
app.config["SQLALCHEMY_DATABASE_URI"] = connect_string
db = SQLAlchemy(app)

vote_table = db.Table("votes",
                      db.Column("image_name", db.Text),
                      db.Column("vote_count", db.Text))


@app.route("/")
def index():
    return redirect("static/index.html")


@app.route("/randomspuds/<int:samp_size>")
def random_spuds(samp_size):
    random.seed(time.time())
    file_list = [f for f in os.listdir("static/fixedpics")
                 if f.endswith("jpg")]

    samps = random.sample(file_list, samp_size)
    return jsonify({"results": samps})


def __votes_on_pic(pic_name):
    query = db.select([vote_table])
    query = query.where(vote_table.c.image_name == pic_name)
    conn = db.get_engine(app).connect()
    result_set = conn.execute(query)
    data = result_set.fetchall()
    if len(data) == 0:
        vote_count = 0
    else:
        _, vote_count = data[0]
    return vote_count


@app.route("/votes/<pic_name>", methods=["GET"])
def votes_on_pic(pic_name):
    vote_count = __votes_on_pic(pic_name)
    return jsonify({"pic_id": pic_name, "votes": vote_count})


@app.route("/vote", methods=["POST"])
def do_vote():

    # Find out what the previous vote count was and add one
    pic_name = request.get_json().get("pic_name")
    votes = __votes_on_pic(pic_name)
    votes += 1

    # If the vote count is 1, this is a new record and should be put in as an insert.  Otherwise do an update query
    eng = db.get_engine(app)
    eng.echo = True
    conn = eng.connect()
    if votes == 1:
        query = vote_table.insert()
        query = query.values(image_name=pic_name, vote_count=votes)
    else:
        query = vote_table.update().where(vote_table.c.image_name == pic_name).values(vote_count=votes)

    conn.execute(query)
    return jsonify({"flask_message": "vote received for {}".format(pic_name)})


if __name__ == '__main__':
    app.run(debug=True)
