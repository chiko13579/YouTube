import os
import shutil
import subprocess
import re
import sys
import random

# --- Configuration (Japanese Localized) ---
BASE_INPUT_DIR = "素材"       # Inputs
BGM_POOL_DIR = "素材/BGM集"   # BGM Pool
ASSETS_DIR = "public/assets"
ROOT_TSX = "src/Root.tsx"
OUTPUT_DIR = "完成品"         # Outputs

# Map input filenames (Japanese) to project asset names
FILE_MAPPING = {
    "音声.mp3": "juju_voice.mp3",  # Voice
    "動画.mp4": "video.mp4"       # Video
}

# English fallbacks just in case
FALLBACK_MAPPING = {
    "voice.mp3": "juju_voice.mp3",
    "video.mp4": "video.mp4"
}

def run_command(cmd, shell=True):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=shell, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(e.stderr)
        sys.exit(1)

def setup_bgm(src_dir):
    """Handle BGM selection: Specific override OR Random from pool."""
    dst = os.path.join(ASSETS_DIR, "current_bgm.mp3")
    
    # 1. Check for specific override in the project folder (Japanese or English)
    specific_bgm_jp = os.path.join(src_dir, "BGM.mp3")
    specific_bgm_en = os.path.join(src_dir, "bgm.mp3")
    
    if os.path.exists(specific_bgm_jp):
        shutil.copy2(specific_bgm_jp, dst)
        print(f"  [BGM] 指定BGMを使用: BGM.mp3")
        return
    elif os.path.exists(specific_bgm_en):
        shutil.copy2(specific_bgm_en, dst)
        print(f"  [BGM] Using specific BGM: bgm.mp3")
        return

    # 2. Check pool for random selection
    if os.path.exists(BGM_POOL_DIR):
        files = [f for f in os.listdir(BGM_POOL_DIR) if f.lower().endswith(('.mp3', '.wav'))]
        if files:
            chosen = random.choice(files)
            src = os.path.join(BGM_POOL_DIR, chosen)
            shutil.copy2(src, dst)
            print(f"  [BGM] おまかせBGMを選択: {chosen}")
            return
    
    print("  [BGM] BGMが見つかりませんでした (無音になります)")

def setup_files(project_name):
    """Copy files from inputs/project_name/ to public/assets/."""
    # Determine source directory
    if project_name:
        src_dir = os.path.join(BASE_INPUT_DIR, project_name)
    else:
        src_dir = BASE_INPUT_DIR

    if not os.path.exists(src_dir):
        if project_name:
             print(f"エラー: フォルダ '{src_dir}' が見つかりません。")
             sys.exit(1)
        else:
            os.makedirs(src_dir)
            print(f"フォルダ '{src_dir}' を作成しました。ここに素材を入れてください。")
            sys.exit(0)

    print(f"'{src_dir}' から素材を読み込み中...")
    
    # Standard files
    for input_name, asset_name in FILE_MAPPING.items():
        src = os.path.join(src_dir, input_name)
        dst = os.path.join(ASSETS_DIR, asset_name)
        
        # Try Japanese name first
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  [OK] 読み込み: {input_name}")
            continue
            
        # Try English fallback
        en_name = list(FALLBACK_MAPPING.keys())[list(FILE_MAPPING.keys()).index(input_name)] # Hacky mapping match
        src_en = os.path.join(src_dir, en_name)
        if os.path.exists(src_en):
            shutil.copy2(src_en, dst)
            print(f"  [OK] 読み込み: {en_name}")
        else:
            if "video" in asset_name:
                 print(f"  [--] {input_name} なし (既存の動画を使用)")
            else:
                 print(f"  [!!] {input_name} が見つかりません！")

    # BGM Logic
    setup_bgm(src_dir)

def get_audio_duration(file_path):
    """Get duration in seconds using ffprobe."""
    if not os.path.exists(file_path):
        return None
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    try:
        duration_str = run_command(cmd)
        return float(duration_str)
    except:
        return None

def update_duration_in_root(duration_sec):
    """Update durationInFrames in Root.tsx based on audio duration."""
    fps = 30
    total_frames = int(duration_sec * fps) + 30 
    print(f"音声の長さ: {duration_sec:.2f}秒 -> {total_frames}フレーム に設定")
    
    with open(ROOT_TSX, "r") as f:
        content = f.read()
    
    lines = content.splitlines()
    new_lines = []
    in_prototype = False
    
    for line in lines:
        if 'id="Prototype"' in line:
            in_prototype = True
        
        if in_prototype and "durationInFrames={" in line:
            line = re.sub(r"durationInFrames=\{\d+\}", f"durationInFrames={{{total_frames}}}", line)
            in_prototype = False 
            
        new_lines.append(line)
        
    with open(ROOT_TSX, "w") as f:
        f.write("\n".join(new_lines))

def main():
    print("=== 全自動動画生成ロボ ===")
    
    # Check for arguments
    project_name = None
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        print(f"対象プロジェクト: {project_name}")
    else:
        print("対象: '素材'フォルダ直下")

    # 1. Setup Files
    setup_files(project_name)
    
    # 2. Transcribe
    print("\n--- 文字起こし中 (AI) ---")
    run_command("source venv/bin/activate && python3 transcribe.py")
    
    # 3. Update Duration
    print("\n--- 長さ調整中 ---")
    voice_path = os.path.join(ASSETS_DIR, "juju_voice.mp3")
    duration = get_audio_duration(voice_path)
    if duration:
        update_duration_in_root(duration)

    # 4. Render
    print("\n--- 動画書き出し中... (しばらくお待ちください) ---")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Output filename based on project name
    if project_name:
        output_file = os.path.join(OUTPUT_DIR, f"{project_name}.mp4")
    else:
        output_file = os.path.join(OUTPUT_DIR, "完成動画.mp4")
        
    cmd = f"npx remotion render Prototype {output_file} --props='{{ \"mode\": \"vertical\" }}'"
    run_command(cmd)
    
    print(f"\n=== 完成！保存先: {output_file} ===")
    subprocess.run(["open", OUTPUT_DIR]) # Open folder on Mac

if __name__ == "__main__":
    main()
