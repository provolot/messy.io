from slackbot.bot import respond_to
from slackbot.bot import listen_to
from slackbot.bot import idle
import slackbot_settings
import re
import time
from lib.singleton import Messybot
import lib.phrases as phrases
DEGREE_SYMBOL = u"\u00b0" 

messybot = Messybot()

def people_num_to_text(n):
    if n < 0:
        return ""
    if n == 0:
        return "Nobody"
    if n == 1:
        return "1 person"
    return str(n) + " people"

def start_vote(client):
    global current_vote_message

    current_temp = messybot.isyclient.current_temp()
    heatpoint = messybot.isyclient.heatpoint

    m = "*VOTING TIME!*\n" 
    m += "Hey @channel! It's *" + str(current_temp) + DEGREE_SYMBOL + "F* on the third floor right now. \n"
    m += "It's supposed to be at " + str(heatpoint) + DEGREE_SYMBOL + "F. \n"
    m += "Do you want the *temperature* to be *warmer* or *cooler*?"

    res = client.send_message(slackbot_settings.MAIN_CHANNEL, m)

    # record vote message so that we can later grab reaction count from it
    current_vote_message = {}
    current_vote_message['channel'] = res.body['channel']
    current_vote_message['ts'] = res.body['ts']

    # add reactions so to make it easier to click on by users
    client.react_to_message(heat_reaction_warmer, res.body['channel'], res.body['ts'])
    client.react_to_message(heat_reaction_cooler, res.body['channel'], res.body['ts'])

def close_vote(client):
    global current_vote_message

    res = client.webapi.reactions.get(channel=current_vote_message['channel'], timestamp=current_vote_message['ts'])
    reactions = { r['name']:r for r in res.body['message']['reactions'] }

    tally_warmer = (int(reactions[heat_reaction_warmer]['count'] - 1)
    tally_cooler = (int(reactions[heat_reaction_cooler]['count'] - 1)
    heat_diff = heat_increment(tally_warmer - tally_cooler)

    current_temp = messybot.isyclient.current_temp()
    future_heatpoint = current_temp + heat_diff

    tally = ""
    if(tally_warmer + tally_cooler == 0):
        tally += "Nobody voted! Everybody's " + phrases.peachy_keen() + "."
    else:
        tally += people_num_to_text(tally_warmer) + " voted to make it warmer. "
        tally += people_num_to_text(tally_cooler) + " voted to make it cooler. "

    m =  "Vote results: " + tally + "\n"
    if(heat_diff == 0):
        m += "So... We're going to keep the *same temperature*!"
    else:
        d = "up" if heat_diff > 0 else "down"
        m += "So... We're going to *set the temperature* " + d + " *to " + str(future_heatpoint) + DEGREE_SYMBOL + "*!\n"
        m += "(each person's vote is 0.5 " + DEGREE_SYMBOL + "F, and then I'll round up to the nearest whole number.)"

        print("SETTING HEATPOINT TO", future_heatpoint)
        messybot.isyclient.heatpoint = future_heatpoint

    client.rtm_send_message(slackbot_settings.MAIN_CHANNEL, m)

    current_vote_message = {}

#########

heat_reaction_warmer = "fire"
heat_reaction_cooler = "snowman"
def heat_increment(x):
    # this could be non-linear
    inc = round(x * 0.501) # adding the 0.001 because python3 does banker's rounding 
    return int(inc)

current_vote_message = {}
last_vote = None

vote_frequency = 20
vote_duration = 10

@idle
def heat_scheduler(client):
    global current_vote_message
    global last_vote

    """
    # logic:
    every X seconds, send a message and start vote
    after 5 seconds, close the vote, announce results
        if: temperature is still catching up to setpoint, then don't adjust temperature
        if: tempeature is pretty much at setpoint, adjust temperature
    """

    # debug to speed up vote
    if(last_vote == None):
        start_vote(client)
        last_vote = time.time()

    #every X secs, start vote
    if time.time() - last_vote >= vote_frequency:
        last_vote = time.time()
        start_vote(client)

    # after Y seconds, close the vote
    if time.time() - last_vote >= vote_duration:
        if(any(current_vote_message)):
            close_vote(client)


