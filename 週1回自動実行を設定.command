#!/bin/bash
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
CRON_SCRIPT="$PROJECT_DIR/run_cron.sh"

echo "==================================================="
echo "  YouTube 週1回自動ダウンロード 設定"
echo "==================================================="
echo "毎週 月曜日の 朝9:00 に自動実行するように設定します。"
echo "（パソコンが起動している必要があります）"
echo ""
echo "設定内容:"
echo "実行ファイル: $CRON_SCRIPT"
echo ""

read -p "設定しますか？ (y/n): " confirm
if [[ $confirm != "y" ]]; then
    echo "キャンセルしました。"
    exit 0
fi

# 1. Start from scratch or append? Best to remove old entry first.
# Get current crontab, remove lines containing our script, save to tmp
crontab -l 2>/dev/null | grep -v "$CRON_SCRIPT" > current_cron

# 2. Add new job (0 9 * * 1 = Mon 9:00)
# Format: Minute Hour DayOfMonth Month DayOfWeek Command
echo "0 9 * * 1 /bin/bash $CRON_SCRIPT" >> current_cron

# 3. Install new cron
crontab current_cron
rm current_cron

echo ""
echo "✅ 設定完了しました！"
echo "これで毎週月曜 朝9時に自動でチェックして、新しい動画があればダウンロード＆テキスト化します。"
echo "（前回までの分は自動でスキップされます）"
echo "---------------------------------------------------"
read -p "Press enter to close"
