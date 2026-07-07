import os
import sys
import json
import argparse
import genanki
import subprocess

BUILD_ROOT = "/Users/petit/Desktop/anki personalizado/build"

# Model and Deck ID base numbers
MODEL_ID_BASE = 1434531250000
DECK_ID_BASE = 1543210000

def get_unique_id(name, base):
    # Hash name to generate a unique but deterministic ID
    h = abs(hash(name)) % 100000
    return base + h

def create_silence_file(dest_dir):
    silence_file = "_1sec.m4a"
    silence_path = os.path.join(dest_dir, silence_file)
    if not os.path.exists(silence_path):
        # Speak a space to generate a short silence
        subprocess.run(["say", " ", "-o", silence_path])
    return silence_file, silence_path

def main():
    parser = argparse.ArgumentParser(description="Build Anki APKG deck from generated card data.")
    parser.add_argument("--category", type=str, required=True, help="Category name (e.g. 'vinos', 'energia')")
    parser.add_argument("--output", type=str, default="", help="Path to output .apkg file")
    
    args = parser.parse_args()
    
    category_title = args.category.capitalize()
    staging_dir = os.path.join(BUILD_ROOT, args.category)
    media_dir = os.path.join(staging_dir, "media")
    data_json_path = os.path.join(staging_dir, "deck_data.json")
    
    if not os.path.exists(data_json_path):
        print(f"Error: No card data found at {data_json_path}. Run generate_anki_data.py first.")
        sys.exit(1)
        
    with open(data_json_path, "r", encoding="utf-8") as f:
        deck_data = json.load(f)
        
    print(f"Loaded {len(deck_data)} cards for category '{args.category}'...")
    
    # Generate 1-second silence file in media directory
    silence_name, silence_path = create_silence_file(media_dir)
    
    # Generate deterministic unique IDs
    model_id = get_unique_id(args.category + "_model", MODEL_ID_BASE)
    deck_id = get_unique_id(args.category + "_deck", DECK_ID_BASE)
    
    # Define Anki Model (matching 4000 EEW styling)
    css_style = """
    .card {
     font-family: arial;
     font-size: 150%;
     text-align: center;
     color: Black;
     background-color: black;
    }

    #rubric {
      text-align: left;
      padding: 4px;
      padding-left: 10px;
      padding-right: 10px;
      margin-bottom: 10px;
      background: #1d6695;
      color: white;
      font-weight: 500;
    }

    img {
        max-width: 100%;
        height: auto;
        width: 300px;
        border-radius: 20px;
    }
    """
    
    front_template = f"""
    <div id="rubric">Technical English: {category_title}</div>
    <div style='font-family: Arial; font-size: 70px; color: #FF80DD;'>{{{{Word}}}}</div>
    {{{{Sound}}}}<hr>
    <div style='font-family: Arial; font-size: 70px; color: #FF80DD;'>{{{{IPA}}}}</div>
    """
    
    back_template = f"""
    <div style='font-family: Arial; color: #FF80DD;'>{{{{Word}}}}</div>
    <hr>
    {{{{Image}}}}
    <hr>
    <div style='font-family: Arial; color: #00aaaa; text-align: left;'>
    Meaning: {{{{Meaning}}}}</div>
    <hr>
    <div style='font-family: Arial; color: #9CFFFA; text-align: left;'>
    &nbsp;→&nbsp;Example: {{{{Example}}}}</div>

    {{{{Sound_Meaning}}}}
    [sound:{silence_name}]
    {{{{Sound_Example}}}}
    """
    
    anki_model = genanki.Model(
        model_id,
        f"Technical English - {category_title}",
        fields=[
            {"name": "Word"},
            {"name": "Image"},
            {"name": "Sound"},
            {"name": "Sound_Meaning"},
            {"name": "Sound_Example"},
            {"name": "Meaning"},
            {"name": "Example"},
            {"name": "IPA"}
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": front_template,
                "afmt": back_template
            }
        ],
        css=css_style
    )
    
    # Define Anki Deck
    anki_deck = genanki.Deck(
        deck_id,
        f"Technical English::{category_title}"
    )
    
    # Build package media list
    media_files = []
    # Add the silence file
    media_files.append(silence_path)
    
    # Add notes to deck
    for card in deck_data:
        word_audio_path = os.path.join(media_dir, card['word_audio'])
        meaning_audio_path = os.path.join(media_dir, card['meaning_audio'])
        example_audio_path = os.path.join(media_dir, card['example_audio'])
        
        # Verify media files exist
        if not os.path.exists(word_audio_path) or not os.path.exists(meaning_audio_path) or not os.path.exists(example_audio_path):
            print(f"Warning: Media files for '{card['word']}' are missing. Skipping note.")
            continue
            
        media_files.extend([word_audio_path, meaning_audio_path, example_audio_path])
        
        # Instantiate Note
        # Refinements inspired by:
        # - genanki (https://github.com/kerrickstaley/genanki): Using genanki.guid_for to generate 
        #   stable, deterministic GUIDs based on category and word. This ensures that rebuilding the 
        #   deck updates existing notes in-place and preserves user review scheduling history (FSRS state).
        # - AnkiDeckBuilder (https://github.com/nchagti/AnkiDeckBuilder): Using hierarchical tags 
        #   (e.g., Category::Subcategory) to allow easy searching and targeted filtering inside Anki.
        note = genanki.Note(
            model=anki_model,
            fields=[
                card['word'],                         # Word
                "",                                   # Image (empty for now)
                f"[sound:{card['word_audio']}]",       # Sound
                f"[sound:{card['meaning_audio']}]",    # Sound_Meaning
                f"[sound:{card['example_audio']}]",    # Sound_Example
                card['meaning'],                      # Meaning
                card['example'],                      # Example
                card['ipa']                           # IPA
            ],
            guid=genanki.guid_for(args.category, card['word']),
            tags=["Technical_English", f"Technical_English::{category_title}"]
        )
        anki_deck.add_note(note)
        
    # Write to APKG package
    output_filename = args.output if args.output else f"Technical_English_{category_title}.apkg"
    
    # Make sure output is in workspace root by default
    if not os.path.isabs(output_filename):
        output_filename = os.path.join("/Users/petit/Desktop/anki personalizado", output_filename)
        
    print(f"Creating package with {len(anki_deck.notes)} notes and {len(media_files)} media files...")
    
    package = genanki.Package(anki_deck)
    package.media_files = media_files
    
    package.write_to_file(output_filename)
    print(f"Successfully compiled deck: {output_filename}")

if __name__ == "__main__":
    main()
