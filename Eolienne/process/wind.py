#!/usr/bin/env python
# coding=utf8
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "wind.py"
__version__ = "1.0"

import signal
import sys
from random import getrandbits as randbits
from random import randint
from time import sleep

WIND_SPEED_INIT = 10
WIND_SPEED_FILE = "/tmp/wind.txt"


def signal_handler(sig, frame):
    print("CTRL+C pressed, exiting...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    wind_speed = WIND_SPEED_INIT
    gust_state = 0  # 0 = no / 1 = begin / 2 = in progress / 3 = last
    gust_cmp = 0

    wind_fd = open(WIND_SPEED_FILE, "w")

    while True:
        sleep(1)
        # try gust
        if gust_state == 3:
            gust_state = 0
        if gust_state == 1 or gust_state == 2:
            gust_state = 2
            gust_cmp -= 1
            if gust_cmp == 0:
                gust_state = 3

        if randint(0, 20) == 10 and gust_state == 0:
            gust_state = 1
            gust_cmp += 5

        # update wind speed
        if randbits(1):
            wind_speed += 1
        else:
            wind_speed -= 1
        if gust_state == 1:
            print("**new gust**")
            wind_speed += 10
        if gust_state == 3:
            print("**eo gust**")
            wind_speed -= 10
        if wind_speed < 0:
            wind_speed = 0
        if wind_speed > 30:
            wind_speed = 30

        wind_fd.write(str(wind_speed))
        wind_fd.seek(0)
