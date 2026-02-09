import whisper
import json
import os
import budoux
import sys

# Configuration (Defaults)
DEFAULT_AUDIO_FILE = "public/assets/juju_voice.mp3"
DEFAULT_OUTPUT_FILE = "src/subtitles.json"

def transcribe_audio(audio_file, output_file):
    print(f"Loading Whisper model... This might take a moment.")
    model = whisper.load_model("base")
    
    print(f"Transcribing {audio_file} with word timestamps...")
    # Enable word_timestamps
    result = model.transcribe(audio_file, fp16=False, word_timestamps=True)

    # 1. Collect all words with timestamps
    all_words = []
    for segment in result["segments"]:
        all_words.extend(segment.get("words", []))

    if not all_words:
        print("Error: No word timestamps found. Fallback to segments.")
        # Fallback logic could be added here, but for now we proceed
    
    # 2. Get full text and parse with BudouX
    full_text = "".join([w["word"] for w in all_words]).strip()
    parser = budoux.load_default_japanese_parser()
    phrases = parser.parse(full_text)
    
    print("Semantic Phrases (BudouX):", phrases)

    subtitles = []
    fps = 30
    MAX_CHARS_PER_LINE = 14 

    # 3. Group phrases into lines
    lines = []
    current_line = ""
    
    for phrase in phrases:
        if len(current_line) + len(phrase) > MAX_CHARS_PER_LINE:
            if current_line: lines.append(current_line)
            current_line = phrase
        else:
            current_line += phrase
    if current_line:
        lines.append(current_line)

    print("Final Lines:", lines)
    
    # 4. Map lines back to time
    w_idx = 0
    total_words = len(all_words)
    
    for line in lines:
        line_start_time = None
        line_end_time = None
        
        constructed_text = ""
        words_in_line = []
        
        while w_idx < total_words:
            word_obj = all_words[w_idx]
            word_txt = word_obj["word"].strip()
            
            if not line_start_time:
                line_start_time = word_obj["start"]
            
            words_in_line.append(word_obj)
            constructed_text += word_txt
            w_idx += 1
            
            clean_constructed = constructed_text.replace(" ", "")
            clean_line = line.replace(" ", "")
            
            if clean_constructed == clean_line:
                line_end_time = word_obj["end"]
                break
            
            if len(clean_constructed) >= len(clean_line):
                line_end_time = word_obj["end"]
                break
        
        if line_end_time is None and words_in_line:
             line_end_time = words_in_line[-1]["end"]

        if line_start_time is not None:
             start_frame = int(line_start_time * fps)
             end_frame = int(line_end_time * fps)
             
             # Min duration
             if end_frame - start_frame < 10: end_frame = start_frame + 10
             
             subtitles.append({
                "startFrame": start_frame,
                "endFrame": end_frame,
                "text": line
             })
             print(f"[{line_start_time:.2f}s -> {line_end_time:.2f}s] {line}")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(subtitles, f, ensure_ascii=False, indent=2)
        
    # Also save as plain text for reading
    txt_file = output_file.replace(".json", ".txt")
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"\nSuccessfully saved subtitles to {output_file}")
    print(f"Successfully saved plain text to {txt_file}")

if __name__ == "__main__":
    # Check for CLI arguments
    if len(sys.argv) >= 3:
        audio_in = sys.argv[1]
        json_out = sys.argv[2]
    else:
        audio_in = DEFAULT_AUDIO_FILE
        json_out = DEFAULT_OUTPUT_FILE
        print(f"Using default paths: {audio_in} -> {json_out}")

    if not os.path.exists(audio_in):
        print(f"Error: File {audio_in} not found.")
        sys.exit(1)
    
    transcribe_audio(audio_in, json_out)
