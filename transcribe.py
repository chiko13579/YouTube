import whisper
import json
import os
import budoux
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configuration (Defaults)
DEFAULT_AUDIO_FILE = "public/assets/juju_voice.mp3"
DEFAULT_OUTPUT_FILE = "src/subtitles.json"

def proofread_subtitles(subtitles):
    """
    Use GPT-4o to check for typos and unnatural line breaks in Japanese.
    Expected Input: List of {startFrame, endFrame, text}
    """
    if not OPENAI_API_KEY:
        print("Notice: OPENAI_API_KEY not found. Skipping AI proofreading.")
        return subtitles
    
    print("\n🤖 AI Proofreading in progress (GPT-4o)...")
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Prepare prompt
    # We send the array and ask for the same array back with corrected text.
    # To save tokens, we might just send the text list, but keeping structure is safer for mapping back.
    
    start_time = subtitles[0]['startFrame'] if subtitles else 0
    # Simplified structure for AI to process easier: index, text
    lines_for_ai = [{"index": i, "text": s["text"]} for i, s in enumerate(subtitles)]
    
    system_prompt = (
        "You are a professional Japanese video subtitle editor. "
        "Your task is to proofread the following subtitles to ensure they sound like natural, spoken Japanese.\n"
        "1. Aggressively correct unnatural phrasing, grammar errors, and potential mistranscriptions.\n"
        "   - Example: 'あー幸せだなと思いやき' -> '『あー幸せ』と呟き' (detect context of 'muttering' or 'thinking')\n"
        "   - Example: '幸せ突破やき' -> '幸せだったやき' or '幸せと呟き' (fix nonsensical words)\n"
        "2. Ensure the tone is consistent and appropriate for a narration.\n"
        "3. Do NOT change the number of lines. The index MUST match exactly.\n"
        "4. Return ONLY a JSON object: {\"corrections\": [{\"index\": 0, \"text\": \"corrected text\"}, ...]}\n"
        "If a line is already natural, return it as is."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(lines_for_ai, ensure_ascii=False)}
            ],
            response_format={"type": "json_object"}
        )
        
        result_content = response.choices[0].message.content
        data = json.loads(result_content)
        corrections = data.get("corrections", [])
        
        # Apply corrections
        for corr in corrections:
            idx = corr.get("index")
            new_text = corr.get("text")
            
            if idx is not None and 0 <= idx < len(subtitles):
                old_text = subtitles[idx]["text"]
                if old_text != new_text:
                    print(f"  [Fix] {old_text} -> {new_text}")
                    subtitles[idx]["text"] = new_text
                    
        print("✅ AI Proofreading complete.\n")
        return subtitles

    except Exception as e:
        print(f"⚠️ AI Proofreading failed: {e}")
        return subtitles


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
        force_break = False
        if phrase.endswith("。"):
             force_break = True

        if len(current_line) + len(phrase) > MAX_CHARS_PER_LINE:
            if current_line: lines.append(current_line)
            current_line = phrase
        else:
            current_line += phrase
        
        if force_break:
            lines.append(current_line)
            current_line = ""
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
             # print(f"[{line_start_time:.2f}s -> {line_end_time:.2f}s] {line}")
    
    # --- AI Proofreading Step ---
    subtitles = proofread_subtitles(subtitles)
    # ----------------------------

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(subtitles, f, ensure_ascii=False, indent=2)
        
    # Also save as plain text for reading
    txt_file = output_file.replace(".json", ".txt")
    with open(txt_file, "w", encoding="utf-8") as f:
        full_text_proofread = "".join([s["text"] for s in subtitles])
        f.write(full_text_proofread)

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
