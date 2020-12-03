#!/usr/bin/python

import argparse
import logging
import os
from json.decoder import JSONDecodeError

import PIL
import twitter
import json
import datetime
import humanize
from os import path

from PIL import ImageFont, ImageDraw, Image

VERBOSE = logging.DEBUG - 1
logging.addLevelName(VERBOSE, "VERBOSE")

logger = logging.getLogger(__name__)

# Argument Parser Setup
parser = argparse.ArgumentParser(description='Arguments For Out of Office Replier')
parser.add_argument("-log", "--log", help="Set Log Level (Defaults to WARNING)",
                    dest='logLevel',
                    default='WARNING',
                    type=str.upper,
                    choices=['VERBOSE', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])


def main(arguments: argparse.Namespace):
    # Set Logging Level
    logger.setLevel(arguments.logLevel)  # This Script's Log Level

    # Setup For Twitter API
    with open("credentials.json", "r") as file:
        credentials = json.load(file)

    # Date/Time Out of Office Epoch
    in_office = 1484931600
    out_of_office = 1611162000
    current_time = int(datetime.datetime.utcnow().timestamp())

    leaving = get_time_remaining(current=current_time, leaving=out_of_office)
    logger.info("Leaving Office: {}".format(leaving))

    percentage = get_percentage_remaining(current=current_time, entry=in_office, leaving=out_of_office)
    progress_bar = draw_progress_bar(percentage)

    last_replied_status = read_status_from_file()
    replied_to_status = run_search(credentials=credentials, leaving_countdown=leaving, latest_status=last_replied_status, progress_bar=progress_bar)

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
    file = "latest_status.json"
    if not path.exists(file):
        return None

    f = open(file, "r")
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


def get_percentage_remaining(entry: int, leaving: int, current: int) -> float:
    entry_time = datetime.datetime.utcfromtimestamp(entry)
    leaving_time = datetime.datetime.utcfromtimestamp(leaving)
    current_time = datetime.datetime.utcfromtimestamp(current)

    percentage = (current_time - entry_time) / (leaving_time - entry_time) * 100

    logger.info("Percentage Remaining: {}".format(percentage))
    return percentage


def get_time_remaining(current: int, leaving: int):
    leaving_time = datetime.datetime.utcfromtimestamp(leaving)
    current_time = datetime.datetime.utcfromtimestamp(current)

    remaining = leaving_time-current_time

    return humanize.precisedelta(remaining)


def run_search(credentials: json, leaving_countdown: str, latest_status: int = None, progress_bar: PIL.Image = None) -> int:
    api = twitter.Api(consumer_key=credentials['consumer']['key'],
                      consumer_secret=credentials['consumer']['secret'],
                      access_token_key=credentials['token']['key'],
                      access_token_secret=credentials['token']['secret'],
                      sleep_on_rate_limit=True)

    # user_id=25073877 is Donald Trump (@realDonaldTrump)
    prez_statuses = api.GetUserTimeline(user_id=25073877, since_id=latest_status, count=1)

    for prez_status in prez_statuses:
        new_status = "@{user} {name} will be out of office in {countdown}".format(name=prez_status.user.name, user=prez_status.user.screen_name, countdown=leaving_countdown)
        logger.debug(new_status)

        if progress_bar is None:
            api.PostUpdate(in_reply_to_status_id=prez_status.id, status=new_status)
        else:
            # Write To File
            progress_bar.save("working/temp.png", "PNG")
            api.PostUpdate(in_reply_to_status_id=prez_status.id, status=new_status, media="working/temp.png")
            os.remove("working/temp.png")

        return prez_status.id  # We only want to post once

    return None


def draw_progress_bar(progress: float) -> PIL.Image:
    if not os.path.exists('working'):
        os.makedirs('working')

    with Image.new("RGBA", (1024, 128)) as im:
        draw = ImageDraw.Draw(im, 'RGBA')

        # Fill With Transparent Background
        draw.rectangle(xy=((0, 0), (im.size[0]-1, im.size[1]-1)), fill=(0, 0, 0, 0), outline=(0, 0, 0, 0), width=1)

        # Draw Unfilled of Bar
        draw.rectangle(xy=((10, 10), (im.size[0]-10, im.size[1]-10)), fill=(20, 20, 20, 255), outline=(0, 0, 0, 255), width=1)

        # Draw Progress Filled
        end_bar_length = (im.size[0]-10)*(progress/100)
        draw.rectangle(xy=((10, 10), (end_bar_length, (im.size[1]-10))), fill=(10, 203, 200, 255), outline=(2, 56, 50, 255), width=1)

        # Write Text
        fnt = ImageFont.truetype("working/firacode/FiraCode-Bold.ttf", 40)

        percentage_text = "{percent}% Complete".format(percent=round(progress, 2))
        text_length = int(25.384615384615385 * len(percentage_text))
        length = (im.size[0] - end_bar_length) + text_length

        draw.multiline_text((im.size[0]-length, (im.size[1]/2)-(37.5/2)), percentage_text, font=fnt, fill=(int(200), int(50), int(0), 255))

        return im


if __name__ == '__main__':
    args = parser.parse_args()
    main(args)