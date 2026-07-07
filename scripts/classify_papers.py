import os
import shutil
import re
from markitdown import MarkItDown

# Define paths
PAPERS_ROOT = "/Users/petit/Desktop/anki personalizado/papers"

# Define categories and their search keywords (case-insensitive)
CATEGORIES = {
    "clima": [
        r"\bclimate\b", r"\btemperature\b", r"\bprecipitation\b", r"\bdrought\b", 
        r"\bweather\b", r"\bwarming\b", r"\bmeteorological\b", r"\bheatwave\b", 
        r"\bhydrological\b", r"\bcmip\b", r"\bel nino\b", r"\bprecipitation\b"
    ],
    "energia": [
        r"\belectricity\b", r"\bgrid\b", r"\bpower\b", r"\benergy\b", 
        r"\bbess\b", r"\bbattery\b", r"\btransmission\b", r"\bsmart-meter\b", 
        r"\bcooling\b", r"\bheating\b", r"\bair-conditioning\b", r"\bwind\b", 
        r"\bsolar\b", r"\bphotovoltaic\b", r"\bcurtailment\b"
    ],
    "ciencia_de_datos": [
        r"\bmachine learning\b", r"\bdeep learning\b", r"\bneural network\b", 
        r"\bconvolutional\b", r"\btransformer\b", r"\brandom forest\b", 
        r"\bartificial intelligence\b", r"\bclustering\b", r"\bpredictive model\b",
        r"\bcnn\b", r"\blstm\b", r"\bsuper-resolve\b", r"\bemulator\b"
    ],
    "estadistica": [
        r"\bstatistical\b", r"\bgeneralized additive\b", r"\bregression\b", 
        r"\bbias correction\b", r"\bquantile mapping\b", r"\bensemble\b", 
        r"\bprobability\b", r"\bvariance\b", r"\bdistribution\b",
        r"\bgam\b", r"\bdownscaling\b"
    ],
    "programacion": [
        r"\bprogramming\b", r"\bsoftware\b", r"\bpython\b", r"\bcode\b", 
        r"\bgit\b", r"\bdatabase\b", r"\bapi\b", r"\bserver\b", 
        r"\balgorithm\b"
    ],
    "vinos": [
        r"\bwine\b", r"\bviticulture\b", r"\boenology\b", r"\bgrape\b", 
        r"\bfermentation\b", r"\bwinery\b"
    ]
}

def main():
    print("Starting classification and conversion pipeline...")
    
    # Initialize MarkItDown
    md = MarkItDown()
    
    # Create target directories
    for cat in CATEGORIES.keys():
        os.makedirs(os.path.join(PAPERS_ROOT, cat), exist_ok=True)
    os.makedirs(os.path.join(PAPERS_ROOT, "ciencia"), exist_ok=True) # Fallback category
    
    # Scan for PDF files in the root folder
    pdf_files = [f for f in os.listdir(PAPERS_ROOT) if f.endswith(".pdf") and os.path.isfile(os.path.join(PAPERS_ROOT, f))]
    
    if not pdf_files:
        print("No PDF files found in the root papers/ folder.")
        return
        
    print(f"Found {len(pdf_files)} PDF files to classify and convert.")
    
    for i, pdf_file in enumerate(pdf_files, 1):
        pdf_path = os.path.join(PAPERS_ROOT, pdf_file)
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file}")
        
        try:
            # 1. Convert PDF to markdown text
            result = md.convert(pdf_path)
            text = result.text_content
            
            # 2. Count matches for each category
            scores = {}
            for cat, patterns in CATEGORIES.items():
                score = 0
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    score += len(matches)
                scores[cat] = score
            
            # Print scores for debugging
            print(f"  Scores: {scores}")
            
            # 3. Determine the best category (must have at least a few keywords, otherwise goes to 'ciencia')
            best_cat = "ciencia"
            max_score = 0
            for cat, score in scores.items():
                if score > max_score:
                    max_score = score
                    best_cat = cat
            
            if max_score < 5:  # If very low keyword count, default to general science
                best_cat = "ciencia"
                
            print(f"  Classified as: {best_cat} (Score: {max_score})")
            
            # 4. Save markdown to the categorized directory
            base_name = os.path.splitext(pdf_file)[0]
            # Replace characters that might cause path issues
            clean_base_name = re.sub(r'[^\w\-\. ]', '_', base_name)
            
            md_filename = f"{clean_base_name}.md"
            md_dest_path = os.path.join(PAPERS_ROOT, best_cat, md_filename)
            with open(md_dest_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            # 5. Move PDF to the categorized directory
            pdf_dest_path = os.path.join(PAPERS_ROOT, best_cat, f"{clean_base_name}.pdf")
            shutil.move(pdf_path, pdf_dest_path)
            
            print(f"  Successfully processed and moved to papers/{best_cat}/")
            
        except Exception as e:
            print(f"  Error processing {pdf_file}: {e}")

if __name__ == "__main__":
    main()
