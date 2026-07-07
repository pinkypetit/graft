import os
import re
import csv
import math
from collections import Counter

PAPERS_ROOT = "/Users/petit/Desktop/anki personalizado/papers"
PARETOS_ROOT = "/Users/petit/Desktop/anki personalizado/paretos"

# A comprehensive list of English stop words and general academic terms to exclude
STOP_WORDS = set([
    # Standard English stop words
    'the', 'and', 'of', 'to', 'in', 'is', 'for', 'that', 'with', 'on', 'as', 'by', 'it', 'at', 'an', 'are', 'be', 'this',
    'from', 'or', 'which', 'but', 'not', 'they', 'we', 'our', 'their', 'have', 'has', 'had', 'been', 'were', 'was', 'can',
    'will', 'would', 'should', 'could', 'about', 'more', 'also', 'its', 'their', 'there', 'them', 'these', 'those', 'than',
    'then', 'into', 'only', 'other', 'some', 'such', 'who', 'how', 'when', 'where', 'why', 'what', 'which', 'any', 'each',
    'both', 'all', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'first', 'second',
    'third', 'many', 'very', 'here', 'there', 'he', 'she', 'him', 'her', 'his', 'hers', 'me', 'us', 'you', 'your', 'i',
    'my', 'am', 'so', 'if', 'out', 'up', 'down', 'no', 'yes', 'do', 'does', 'did', 'done', 'doing', 'go', 'get', 'make',
    'made', 'take', 'took', 'taken', 'use', 'used', 'using', 'see', 'saw', 'seen', 'come', 'came', 'find', 'found',
    'give', 'gave', 'given', 'keep', 'kept', 'know', 'knew', 'known', 'think', 'thought', 'say', 'said', 'tell', 'told',
    
    # Common academic/research noise words
    'fig', 'figure', 'table', 'results', 'analysis', 'study', 'data', 'model', 'models', 'method', 'methods', 'paper',
    'authors', 'university', 'page', 'pages', 'et', 'al', 'journal', 'research', 'system', 'systems', 'time', 'value',
    'values', 'level', 'levels', 'high', 'low', 'different', 'show', 'shows', 'shown', 'using', 'based', 'new', 'same',
    'used', 'using', 'use', 'within', 'between', 'during', 'under', 'over', 'both', 'either', 'neither', 'through',
    'after', 'before', 'since', 'until', 'while', 'because', 'although', 'though', 'even', 'also', 'too', 'well',
    'particular', 'particularly', 'specific', 'specifically', 'significant', 'significantly', 'different', 'differently',
    'similar', 'similarly', 'general', 'generally', 'common', 'commonly', 'important', 'importance', 'case', 'cases',
    'example', 'examples', 'ie', 'eg', 'etc', 'versus', 'vs', 'per', 'via', 'pro', 'con', 'approach', 'approaches',
    'context', 'contexts', 'process', 'processes', 'factor', 'factors', 'effect', 'effects', 'impact', 'impacts',
    'change', 'changes', 'future', 'present', 'past', 'year', 'years', 'month', 'months', 'day', 'days', 'hour', 'hours',
    'total', 'average', 'mean', 'median', 'std', 'dev', 'deviation', 'percentage', 'percent', 'rate', 'rates', 'ratio',
    'ratios', 'range', 'ranges', 'increase', 'increases', 'increased', 'decrease', 'decreases', 'decreased', 'higher',
    'lower', 'greater', 'less', 'more', 'least', 'most', 'best', 'worst', 'good', 'bad', 'large', 'small', 'larger',
    'smaller', 'major', 'minor', 'main', 'primary', 'secondary', 'key', 'keys', 'central', 'core', 'basic', 'advanced',
    'simple', 'complex', 'single', 'multiple', 'various', 'several', 'number', 'numbers', 'amount', 'amounts',
    'quantity', 'quantities', 'measure', 'measures', 'measured', 'measurement', 'measurements', 'observe', 'observed',
    'observation', 'observations', 'find', 'finds', 'finding', 'findings', 'conclude', 'concludes', 'concluded',
    'conclusion', 'conclusions', 'suggest', 'suggests', 'suggested', 'suggestion', 'suggestions', 'indicate',
    'indicates', 'indicated', 'indication', 'indications', 'discuss', 'discusses', 'discussed', 'discussion',
    'discussions', 'describe', 'describes', 'described', 'description', 'descriptions', 'propose', 'proposes',
    'proposed', 'proposal', 'proposals', 'develop', 'develops', 'developed', 'development', 'developments',
    'perform', 'performs', 'performed', 'performance', 'evaluate', 'evaluates', 'evaluated', 'evaluation',
    'evaluations', 'assess', 'assesses', 'assessed', 'assessment', 'assessments', 'compare', 'compares', 'compared',
    'comparison', 'comparisons', 'relate', 'relates', 'related', 'relation', 'relations', 'relationship', 'relationships',
    'doi', 'org', 'https', 'http', 'arxiv', 'vol', 'volume', 'iss', 'issue', 'pp', 'isbn', 'issn', 'url', 'ref', 'refs',
    'references', 'abstract', 'author', 'authors', 'pub', 'publish', 'publisher', 'published', 'editor', 'editors',
    'editorial', 'guest', 'special', 'topic', 'topics', 'section', 'sections', 'chapter', 'chapters', 'volume', 'volumes',
    
    # Spanish stop words and academic noise to exclude
    'las', 'los', 'para', 'como', 'con', 'del', 'este', 'esta', 'estos', 'estas', 'entre', 'sobre', 'desde',
    'hasta', 'hacia', 'otro', 'otra', 'otros', 'otras', 'tanto', 'tanta', 'tantos', 'tantas', 'como', 'pero',
    'mas', 'suyo', 'suya', 'sus', 'sus', 'una', 'uno', 'unas', 'unos', 'ella', 'ellos', 'ellas', 'nosotros',
    'nosotras', 'usted', 'ustedes', 'bajo', 'donde', 'cuando', 'quien', 'quienes', 'cual', 'cuales', 'cuyo',
    'cuya', 'cuyos', 'cuyas', 'cambio', 'climatico', 'chile', 'calor', 'demanda', 'electrica', 'olas', 'efectos',
    'contexto', 'estudio', 'analisis', 'datos', 'modelo', 'metodo', 'metodos', 'resultados', 'figura', 'tabla'
])

def clean_and_tokenize(text):
    # Find all words (preserving case)
    raw_words = re.findall(r'\b[a-zA-Z]{3,20}\b', text)
    
    # We will count capitalization ratios to filter out proper nouns
    word_counts = {}
    cap_counts = {}
    
    for w in raw_words:
        # Filter out acronyms (all-uppercase words of length >= 3 like GCM, BESS, HVDC, RCP, SDG)
        if w.isupper() and len(w) >= 3:
            continue
            
        low_w = w.lower()
        if low_w in STOP_WORDS:
            continue
            
        # Count capitalization (only if it starts with uppercase but is not all uppercase)
        is_cap = w[0].isupper() and not w.isupper()
        
        word_counts[low_w] = word_counts.get(low_w, 0) + 1
        if is_cap:
            cap_counts[low_w] = cap_counts.get(low_w, 0) + 1
            
    # Filter out words that are capitalized in more than 40% of their occurrences (proper nouns/names)
    filtered_words = []
    for word, count in word_counts.items():
        cap_ratio = cap_counts.get(word, 0) / count
        # Proper nouns like Chile, Poland, Zhang, Thompson are capitalized in the papers
        if cap_ratio > 0.4:
            continue
        filtered_words.extend([word] * count)
        
    return filtered_words

def main():
    print("Starting word extraction and Pareto ranking...")
    
    # 1. Scan folders to find all categories
    categories = [d for d in os.listdir(PAPERS_ROOT) if os.path.isdir(os.path.join(PAPERS_ROOT, d))]
    
    # Category collections of words
    cat_word_counts = {}
    
    # Total document frequency for IDF
    # A "document" here is a category directory
    all_words = set()
    
    for category in categories:
        cat_dir = os.path.join(PAPERS_ROOT, category)
        md_files = [f for f in os.listdir(cat_dir) if f.endswith(".md")]
        
        if not md_files:
            continue
            
        print(f"Processing category '{category}' with {len(md_files)} markdown files...")
        
        # Combine all text for this category
        cat_text = ""
        for md_file in md_files:
            md_path = os.path.join(cat_dir, md_file)
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    cat_text += f.read() + "\n"
            except Exception as e:
                print(f"  Error reading {md_file}: {e}")
                
        # Clean and tokenize
        tokens = clean_and_tokenize(cat_text)
        cat_word_counts[category] = Counter(tokens)
        all_words.update(cat_word_counts[category].keys())
        
    num_categories = len(cat_word_counts)
    if num_categories == 0:
        print("No categories with processed papers found.")
        return
        
    # 2. Compute Document Frequency (DF) of words across categories
    # DF = number of categories in which the word appears at least 3 times (to avoid typos/rare noise)
    df = {}
    for word in all_words:
        count_in_cats = 0
        for category, counts in cat_word_counts.items():
            if counts[word] >= 3:
                count_in_cats += 1
        df[word] = max(1, count_in_cats)  # Avoid division by zero
        
    # 3. Compute TF-IDF Score for each word in each category
    for category, counts in cat_word_counts.items():
        print(f"\nRanking words for category: '{category}'...")
        total_tokens = sum(counts.values())
        if total_tokens == 0:
            continue
            
        scored_words = []
        for word, tf in counts.items():
            # Only consider words that appear at least 3 times in this category
            if tf < 3:
                continue
                
            # Relative TF (Term Frequency)
            rel_tf = tf / total_tokens
            # IDF (Inverse Document Frequency)
            # Log formula with smoothing
            idf = math.log(num_categories / df[word]) + 1.0
            
            # Final TF-IDF Score
            score = rel_tf * idf
            
            scored_words.append({
                'Word': word,
                'TF': tf,
                'IDF': round(idf, 3),
                'Score': round(score * 1000, 5) # Scale for readability
            })
            
        # Sort by Score descending
        scored_words.sort(key=lambda x: x['Score'], reverse=True)
        
        # Save to paretos/<category>/ranked_words.csv
        dest_dir = os.path.join(PARETOS_ROOT, category)
        os.makedirs(dest_dir, exist_ok=True)
        dest_file = os.path.join(dest_dir, "ranked_words.csv")
        
        with open(dest_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Word", "Frequency", "IDF", "Score"])
            for sw in scored_words:
                writer.writerow([sw['Word'], sw['TF'], sw['IDF'], sw['Score']])
                
        print(f"  Saved {len(scored_words)} ranked words to {dest_file}")
        
    print("\nPareto ranking complete.")

if __name__ == "__main__":
    main()
