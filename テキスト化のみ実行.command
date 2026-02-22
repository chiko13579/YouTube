#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "ダウンロード済みの動画をテキスト化します..."
python3 process_existing.py
echo "---------------------------------------------------"
echo "完了しました。ウィンドウを閉じてください。"
read -p "Press enter to close"
