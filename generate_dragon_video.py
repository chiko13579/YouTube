import os
import json
import requests
import sys
from dotenv import load_dotenv
from openai import OpenAI
import time

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")

if not OPENAI_API_KEY:
    print("Notice: OPENAI_API_KEY not found. Using local transcription and default keywords.")
    client = None
else:
    client = OpenAI(api_key=OPENAI_API_KEY)

def generate_dragon_image(tone):
    # Check for custom image first
    custom_image_path = "public/assets/custom_dragon.png"
    if os.path.exists(custom_image_path):
        print(f"Using custom dragon image found at {custom_image_path}")
        return "CUSTOM"

    print(f"Generating Dragon Image with tone: {tone}...")
    if not client:
        print("Skipping image generation (No OpenAI Key).")
        return None

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"A high quality, cinematic portrait of a wise and powerful dragon, speaking directly to the camera. The dragon has a {tone} expression. Detailed scales, dramatic lighting, 8k resolution, photorealistic.",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        return image_url
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

def analyze_audio_context(transcription_text):
    if not client:
        print("Using fallback context analysis (No OpenAI Key).")
        # Simple fallback: extract nouns or just use defaults
        return {"tone": "neutral", "keywords": ["nature", "scenery", "sky", "business", "relaxing"]}

    print("Analyzing audio context...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional video editor finding B-roll footage. \n"
                                              "Analyze the provided text and extract: \n"
                                              "1. A 'tone' for the speaker (e.g., serious, excited, calm). \n"
                                              "2. A list of 6-8 VISUAL search terms for stock videos. \n"
                                              "   - DO NOT use abstract concepts like 'happiness' or 'thought'. \n"
                                              "   - USE visual descriptions like 'person smiling at sunset', 'hand writing in notebook', 'clock ticking', 'starry night sky'. \n"
                                              "   - These terms will be used to search Pexels.\n"
                                              "Return JSON: {\"tone\": \"...\", \"keywords\": [\"...\"]}"},
                {"role": "user", "content": transcription_text}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        return data
    except Exception as e:
        print(f"Error analyzing context: {e}")
        return {"tone": "neutral", "keywords": ["nature", "cinematic", "scenery"]}

def search_pexels_videos(keywords, min_duration=5):
    print(f"Searching Pexels videos for keywords: {keywords}")
    headers = {"Authorization": PEXELS_API_KEY}
    videos = []
    
    # Ensure download directory exists
    stock_dir = "public/assets/stock"
    os.makedirs(stock_dir, exist_ok=True)
    
    for keyword in keywords:
        if len(videos) >= 5: break # Limit to 5 videos for now to save time/space
        url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=3&orientation=landscape"
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                for v in data.get("videos", []):
                    # Filter for decent quality and duration
                    video_files = v.get("video_files", [])
                    # Get HD quality if possible (but not too huge, maybe 720p is safer for render)
                    target_file = next((f for f in video_files if f["height"] == 720), None) or \
                                  next((f for f in video_files if f["height"] == 1080), None) or \
                                  (video_files[0] if video_files else None)
                    
                    if target_file and v["duration"] >= min_duration:
                        # Download the video
                        video_filename = f"pexels_{v['id']}.mp4"
                        local_path = os.path.join(stock_dir, video_filename)
                        
                        if not os.path.exists(local_path):
                            print(f"Downloading video {v['id']}...")
                            download_res = requests.get(target_file["link"])
                            with open(local_path, "wb") as f:
                                f.write(download_res.content)
                        else:
                            print(f"Video {v['id']} already exists.")
                            
                        # Add to list with local path for Remotion (relative to public)
                        videos.append({
                            "id": v["id"],
                            "url": f"/assets/stock/{video_filename}",
                            "duration": v["duration"],
                            "keyword": keyword
                        })
                        break # One video per keyword to match variety
        except Exception as e:
            print(f"Error searching/downloading Pexels for {keyword}: {e}")
            
    # Deduplicate by ID
    seen = set()
    unique_videos = []
    for v in videos:
        if v["id"] not in seen:
            unique_videos.append(v)
            seen.add(v["id"])
            
    return unique_videos

def main(title_audio_path, body_audio_path):
    # 1. Transcribe Title Audio (for Dragon Context/LipSync duration)
    title_txt_file = "src/title_subtitles.txt"
    title_json_subtitles = "src/title_subtitles.json"
    print(f"Running transcription on Title: {title_audio_path}...")
    os.system(f"venv/bin/python transcribe.py \"{title_audio_path}\" \"{title_json_subtitles}\"")
    
    
    # 2. Transcribe Body Audio (for Keywords/Stock Videos)
    body_txt_file = "src/body_subtitles.txt"
    body_json_subtitles = "src/body_subtitles.json"
    print(f"Running transcription on Body: {body_audio_path}...")
    os.system(f"venv/bin/python transcribe.py \"{body_audio_path}\" \"{body_json_subtitles}\"")
    
    # Calculate durations EARLY
    from mutagen.mp3 import MP3
    try:
        title_audio_duration = MP3(title_audio_path).info.length
        body_audio_duration = MP3(body_audio_path).info.length
    except Exception as e:
        print(f"Error reading audio duration: {e}. Defaulting to 10s and 30s.")
        title_audio_duration = 10.0
        body_audio_duration = 30.0

    
    if not os.path.exists(body_txt_file):
        print("Body transcription failed.")
        return

    # 3. Analyze Body Subtitles for Scenes
    print("Reading subtitles for scene analysis...")
    with open(body_json_subtitles, 'r') as f:
        subtitles = json.load(f)
    
    # Read title text if available
    title_text = ""
    if os.path.exists(title_txt_file):
        with open(title_txt_file, "r") as f:
            title_text = f.read()

    # 3b. Group subtitles into scenes (~5-8 seconds or logical chunks)
    scenes = group_subtitles_into_scenes(subtitles, title_text)
    
    # 4. Generate/Prepare Dragon Image (Title Context)
    # Use the first scene's tone or overall tone
    image_url = generate_dragon_image("neutral") 
    local_image_path = "public/assets/dragon_base.png"
    
    if image_url == "CUSTOM":
        import shutil
        shutil.copy("public/assets/custom_dragon.png", local_image_path)
        print(f"Used custom image: {local_image_path}")
    elif image_url:
        img_data = requests.get(image_url).content
        with open(local_image_path, "wb") as f:
            f.write(img_data)
        print(f"Saved Dragon Image to {local_image_path}")
    
    # 5. Generate Lip Sync Video (AI - Replicate)
    lipsync_video_path = "public/assets/dragon_lipsync.mp4"
    print("Generating Lip-Sync Video via Replicate (SadTalker)...")
    
    lipsync_url = generate_lip_sync_video(local_image_path, title_audio_path)
    
    if lipsync_url:
        try:
            v_data = requests.get(lipsync_url).content
            with open(lipsync_video_path, "wb") as f:
                f.write(v_data)
            print(f"Saved Lip-Sync Video to {lipsync_video_path}")
            
            # Use video for intro
            intro_manifest = {
                "type": "video",
                "visual_src": "/assets" + "/dragon_lipsync.mp4", # Relative for Remotion
                "audio_src": "/assets/" + os.path.basename(title_audio_path), # Audio is embedded in video usually, but we keep track
                "durationInSeconds": title_audio_duration
            }
        except Exception as e:
            print(f"Error downloading lipsync video: {e}")
            # Fallback to image
            intro_manifest = {
                "type": "image",
                "visual_src": "/assets/dragon_base.png",
                "audio_src": "/assets/" + os.path.basename(title_audio_path),
                "durationInSeconds": title_audio_duration
            }
    else:
        print("Lip-Sync generation failed or skipped. Using static image.")
        intro_manifest = {
            "type": "image",
            "visual_src": "/assets/dragon_base.png",
            "audio_src": "/assets/" + os.path.basename(title_audio_path),
            "durationInSeconds": title_audio_duration
        }

    # 6. Fetch Stock Videos for Scenes
    timeline = []
    if PEXELS_API_KEY:
        timeline = fetch_videos_for_scenes(scenes)
    else:
        print("PEXELS_API_KEY not found. Using random local videos.")
        pass 

    # 7. Create Manifest
    from mutagen.mp3 import MP3
    
    # Calculate duration BEFORE creating manifest (and before using it in intro fallback)
    # Actually we need it for the intro logic too.
    
    manifest = {
        "intro": intro_manifest,
        "body": {
            "timeline": timeline,
            "audio_src": "/assets/" + os.path.basename(body_audio_path),
            "durationInSeconds": body_audio_duration
        }
    }
    
    # Write to public for runtime access
    with open("public/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    # Write to src for build-time access
    with open("src/dragon-manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print("Saved public/manifest.json and src/dragon-manifest.json")

def generate_lip_sync_video(image_path, audio_path):
    if not REPLICATE_API_KEY:
        print("REPLICATE_API_KEY not found. Skipping.")
        return None
        
    print(f"  Invoking run_replicate.py for Lip Sync via venv_replicate...")
    try:
        import subprocess
        
        # Run isolated process using DEDICATED VENV
        python_executable = "venv_replicate/bin/python"
        if not os.path.exists(python_executable):
            print(f"  Warning: {python_executable} not found. Using system python (might fail).")
            python_executable = "python3"

        result = subprocess.run(
            [python_executable, "run_replicate.py", image_path, audio_path],
            capture_output=True,
            text=True
        )
        
        print(f"  Subprocess STDOUT: {result.stdout}")
        print(f"  Subprocess STDERR: {result.stderr}")
        
        if result.returncode != 0:
            print("  Replicate script failed.")
            return None
            
        # Parse output for URL
        for line in result.stdout.splitlines():
            if line.startswith("OUTPUT_URL="):
                url = line.replace("OUTPUT_URL=", "").strip()
                # Clean up if needed (Replicate sometimes returns list string)
                if url.startswith("['") and url.endswith("']"):
                    url = url[2:-2]
                return url
                
        return None
        
    except Exception as e:
        print(f"  Error invoking Replicate subprocess: {e}")
        return None

def group_subtitles_into_scenes(subtitles, title_context):
    """
    Groups subtitles into scenes based on sentence endings ("。").
    """
    if not subtitles: return []
    
    scenes = []
    current_scene_text = []
    current_start_frame = subtitles[0]['startFrame']
    
    for i, sub in enumerate(subtitles):
        current_scene_text.append(sub['text'])
        
        # Check for sentence end
        is_sentence_end = "。" in sub['text']
        is_last = (i == len(subtitles) - 1)
        
        if is_sentence_end or is_last:
            # End of scene
            scene_text = " ".join(current_scene_text)
            print(f"Analyzing scene: {scene_text[:30]}...")
            
            # Get multiple queries
            queries = get_scene_visual_queries(scene_text, title_context)
            
            # Determine end frame to avoid gaps
            # If not last scene, extend to start of next subtitle
            if not is_last:
                scene_end_frame = subtitles[i+1]['startFrame']
            else:
                scene_end_frame = sub['endFrame'] + 30 # Add buffer at very end
            
            scenes.append({
                "startFrame": current_start_frame,
                "endFrame": scene_end_frame, 
                "text": scene_text,
                "queries": queries # List of queries
            })
            
            # Reset
            if not is_last:
                current_start_frame = subtitles[i+1]['startFrame']  # Next starts at next subtitle start
                current_scene_text = []

    return scenes

def get_scene_visual_queries(segment_text, broad_context):
    if not client:
        return ["nature", "abstract", "scenery"] 
        
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a visual director. Given a sentence from a video script, ensure you understand the broad context.\n"
                                              "Broad Context: " + broad_context + "\n"
                                              "Task: Provide 3 DISTINCT visual search queries for a stock video website (Pexels) to match the sentence.\n"
                                              "1. Literal: Directly depicting the action/object.\n"
                                              "2. Metaphorical/Emotional: Depicting the feeling or abstract concept.\n"
                                              "3. Atmospheric: A background vibe that fits.\n"
                                              "Return JSON: {\"queries\": [\"query1\", \"query2\", \"query3\"]}"},
                {"role": "user", "content": f"Script Segment: {segment_text}"}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        return data.get("queries", ["scenery"])
    except Exception as e:
        print(f"Error getting scene queries: {e}")
        return ["scenery"]

def select_best_video_from_candidates(scene_text, candidates):
    """
    Uses GPT-4o Vision to select the best video from a list of candidates.
    candidates: list of dicts {id, url, image, video_files}
    """
    if not candidates: return None
    if not client: return candidates[0] # Fallback

    print(f"  🤖 AI Selecting best video from {len(candidates)} candidates for: '{scene_text[:20]}...'")

    # Prepare message for GPT-4o
    content = [
        {"type": "text", "text": f"Select the video that best matches this scene description: \"{scene_text}\".\n"
                                  f"Return ONLY the JSON object: {{\"selected_id\": <id>}}. \n"
                                  f"If none are perfect, choose the best available relative to the mood."}
    ]
    
    # Add images
    for c in candidates:
        content.append({
            "type": "image_url",
            "image_url": {"url": c["image"]}
        })
        content.append({
            "type": "text",
            "text": f"ID: {c['id']}"
        })

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a video editor selecting stock footage. You will be given a scene description and a list of video thumbnails with IDs. Select the single best match."},
                {"role": "user", "content": content}
            ],
            max_tokens=50,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        selected_id = result.get("selected_id")
        
        # Find the candidate object
        selected = next((c for c in candidates if c["id"] == selected_id), None)
        if selected:
            print(f"  ✅ AI Selected ID: {selected_id}")
            return selected
        else:
            print(f"  ⚠️ AI returned unknown ID {selected_id}, using first candidate.")
            return candidates[0]
            
    except Exception as e:
        print(f"  ❌ AI Selection failed: {e}. Using first candidate.")
        return candidates[0]

def fetch_videos_for_scenes(scenes):
    timeline = []
    headers = {"Authorization": PEXELS_API_KEY}
    stock_dir = "public/assets/stock"
    os.makedirs(stock_dir, exist_ok=True)
    
    fps = 30
    
    for i, scene in enumerate(scenes):
        queries = scene["queries"]
        duration_sec = (scene["endFrame"] - scene["startFrame"]) / fps
        min_duration = max(5, duration_sec) 
        
        print(f"Scene {i+1}: Queries {queries} ({duration_sec:.1f}s)")
        
        video_path = None
        
        # Try queries effectively
        # Strategy: Search query 1 (Top 5). If good, AI select. 
        # If no results, try query 2.
        
        for query in queries:
            print(f"  Searching: '{query}' (min {duration_sec:.1f}s)...")
            # Fetch TOP 5 videos with minimum duration
            # Pexels API supports 'min_duration'
            url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=landscape&size=medium&min_duration={int(duration_sec)}"
            
            try:
                res = requests.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    videos = data.get("videos", [])
                    
                    if videos:
                        # Prepare candidates
                        candidates = []
                        for v in videos:
                            # Extract useful info
                            video_files = v.get("video_files", [])
                            target = next((f for f in video_files if f["height"] == 720), None) or video_files[0]
                            
                            candidates.append({
                                "id": v["id"],
                                "image": v["image"], # Thumbnail
                                "download_link": target["link"],
                                "duration": v["duration"]
                            })
                        
                        # Filter out candidates that are surprisingly short (API isn't perfect)
                        valid_candidates = [c for c in candidates if c["duration"] >= duration_sec * 0.8] # Allow 20% slack for slow mo
                        
                        if not valid_candidates:
                             print(f"  Found videos but all too short. Checking original candidates...")
                             valid_candidates = candidates # Fallback to whatever we have

                        # AI SELECTION
                        best_match = select_best_video_from_candidates(scene["text"], valid_candidates)
                        
                        # Download
                        filename = f"scene_{i}_{best_match['id']}.mp4"
                        local_path = os.path.join(stock_dir, filename)
                        
                        if not os.path.exists(local_path):
                            print(f"  Downloading video...")
                            d_res = requests.get(best_match["download_link"])
                            with open(local_path, "wb") as f:
                                f.write(d_res.content)
                        else:
                            print(f"  Using cached.")
                            
                        video_path = f"/assets/stock/{filename}"
                        print(f"  -> Found match with '{query}'")
                        break # Found it!
                    else:
                        print(f"  No videos found for '{query}'.")
                else:
                     print(f"  API Error: {res.status_code}")
            except Exception as e:
                print(f"  Error fetching: {e}")
        
        # Fallback
        if not video_path:
             print("  All queries failed. Using fallback.")
             video_path = "/assets/stock/pexels_fallback.mp4"
             
        # Get actual duration of the source video for looping
        source_duration = 10.0
        try:
            from mutagen.mp4 import MP4
            # We need the absolute path to read metadata
            abs_path = os.path.join(stock_dir, os.path.basename(video_path))
            source_duration = MP4(abs_path).info.length
        except Exception as e:
            print(f"  Could not get source duration: {e}")

        timeline.append({
            "startFrame": scene["startFrame"],
            "durationInFrames": scene["endFrame"] - scene["startFrame"],
            "video_src": video_path,
            "keyword": queries[0],
            "source_duration": source_duration
        })
        
    return timeline

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_dragon_video.py <title_audio_path> <body_audio_path>")
        sys.exit(1)
    
    title_audio = sys.argv[1]
    body_audio = sys.argv[2]
    main(title_audio, body_audio)
