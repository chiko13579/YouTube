#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 monitor_youtube.py
echo "---------------------------------------------------"
echo "完了しました。ウィンドウを閉じてください。"
read -p "Press enter to close"
