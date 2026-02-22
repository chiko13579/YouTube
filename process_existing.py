import os
import subprocess
import sys

BASE_INPUT_DIR = "素材"

def run_command(cmd, shell=True):
    try:
        if isinstance(cmd, list):
            subprocess.run(cmd, shell=False, check=True)
        else:
            subprocess.run(cmd, shell=shell, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

def main():
    print("=== Processing Existing Audio Files ===")
    
    if not os.path.exists(BASE_INPUT_DIR):
        print(f"Directory {BASE_INPUT_DIR} not found.")
        return

    subdirs = [d for d in os.listdir(BASE_INPUT_DIR) if os.path.isdir(os.path.join(BASE_INPUT_DIR, d))]
    print(f"Found {len(subdirs)} folders. Checking for audio...")
    
    count = 0
    for project_name in subdirs:
        project_path = os.path.join(BASE_INPUT_DIR, project_name)
        voice_file = os.path.join(project_path, "音声.mp3")
        
        output_json = os.path.join(project_path, "字幕.json")
        output_txt = os.path.join(project_path, "字幕.txt")
        
        if os.path.exists(voice_file):
            if not os.path.exists(output_txt):
                print(f"\n[{count+1}/{len(subdirs)}] Transcribing: {project_name}")
                
                # Call transcribe.py
                cmd = [sys.executable, "transcribe.py", voice_file, output_json]
                run_command(cmd)
                
                # Verify and delete
                if os.path.exists(output_txt):
                    print(f"  [Cleanup] Deleting audio file: {voice_file}")
                    os.remove(voice_file)
            else:
                 # Clean up leftover audio if text exists
                 if os.path.exists(voice_file):
                     print(f"  [Cleanup] Deleting leftover audio: {project_name}")
                     os.remove(voice_file)
        
        count += 1

    print("\n=== All Existing Files Processed ===")

if __name__ == "__main__":
    main()
