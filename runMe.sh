#!/bin/bash

source venv/bin/activate

while true; do
  echo "Checking For New Tweets"
  python3 main.py --log=verbose

  echo "Waiting 5 Minutes"
  sleep $((5*60))
done