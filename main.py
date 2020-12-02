#!/usr/bin/python

import argparse
# import pandas as pd
import logging
from json.decoder import JSONDecodeError

import twitter
import json
import datetime
import humanize

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

    # Date/Time Out of Office Epoch
    out_of_office = 1611162000

    leaving = get_time_remaining(leaving=out_of_office)
    logger.info(leaving)

    last_replied_status = read_status_from_file()
    replied_to_status = run_search(credentials=credentials, leaving_countdown=leaving, latest_status=last_replied_status)

    if replied_to_status is not None:
        save_status_to_file(replied_to_status)


def save_status_to_file(status_id: int):
    file_contents = {
        "last_status": status_id
    }

    f = open("latest_status.json", "w")
    f.write(json.dumps(file_contents))
    f.close()


def read_status_from_file() -> int:
    f = open("latest_status.json", "r")
    filecontents = f.read()
    f.close()

    # {"last_status": 1333984649056546816}
    try:
        decoded = json.loads(filecontents)

        if 'last_status' not in decoded:
            return None
    except JSONDecodeError:
        return None

    return decoded['last_status']


def get_time_remaining(leaving: int):
    leaving_time = datetime.datetime.utcfromtimestamp(leaving)
    current_time = datetime.datetime.utcnow()

    remaining = leaving_time-current_time

    return humanize.precisedelta(remaining)


def run_search(credentials: json, leaving_countdown: str, latest_status: int = None) -> int:
    api = twitter.Api(consumer_key=credentials['consumer']['key'],
                      consumer_secret=credentials['consumer']['secret'],
                      access_token_key=credentials['token']['key'],
                      access_token_secret=credentials['token']['secret'],
                      sleep_on_rate_limit=True)

    # user_id=25073877 is Donald Trump (@realDonaldTrump)
    prez_statuses = api.GetUserTimeline(user_id=25073877, since_id=latest_status, count=1)
    logger.warning(prez_statuses)

    for prez_status in prez_statuses:
        new_status = "@{user} {name} will be out of office in {countdown}".format(name=prez_status.user.name, user=prez_status.user.screen_name, countdown=leaving_countdown)
        logger.debug(new_status)

        api.PostUpdate(in_reply_to_status_id=prez_status.id, status=new_status)
        return prez_status.id  # We only want to post once

    return None


if __name__ == '__main__':
    # This is to get DoltPy's Logger To Shut Up When Running `this_script.py -h`
    logging.Logger.setLevel(system_helpers.logger, logging.CRITICAL)

    args = parser.parse_args()
    main(args)
