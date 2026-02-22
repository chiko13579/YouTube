import sys
import os
import requests
import time
import base64
import mimetypes
from dotenv import load_dotenv

load_dotenv()

def file_to_data_uri(filepath):
    mime, _ = mimetypes.guess_type(filepath)
    if not mime:
        mime = "application/octet-stream"
    
    with open(filepath, "rb") as f:
        data = f.read()
        encoded = base64.b64encode(data).decode("utf-8")
        
    return f"data:{mime};base64,{encoded}"

def main():
    if len(sys.argv) < 3:
        print("Usage: python run_replicate.py <image_path> <audio_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    audio_path = sys.argv[2]
    
    api_key = os.getenv("REPLICATE_API_KEY")
    if not api_key:
        print("Error: REPLICATE_API_KEY not found.")
        sys.exit(1)

    print(f"Starting Replicate Lip Sync generation (HTTP API)...")
    print(f"Image: {image_path}")
    print(f"Audio: {audio_path}")

    # Convert to Data URIs
    try:
        image_uri = file_to_data_uri(image_path)
        audio_uri = file_to_data_uri(audio_path)
        print("Converted files to Data URIs.")
    except Exception as e:
        print(f"Error reading files: {e}")
        sys.exit(1)

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }

    # SadTalker version (cjwbw)
    version = "a519cc0cfebaaeade068b23899165a11ec76aaa1d2b313d40d214f204ec957a3"
    
    data = {
        "version": version,
        "input": {
            "source_image": image_uri,
            "driven_audio": audio_uri,
            "enhancer": "gfpgan",
            "preprocess": "full",
            "still": True
        }
    }

    print("Sending request to Replicate...")
    try:
        response = requests.post("https://api.replicate.com/v1/predictions", headers=headers, json=data)
        if response.status_code != 201:
            print(f"Error creating prediction: {response.status_code} {response.text}")
            sys.exit(1)
            
        prediction = response.json()
        prediction_id = prediction["id"]
        print(f"Prediction started: {prediction_id}")
        
        # Poll
        while True:
            time.sleep(2)
            poll_resp = requests.get(f"https://api.replicate.com/v1/predictions/{prediction_id}", headers=headers)
            if poll_resp.status_code != 200:
                print(f"Error polling: {poll_resp.status_code}")
                continue
                
            status_data = poll_resp.json()
            status = status_data["status"]
            print(f"Status: {status}")
            
            if status == "succeeded":
                output = status_data["output"]
                print(f"OUTPUT_URL={output}")
                break
            elif status == "failed":
                print(f"Prediction failed: {status_data.get('error')}")
                sys.exit(1)
            elif status == "canceled":
                print("Prediction canceled.")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
