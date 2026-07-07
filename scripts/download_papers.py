import os
import re
import argparse
import time
import requests
import xml.etree.ElementTree as ET

PAPERS_ROOT = "/Users/petit/Desktop/anki personalizado/papers"

def sanitize_filename(name):
    clean = re.sub(r'[^\w\-\. ]', '_', name)
    return clean[:100].strip()

def download_pdf(url, dest_path):
    print(f"  Downloading from: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '').lower()
        if 'html' in content_type:
            print("  Warning: URL returned HTML instead of PDF. Skipping.")
            return False
            
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"  Successfully saved to: {dest_path}")
        return True
    except Exception as e:
        print(f"  Failed to download PDF: {e}")
        return False

def search_semantic_scholar(query, limit=5):
    print(f"Searching Semantic Scholar for: '{query}'...")
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,year,openAccessPdf,authors"
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        print(f"Error querying Semantic Scholar: {e}")
        return None

def search_arxiv(query, limit=5):
    print(f"Fallback: Searching arXiv for: '{query}'...")
    # Format query for arXiv URL
    formatted_query = query.replace(" ", "+")
    url = f"http://export.arxiv.org/api/query?search_query=all:{formatted_query}&max_results={limit}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.content)
        # XML namespaces used by arXiv
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        papers = []
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
            published = entry.find('atom:published', ns).text
            year = published.split('-')[0] if published else 'Unknown'
            
            authors = []
            for author in entry.findall('atom:author', ns):
                name = author.find('atom:name', ns).text
                authors.append({'name': name})
                
            pdf_url = None
            for link in entry.findall('atom:link', ns):
                if link.attrib.get('title') == 'pdf' or link.attrib.get('type') == 'application/pdf':
                    pdf_url = link.attrib.get('href')
                    # Make sure it's direct pdf url
                    if pdf_url and not pdf_url.endswith('.pdf'):
                        pdf_url += ".pdf"
                    break
            
            if not pdf_url:
                # Construct default PDF url from ID
                id_url = entry.find('atom:id', ns).text
                arxiv_id = id_url.split('/abs/')[-1]
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                
            papers.append({
                'title': title,
                'year': year,
                'authors': authors,
                'openAccessPdf': {'url': pdf_url}
            })
            
        return papers
    except Exception as e:
        print(f"Error querying arXiv: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Download open-access papers based on a search query and organize them by category.")
    parser.add_argument("--query", type=str, required=True, help="Search query (e.g. 'wine chemistry', 'BESS grid stability')")
    parser.add_argument("--category", type=str, required=True, help="Category subfolder (e.g. 'vinos', 'energia', 'clima')")
    parser.add_argument("--limit", type=int, default=5, help="Number of papers to search for (default: 5)")
    
    args = parser.parse_args()
    
    # Create target directory
    cat_dir = os.path.join(PAPERS_ROOT, args.category)
    os.makedirs(cat_dir, exist_ok=True)
    
    # Try Semantic Scholar first
    papers = search_semantic_scholar(args.query, limit=args.limit)
    
    # If Semantic Scholar failed or hit rate limit (returns None), try arXiv
    if papers is None:
        papers = search_arxiv(args.query, limit=args.limit)
        
    if not papers:
        print("No papers found on either Semantic Scholar or arXiv.")
        return
        
    print(f"Found {len(papers)} candidate papers. Starting downloads...")
    downloaded_count = 0
    for paper in papers:
        title = paper.get('title', 'Unknown Title')
        year = paper.get('year', 'Unknown Year')
        print(f"\nPaper found: {title} ({year})")
        
        pdf_info = paper.get('openAccessPdf')
        if not pdf_info or not pdf_info.get('url'):
            print("  No PDF URL available for this paper. Skipping.")
            continue
            
        pdf_url = pdf_info['url']
        
        authors = paper.get('authors', [])
        author_name = authors[0].get('name', 'Unknown') if authors else 'Unknown'
        author_last = author_name.split()[-1] if ' ' in author_name else author_name
        
        safe_title = sanitize_filename(title)
        filename = f"{author_last} - {year} - {safe_title}.pdf"
        dest_path = os.path.join(cat_dir, filename)
        
        if os.path.exists(dest_path):
            print(f"  File already exists: {filename}. Skipping.")
            continue
            
        success = download_pdf(pdf_url, dest_path)
        if success:
            downloaded_count += 1
            time.sleep(2)
            
    print(f"\nDone. Downloaded {downloaded_count} papers into '{args.category}/'.")

if __name__ == "__main__":
    main()
