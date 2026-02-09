import os
import subprocess
import sys

# --- Configuration ---
CHANNEL_URL = "https://www.youtube.com/@hisuikotaro/shorts"
DOWNLOAD_ARCHIVE = "downloaded_history.txt"
BASE_INPUT_DIR = "素材"

def run_command(cmd, shell=True):
    try:
        # If cmd is a list, force shell=False for safety and correct parsing
        if isinstance(cmd, list):
            subprocess.run(cmd, shell=False, check=True)
        else:
            subprocess.run(cmd, shell=shell, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

def main():
    print(f"=== YouTube Shorts Automation Start: {CHANNEL_URL} ===")
    
    # 1. Get List of Videos & Download Audio
    # We use yt-dlp to download directly into the project folder structure
    # Output template: 素材/Title/音声.mp3
    
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--output", f"{BASE_INPUT_DIR}/%(title)s/音声.%(ext)s",
        "--download-archive", DOWNLOAD_ARCHIVE,  # Skip already downloaded
        "--ignore-errors",  # Continue if one fails
        CHANNEL_URL
    ]
    
    # Run download command
    # This will download ALL audios into separate folders
    print("Downloading all past Shorts audio... (This may take a while)")
    run_command(cmd)
    
    '''
    # 2. Process Videos (Transcription ONLY as per user request)
    print("\n=== Extracting Content (Transcription) ===")
    
    # Scan '素材' directory for folders containing '音声.mp3'
    if not os.path.exists(BASE_INPUT_DIR):
        print(f"Directory {BASE_INPUT_DIR} not found.")
        return

    subdirs = [d for d in os.listdir(BASE_INPUT_DIR) if os.path.isdir(os.path.join(BASE_INPUT_DIR, d))]
    
    for project_name in subdirs:
        project_path = os.path.join(BASE_INPUT_DIR, project_name)
        voice_file = os.path.join(project_path, "音声.mp3")
        
        # Check if we should transcribe
        # Output: 素材/Title/字幕.json
        output_json = os.path.join(project_path, "字幕.json")
        output_txt = os.path.join(project_path, "字幕.txt")
        
        if os.path.exists(voice_file):
            if not os.path.exists(output_txt):
                print(f"\n>>> Transcribing Content: {project_name}")
                
                # Call transcribe.py
                # Note: We must run it using the same python env
                cmd = f"python3 transcribe.py \"{voice_file}\" \"{output_json}\""
                run_command(cmd)
                
                # Verify transcription and delete audio
                if os.path.exists(output_txt):
                    print(f"  [Cleanup] Deleting audio file: {voice_file}")
                    os.remove(voice_file)
            else:
                print(f"  [Skipped] Already transcribed: {project_name}")
                # Ensure audio is deleted even if we skipped transcription (if audio was left over)
                if os.path.exists(voice_file) and os.path.exists(output_txt):
                     print(f"  [Cleanup] Deleting leftover audio: {voice_file}")
                     os.remove(voice_file)
    '''
    print("\n=== All Tasks Completed ===")

if __name__ == "__main__":
    main()
