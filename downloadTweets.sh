#!/bin/bash

source venv/bin/activate

while true; do
  echo "Checking For New Tweets"
  python3 presidential-archives.py --log=verbose

  echo "Waiting 16 Minutes"
  sleep $((16*60))
done