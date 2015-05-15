from flask import Flask, request, redirect, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
import os
import random
import time
import configparser


app = Flask(__name__)

##################################
# Setup of database configuration#
##################################
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
    """
    Sends the user to the main page to start picking favorite spuds
    :return: a redirect to the spud picking page.
    """
    return redirect("static/index.html")


@app.route("/randomspuds/<int:samp_size>")
def random_spuds(samp_size):
    """
    Choose some random spud pictures from out of the fixedpics directory.
    :param samp_size: How many pictures you want to randomly choose.
    :return: The names of the sample pictures
    """
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
    """
    Find out how many votes a given picture has gotten
    :param pic_name: The name of the picture to inquire about
    :return: info on the name of the pic and the number of votes it got.
    """
    vote_count = __votes_on_pic(pic_name)
    return jsonify({"pic_id": pic_name, "votes": vote_count})


@app.route("/vote", methods=["POST"])
def do_vote():
    """
    Handle casting of a vote for a spud picture
    Expects a 'pic_name' to be passed in by json format.
    :return: A message confirming receipt of the vote.
    """

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


@app.route("/rankings", methods=["GET"])
def rankings():
    """
    Get a ranking list of the spud pictures and how many votes they each received.
    :return: Ranking list or pics with respective votes listed from most popular to least.
    """

    ranking_list = db.get_engine(app).connect().execute(db.select([vote_table])).fetchall()
    reverse_rank_list = sorted(ranking_list, key=lambda tup: list(tup)[1], reverse=True)
    reverse_rank_list = [{"pic": pic, "votes": votes} for pic, votes in reverse_rank_list]
    return jsonify({"results": reverse_rank_list})

if __name__ == '__main__':
    app.run(debug=True)
