#!/bin/bash

source venv/bin/activate

while true; do
  echo "Checking For New Tweets"
  python3 main.py --log=info

  echo "Waiting 30 Minutes"
  sleep $((30*60))
done