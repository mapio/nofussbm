#!/bin/bash

# trap TERM and change to QUIT
trap 'echo wrapper killing $PID; kill -QUIT $PID' TERM

# program to run
gunicorn nofussbm:app  --access-logfile=- --error-logfile=- -w 3 -b 0.0.0.0:$PORT &

# capture PID and wait
PID=$!
echo wrapper started $PID
wait
