#!/bin/bash
# Simple development runner that logs everything to a file

# Ensure the logs directory exists
mkdir -p logs

# Run honcho and tee output to both console and log file
# This preserves colors in terminal but strips them in the file
exec uvx honcho start | tee >(sed 's/\x1b\[[0-9;]*m//g' > logs/dev.log)
