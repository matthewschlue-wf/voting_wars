from flask import Flask, render_template, request, current_app
import logging
import gevent.wsgi
import json

from vote import queue, redis_handler
from vote.signals import app_start

app = Flask(__name__)

TEAMS_COMPETING = []


def init_app(app):
    """
    Initialize the rabbitmq extension.
    """
    rabbit_queue = queue.Queue()
    r_handler = redis_handler.RedisHandler()

    app.extensions['rabbit_queue'] = rabbit_queue
    app.extensions['r_handler'] = r_handler


# Template for starting multiple extensions.
@app_start.connect
def start_producers(app, **kwargs):
    producers = [
        app.extensions.get('rabbit_queue'),
        app.extensions.get('r_handler')
    ]

    for producer in producers:
        if producer:
            producer.start()


@app.route('/', methods=['GET', 'POST'])
def place_vote():
    """
    Main page,
    :return: rendering a page with the status message of the vote for POST
    :return: rendering the default voting wars page for GET requests
    """
    if request.method == 'POST':
        team = request.form['vote']

        # Post a message with the team being voted for.
        message = json.dumps({'team': team})
        current_app.extensions['rabbit_queue'].queue_message(message)

        # Rendering the output for index.
        return render_template(
            'index.html',
            last_vote=team,
            teams_competing=TEAMS_COMPETING
        )

    else:
        return render_template('index.html',
            teams_competing=TEAMS_COMPETING)


@app.route('/votes')
def votes():
    """
    app route to show the results of voting

    :return: rendered template of the voting results
    """
    vote_total = {}
    for team in TEAMS_COMPETING:
        team = 'team{}'.format(team)
        vote_total[team] = current_app.extensions['r_handler'].get_key(team)

    return render_template('results.html', team_votes_total=vote_total)


def create_teams():
    """
    Helper method to create teams.
    """
    for x in range(1, 15):
        TEAMS_COMPETING.append('{}'.format(x))


def run_app(app):
    init_app(app)
    app_start.send(app)

    try:
        logging.warning('starting the web service')
        ws = gevent.wsgi.WSGIServer(('0.0.0.0', int(5000)), app)
        ws.serve_forever()

    finally:
        logging.info('change this later')

def main():
    app.debug = True
    create_teams()
    run_app(app)
