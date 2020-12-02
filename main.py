#!/usr/bin/python

import argparse
# import pandas as pd
import logging
import twitter
import json

# Custom Log Levels
from doltpy.core import system_helpers
from doltpy.core.system_helpers import get_logger

VERBOSE = logging.DEBUG - 1
logging.addLevelName(VERBOSE, "VERBOSE")

# Dolt Logger
logger = get_logger(__name__)

# Argument Parser Setup
parser = argparse.ArgumentParser(description='Arguments For Presidential Tweet Archiver')
parser.add_argument("-log", "--log", help="Set Log Level (Defaults to WARNING)",
                    dest='logLevel',
                    default='WARNING',
                    type=str.upper,
                    choices=['VERBOSE', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])


def main(arguments: argparse.Namespace):
    # Set Logging Level
    logging.Logger.setLevel(system_helpers.logger, arguments.logLevel)  # DoltPy's Log Level
    logger.setLevel(arguments.logLevel)  # This Script's Log Level

    # Setup For Twitter API
    with open("credentials.json", "r") as file:
        credentials = json.load(file)

    run_search(credentials=credentials)


def run_search(credentials: json):
    api = twitter.Api(consumer_key=credentials['consumer']['key'],
                      consumer_secret=credentials['consumer']['secret'],
                      access_token_key=credentials['token']['key'],
                      access_token_secret=credentials['token']['secret'],
                      sleep_on_rate_limit=True)

    mentions = api.GetMentions(since_id=1330087270569955337)
    # logger.warning(mentions)

    # [Status(ID=1330087270569955337, ScreenName=AlexEvelyn42, Created=Sat Nov 21 09:54:51 +0000 2020, Text='@DigitalRoverDog I forgot I used to have a bot on Twitter.')]
    for mention in mentions:
        new_status = "@{user} Hello {name}".format(name=mention.user.name, user=mention.user.screen_name)
        logger.warning(new_status)
        api.PostUpdate(in_reply_to_status_id=mention.id, status=new_status)

    # status = api.PostUpdate('Test Tweet From Python Twitter!')
    # logger.warning(status.text)


if __name__ == '__main__':
    # This is to get DoltPy's Logger To Shut Up When Running `this_script.py -h`
    logging.Logger.setLevel(system_helpers.logger, logging.CRITICAL)

    args = parser.parse_args()
    main(args)
