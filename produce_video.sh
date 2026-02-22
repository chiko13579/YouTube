#!/bin/bash

# Arguments
TITLE_AUDIO=$1
BODY_AUDIO=$2
OUTPUT_NAME=${3:-"output_video.mp4"}

if [ -z "$TITLE_AUDIO" ] || [ -z "$BODY_AUDIO" ]; then
  echo "Usage: ./produce_video.sh <title.mp3> <body.mp3> [output_filename.mp4]"
  exit 1
fi

echo "=========================================="
echo "🎬 Starting Video Production..."
echo "Title: $TITLE_AUDIO"
echo "Body:  $BODY_AUDIO"
echo "=========================================="

# 1. Generate Manifest & Assets
echo "🤖 Generating assets (Transcription, Search)..."
source venv/bin/activate
python generate_dragon_video.py "$TITLE_AUDIO" "$BODY_AUDIO"

if [ $? -ne 0 ]; then
  echo "❌ Error in python generation script."
  exit 1
fi

echo "=========================================="
echo "📝 Subtitle Review Check"
echo "You can now edit the subtitle files if needed:"
echo "  - src/title_subtitles.json"
echo "  - src/body_subtitles.json"
echo ""
echo "Press [Enter] to continue to rendering, or [Ctrl+C] to abort."
read -p "Waiting for your input..."
echo "=========================================="

# 2. Render Video
echo "🎞️ Rendering video with Remotion..."
npx remotion render src/index.ts DragonStock "out/$OUTPUT_NAME"

echo "=========================================="
echo "✅ Done! Video saved to out/$OUTPUT_NAME"
echo "=========================================="
