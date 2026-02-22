#!/bin/bash
# Wrapper to run the python script from cron
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
source venv/bin/activate
/usr/bin/env python3 monitor_youtube.py >> cron_log.txt 2>&1
