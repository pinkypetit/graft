import os
import re
from markitdown import MarkItDown

PAPERS_ROOT = "/Users/petit/Desktop/anki personalizado/papers"

def main():
    print("Starting batch PDF to Markdown conversion...")
    md_converter = MarkItDown()
    
    # Scan all directories in PAPERS_ROOT
    categories = [d for d in os.listdir(PAPERS_ROOT) if os.path.isdir(os.path.join(PAPERS_ROOT, d))]
    
    total_converted = 0
    
    for category in categories:
        cat_dir = os.path.join(PAPERS_ROOT, category)
        print(f"\nScanning category: '{category}'...")
        
        pdf_files = [f for f in os.listdir(cat_dir) if f.endswith(".pdf")]
        if not pdf_files:
            print("  No PDF files found.")
            continue
            
        print(f"  Found {len(pdf_files)} PDF files.")
        for pdf_file in pdf_files:
            pdf_path = os.path.join(cat_dir, pdf_file)
            base_name = os.path.splitext(pdf_file)[0]
            md_path = os.path.join(cat_dir, f"{base_name}.md")
            
            if os.path.exists(md_path):
                # Already converted
                continue
                
            print(f"  Converting: {pdf_file} -> {base_name}.md")
            try:
                result = md_converter.convert(pdf_path)
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(result.text_content)
                print(f"    Success.")
                total_converted += 1
            except Exception as e:
                print(f"    Error converting {pdf_file}: {e}")
                
    print(f"\nConversion complete. Converted {total_converted} new files to Markdown.")

if __name__ == "__main__":
    main()
