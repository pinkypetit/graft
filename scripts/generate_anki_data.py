import os
import re
import csv
import json
import argparse
import asyncio
import subprocess
import time
import requests
import edge_tts

PAPERS_ROOT = "/Users/petit/Desktop/anki personalizado/papers"
PARETOS_ROOT = "/Users/petit/Desktop/anki personalizado/paretos"
BUILD_ROOT = "/Users/petit/Desktop/anki personalizado/build"
CACHE_PATH = "/Users/petit/Desktop/anki personalizado/cache/dictionary_cache.json"
CURATED_CACHE_PATH = "/Users/petit/Desktop/anki personalizado/cache/curated_cache.json"

# Default TTS Voice (Microsoft Neural SOTA Voice)
DEFAULT_VOICE = "en-US-EmmaNeural"

def load_json_cache(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache {path}: {e}")
    return {}

def save_json_cache(cache, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving cache {path}: {e}")

def fetch_dictionary_info(word, dict_cache):
    if word in dict_cache:
        return dict_cache[word]
        
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    info = {
        "ipa": f"[{word}]",
        "definitions": [],
        "dictionary_example": ""
    }
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                entry = data[0]
                
                # Extract IPA
                phonetics = entry.get('phonetics', [])
                ipa_text = ""
                for p in phonetics:
                    if p.get('text'):
                        ipa_text = p['text']
                        break
                if ipa_text:
                    info['ipa'] = ipa_text
                else:
                    info['ipa'] = entry.get('phonetic', f"[{word}]")
                    
                # Extract definitions
                meanings = entry.get('meanings', [])
                for m in meanings:
                    part_of_speech = m.get('partOfSpeech', '')
                    defs = m.get('definitions', [])
                    for d in defs:
                        if d.get('definition'):
                            info['definitions'].append(f"({part_of_speech}) {d['definition']}")
                            if d.get('example') and not info['dictionary_example']:
                                info['dictionary_example'] = d['example']
                                
        elif response.status_code == 404:
            # Word not found
            pass
    except Exception:
        pass
        
    dict_cache[word] = info
    return info

def find_all_context_sentences(word, category, max_sentences=5):
    cat_dir = os.path.join(PAPERS_ROOT, category)
    if not os.path.exists(cat_dir):
        return []
        
    md_files = [f for f in os.listdir(cat_dir) if f.endswith(".md")]
    candidates = []
    word_pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
    
    for md_file in md_files:
        md_path = os.path.join(cat_dir, md_file)
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Split by sentence endings
            sentences = re.split(r'(?<=[.!?])\s+', content)
            
            for s in sentences:
                s = s.strip().replace('\n', ' ')
                s = re.sub(r'\s+', ' ', s)
                
                if word_pattern.search(s):
                    words_in_s = s.split()
                    # Filter out math equations, table rows, and keep reasonable length
                    if 8 <= len(words_in_s) <= 40 and not any(char in s for char in ['|', '$', '\\', '/']):
                        candidates.append(s)
                        if len(candidates) >= max_sentences:
                            return candidates
        except Exception:
            pass
            
    return candidates

def curate_with_ollama(word, category, raw_sentences, raw_defs):
    prompt = f"""You are an expert lexicographer curating an English vocabulary deck for a professional and academic audience.
The current category/theme is: {category}
Word: {word}

Here are some raw context sentences containing '{word}' found in research papers:
{json.dumps(raw_sentences, indent=2)}

Here are standard dictionary definitions for '{word}':
{json.dumps(raw_defs, indent=2)}

Your task:
1. Analyze if this word is a Spanish word (like 'las', 'los', 'para', 'calor', 'demanda', 'ola'), a proper name/noun (e.g. 'Zhang', 'Chile', 'Poland', 'Thompson'), an acronym/abbreviation (e.g. 'GCM', 'BESS', 'HVDC', 'RCP'), a website/noise (e.g. 'www', 'http', 'doi', 'https'), or not a valid English vocabulary word. If so, you MUST set "skip": true.
2. If it is a valid word, select the dictionary definition that matches how the word is used in the context sentences. If none match or they don't fit the category theme, write a clear, accurate, and concise definition in English.
3. Clean and select the best context sentence from the papers. You MUST remove citations (e.g., [1], [2-4], (Author et al., 2018)), initials, parentheticals, and fix PDF conversion errors (like words stuck together). The sentence must be natural, grammatically correct, and help understand the word's meaning. If the paper sentences are too broken or none exist, write a new clear example sentence where the word's meaning can be inferred from the context.
4. Provide the correct IPA transcription (e.g. /klaɪmət/ or /prɪˌsɪpɪˈteɪʃən/).

Output the result strictly as a JSON object with this exact schema:
{{
  "skip": boolean,
  "ipa": "string (enclosed in forward slashes or brackets)",
  "definition": "string (concise definition)",
  "example": "string (the clean context sentence. Do not bold the word, the script will do it)"
}}"""

    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "qwen2.5:14b",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        }
    }
    
    try:
        response = requests.post("http://localhost:11434/api/chat", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        content = response.json()['message']['content']
        return json.loads(content)
    except Exception as e:
        print(f"    Ollama curation failed: {e}")
        # Return fallback values to be handled
        return {
            "skip": False,
            "ipa": f"[{word}]",
            "definition": raw_defs[0] if raw_defs else f"Related to {word}.",
            "example": raw_sentences[0] if raw_sentences else f"The term relates directly to {word}."
        }

async def generate_edge_tts_async(text, dest_path, voice):
    # Clean text from HTML tags and null bytes
    clean_text = re.sub(r'<[^>]*>', '', text).replace('\x00', '')
    communicate = edge_tts.Communicate(clean_text, voice)
    await communicate.save(dest_path)

def generate_tts_audio(text, dest_path, voice=DEFAULT_VOICE):
    try:
        # Run asynchronous edge-tts
        asyncio.run(generate_edge_tts_async(text, dest_path, voice))
        return True
    except Exception as e:
        print(f"    Edge TTS error for '{text[:20]}...': {e}. Falling back to macOS say.")
        try:
            # Fallback to local macOS say command
            clean_text = re.sub(r'<[^>]*>', '', text).replace('\x00', '').replace('"', '\\"')
            subprocess.run([
                "say",
                "-o", dest_path,
                clean_text
            ], check=True)
            return True
        except Exception as e2:
            print(f"    macOS say fallback failed: {e2}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Generate curated card content, contextual sentences, and TTS audios.")
    parser.add_argument("--category", type=str, required=True, help="Category name (e.g. 'vinos', 'energia')")
    parser.add_argument("--limit", type=int, default=30, help="Number of target cards to curate (default: 30)")
    parser.add_argument("--voice", type=str, default=DEFAULT_VOICE, help=f"edge-tts voice (default: {DEFAULT_VOICE})")
    
    args = parser.parse_args()
    
    staging_dir = os.path.join(BUILD_ROOT, args.category)
    media_dir = os.path.join(staging_dir, "media")
    os.makedirs(media_dir, exist_ok=True)
    
    # Load ranked words list
    csv_path = os.path.join(PARETOS_ROOT, args.category, "ranked_words.csv")
    if not os.path.exists(csv_path):
        print(f"Error: No ranked words CSV found at {csv_path}. Run rank_words.py first.")
        return
        
    ranked_words = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ranked_words.append(row['Word'])
            
    if not ranked_words:
        print(f"No words found in ranked list for category {args.category}.")
        return
        
    print(f"Starting curation of {args.limit} cards for category '{args.category}' using qwen2.5:14b...")
    
    # Load caches
    dict_cache = load_json_cache(CACHE_PATH)
    curated_cache = load_json_cache(CURATED_CACHE_PATH)
    
    deck_data = []
    cards_curated = 0
    words_iterator = iter(ranked_words)
    
    # Iterate through ranked list until we curate exactly 'limit' cards (or run out of words)
    while cards_curated < args.limit:
        try:
            word = next(words_iterator)
        except StopIteration:
            print("\nReached the end of the ranked words list.")
            break
            
        print(f"\nEvaluating word [{cards_curated + 1}/{args.limit} curated]: '{word}'")
        
        # 1. Check if word is already curated in cache
        cache_key = f"{args.category}_{word}"
        if cache_key in curated_cache:
            info = curated_cache[cache_key]
            if info.get('skip'):
                print(f"  Word skipped (cached).")
                continue
            print(f"  Loaded curated content from cache.")
        else:
            # 2. Gather dictionary base info
            dict_info = fetch_dictionary_info(word, dict_cache)
            raw_defs = dict_info['definitions']
            
            # Programmatic safety check: if the word doesn't exist in the English dictionary (404), skip it immediately.
            # This completely blocks Spanish words like "olas", "demanda", "calor" from calling Ollama or being accepted.
            if not raw_defs:
                print(f"  Word skipped: not found in English dictionary (likely a non-English word or typo).")
                curated_cache[cache_key] = {"skip": True}
                continue
            
            # 3. Gather context sentences
            raw_sentences = find_all_context_sentences(word, args.category)
            
            # 4. Curate using local Ollama model
            info = curate_with_ollama(word, args.category, raw_sentences, raw_defs)
            
            # Save to curated cache
            curated_cache[cache_key] = info
            
            if info.get('skip'):
                print(f"  Word skipped by Ollama curation.")
                continue
                
        # Word is accepted
        cards_curated += 1
        ipa = info['ipa']
        definition = info['definition']
        example = info['example']
        
        # Bold the target word in the clean context sentence
        word_pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        # Highlight word
        example_highlighted = word_pattern.sub(lambda m: f"<b>{m.group(0)}</b>", example)
        
        print(f"  Accepted!")
        print(f"  IPA: {ipa}")
        print(f"  Meaning: {definition}")
        print(f"  Example: {example_highlighted}")
        
        # Audio paths
        word_audio_file = f"{args.category}_{word}_word.mp3"
        meaning_audio_file = f"{args.category}_{word}_meaning.mp3"
        example_audio_file = f"{args.category}_{word}_example.mp3"
        
        word_audio_path = os.path.join(media_dir, word_audio_file)
        meaning_audio_path = os.path.join(media_dir, meaning_audio_file)
        example_audio_path = os.path.join(media_dir, example_audio_file)
        
        # Generate neural TTS files
        generate_tts_audio(word, word_audio_path, args.voice)
        generate_tts_audio(definition, meaning_audio_path, args.voice)
        generate_tts_audio(example_highlighted, example_audio_path, args.voice)
        
        deck_data.append({
            "word": word,
            "ipa": ipa,
            "meaning": definition,
            "example": example_highlighted,
            "word_audio": word_audio_file,
            "meaning_audio": meaning_audio_file,
            "example_audio": example_audio_file
        })
        
    # Save caches
    save_json_cache(dict_cache, CACHE_PATH)
    save_json_cache(curated_cache, CURATED_CACHE_PATH)
    
    # Save deck data to build folder
    data_json_path = os.path.join(staging_dir, "deck_data.json")
    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(deck_data, f, ensure_ascii=False, indent=2)
        
    print(f"\nCuration complete. Successfully generated {len(deck_data)} cards for category '{args.category}'.")
    print(f"Card details saved in: {data_json_path}")

if __name__ == "__main__":
    main()
