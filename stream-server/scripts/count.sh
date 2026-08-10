#!/bin/bash

LOGFILE="/scripts/count.log"

ffmpeg -y -i "$1" -vcodec libx264 "$2"

echo "$(date) - removed input: $1" >> "$LOGFILE"
rm -f "$1"

rt=$(/usr/bin/python3 /scripts/count_people.py --input_video "$2" 2>&1)

# ここでログに保存
echo "$(date) - python result: $rt" >> "$LOGFILE"

if [[ "$rt" == *"Discarding"* ]]; then
    echo "$(date) - output discarded: $2" >> "$LOGFILE"
    rm -f "$2"
else
    echo "$(date) - output kept: $2" >> "$LOGFILE"
fi
