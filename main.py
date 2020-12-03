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

parser.add_argument("-offline", "--offline", help="Disable Twitter and internet access for debugging the script",
                    dest='isOffline',
                    default='FALSE',
                    type=str.upper,
                    choices=['TRUE', 'FALSE'])


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

    # Allows Easy Disabling Of Twitter/Network Features For Testing
    if arguments.isOffline == 'TRUE':
        progress_bar.save("working/temp.png")
        logger.warning("Tweeting Ability Disabled Due To Offline Parameter")
        return

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


def get_bar_length(progress_bar: PIL.Image, percentage: float) -> float:
    return (progress_bar.size[0]-10)*(percentage/100)


def draw_progress_bar(progress: float) -> PIL.Image:
    if not os.path.exists('working'):
        os.makedirs('working')

    # Blue - #002868 (0, 40, 104)
    # Red - #BF0A30 (191, 10, 48)
    with Image.new("RGBA", (640, 128)) as im:
        draw = ImageDraw.Draw(im, 'RGBA')

        # Debug Progress (Percentage)
        # progress = 0

        # End Bar Length
        end_bar_length = get_bar_length(progress_bar=im, percentage=progress)

        # Border Limits
        begin_limit = (10, 10)
        end_limit = (end_bar_length, (im.size[1]-10))

        # Colors
        red_stripe = (191, 10, 48, 255)
        white_stripe = (255, 255, 255, 255)
        blue_canton = (0, 40, 104, 255)
        black_border = (0, 0, 0, 255)
        transparent_border = (0, 0, 0, 0)
        unfilled_bar = (20, 20, 20, 255)

        # Fill With Transparent Background
        draw.rectangle(xy=((0, 0), (im.size[0]-1, im.size[1]-1)), fill=transparent_border, outline=transparent_border, width=1)

        # Draw Unfilled Bar
        draw.rectangle(xy=(begin_limit, (im.size[0]-10, im.size[1]-10)), fill=unfilled_bar, outline=black_border, width=1)

        # Draw Red Progress Filled
        draw.rectangle(xy=(begin_limit, end_limit), fill=red_stripe, outline=black_border, width=1)

        # Draw White Progress Filled
        offset = (end_limit[1] - begin_limit[1])/13
        for stripe in range(1, 13):
            if stripe % 2 == 0:
                continue

            new_begin_limit = (begin_limit[0]+1, begin_limit[1] + (offset * stripe))
            new_end_limit = (end_limit[0]-1, begin_limit[1] + (offset * (stripe+1)))

            logger.debug("White Stripe Y Axis Coordinate: {}, {}".format(new_begin_limit[1], new_end_limit[1]))

            draw.rectangle(xy=(new_begin_limit, new_end_limit), fill=white_stripe)

        # Draw Progress Bar Beginning
        begin_bar_length = get_bar_length(progress_bar=im, percentage=20)
        round_rectangle(color=blue_canton, image=im, start=(begin_limit[0]+1, begin_limit[1]+1), end=(int(begin_bar_length-1), end_limit[1]))

        # Write Text and Background Shading
        fnt = ImageFont.truetype("working/firacode/FiraCode-Bold.ttf", 40)

        percentage_text = "{percent}% Complete".format(percent=round(progress, 2))
        text_length = int(25.384615384615385 * len(percentage_text))
        length = (im.size[0] - end_bar_length) + text_length

        text_color = (0, 0, 255, 255)
        shade_color = (0, 0, 0, 130)
        text_start = (im.size[0]-length, (im.size[1]/2)-(37.5/2))
        text_end = (end_limit[0], end_limit[1]-(37.5/2))

        shaded_background = Image.new('RGBA', im.size, (0, 0, 0, 0))
        shaded_background_draw = ImageDraw.Draw(shaded_background)

        shaded_background_draw.rectangle(xy=(text_start, text_end), fill=shade_color)
        im = Image.alpha_composite(im, shaded_background)

        draw = ImageDraw.Draw(im)
        draw.multiline_text(xy=text_start, text=percentage_text, font=fnt, fill=text_color)

        # Paste Trump's Face
        canton_begin_pos = (begin_limit[0]+1, begin_limit[1]+1)
        canton_end_pos = (int(begin_bar_length-1), end_limit[1])
        face_size = (int((canton_end_pos[0] - canton_begin_pos[0])/1.5), int((canton_end_pos[1] - canton_begin_pos[1])))
        face_begin_pos = (int(canton_begin_pos[0] + (canton_end_pos[0]/6)), int(canton_begin_pos[1]))

        face = Image.open("trump.png").convert("RGBA").resize(size=face_size)

        im.paste(im=face, box=face_begin_pos)

        return im


def round_corner(radius: int, fill: tuple, outer_corner_color: tuple = (0, 0, 0, 0)):
    """Draw a round corner
        Stolen From: https://code-maven.com/slides/python/rectangle-with-rounded-corners
    """
    corner = Image.new("RGBA", (radius, radius), outer_corner_color)

    # Corner
    draw = ImageDraw.Draw(corner)
    draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=fill)

    return corner


def round_rectangle(color: tuple, image: PIL.Image, start: tuple, end: tuple):
    """Draw a rounded rectangle
        Modified From: https://code-maven.com/slides/python/rectangle-with-rounded-corners
    """
    # Corner Colors Outside
    left_corners_outer_color = (0, 0, 0, 255)
    right_corners_outer_color = (0, 0, 0, 0)

    radius = 10
    left_corners = round_corner(radius=radius, fill=color, outer_corner_color=left_corners_outer_color)
    right_corners = round_corner(radius=radius, fill=color, outer_corner_color=right_corners_outer_color)

    image.paste(im=left_corners, box=start, mask=left_corners)  # Top Left
    image.paste(im=left_corners.rotate(90), box=(start[0], end[1]-radius), mask=left_corners.rotate(90))  # Bottom Left

    image.paste(im=right_corners.rotate(270), box=(end[0], start[1]), mask=right_corners.rotate(270))  # Top Right
    image.paste(im=right_corners.rotate(180), box=(end[0], end[1]-radius), mask=right_corners.rotate(180))  # Bottom Right

    # Start Drawing
    draw = ImageDraw.Draw(image, 'RGBA')

    # Inside Rectangle (Vertical)
    v_rect_start = (start[0]+radius, start[1])
    v_rect_end = (end[0], end[1]-1)
    draw.rectangle(xy=(v_rect_start, v_rect_end), fill=color)

    # Left Rectangle (Horizontal)
    h_rect_start = (start[0], start[1]+radius)
    h_rect_end = (end[0]+radius-1, end[1]-radius)
    draw.rectangle(xy=(h_rect_start, h_rect_end), fill=color)

    return image


if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
