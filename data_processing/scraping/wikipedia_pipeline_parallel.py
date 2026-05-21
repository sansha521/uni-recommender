import pandas as pd
import requests
import json
import os
import time
import re
from pathlib import Path
from threading import Thread, Lock
from queue import Queue

# Thread-safe file writing
file_lock = Lock()

def normalize_name_to_slug(name):
    """Convert university name to a slug for filename"""
    if pd.isna(name) or not name:
        return None

    # Remove quotes and special characters
    name = str(name).strip('"').strip("'")

    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')

    return slug

def fetch_wikipedia_page(university_name):
    """Fetch Wikipedia page content as plain text"""

    base_url = "https://en.wikipedia.org/w/api.php"

    # Parameters to get plain text extract
    params = {
        'action': 'query',
        'prop': 'extracts',
        'titles': university_name,
        'explaintext': True,
        'exsectionformat': 'plain',
        'format': 'json',
        'redirects': 1  # Follow redirects automatically
    }

    headers = {
        'User-Agent': 'UniRecommenderBot/1.0 (Educational Project; Contact: github.com/user)'
    }

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            return None, f"API Error: {data['error'].get('info', 'Unknown error')}"

        pages = data.get('query', {}).get('pages', {})
        if not pages:
            return None, "No page data found"

        page_data = list(pages.values())[0]

        if 'missing' in page_data:
            return None, "Page not found"

        text = page_data.get('extract', '')

        # Check if we got meaningful content
        if not text or len(text) < 100:
            return None, "No content or content too short"

        return {
            'title': page_data.get('title', ''),
            'text': text,
            'length': len(text)
        }, None

    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"

def save_to_jsonl(university_name, wiki_data, output_file):
    """Thread-safe append to JSONL file"""

    # Minimal structure: just name and text
    output = {
        'name': university_name,
        'text': wiki_data['text']
    }

    # Thread-safe file writing
    with file_lock:
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(output, ensure_ascii=False) + '\n')

def load_scraped_names(output_file):
    """Load names of already scraped universities from JSONL file"""
    if not output_file.exists():
        return set()

    scraped_names = set()
    with open(output_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                scraped_names.add(data['name'])
            except:
                continue

    return scraped_names

def worker(task_queue, output_path, results, print_lock):
    """Worker thread to process universities from queue"""

    while True:
        task = task_queue.get()
        if task is None:
            break

        university_name, country_name, task_num, total_tasks = task

        # Fetch from Wikipedia
        wiki_data, error = fetch_wikipedia_page(university_name)

        if wiki_data:
            try:
                save_to_jsonl(university_name, wiki_data, output_path)
                with print_lock:
                    print(f"[{task_num}/{total_tasks}] ✓ {university_name} ({wiki_data['length']:,} chars)")
                results['success'] += 1
            except Exception as e:
                with print_lock:
                    print(f"[{task_num}/{total_tasks}] ✗ {university_name}: Save error")
                results['failed'].append((university_name, f"Save error: {e}"))
        else:
            with print_lock:
                print(f"[{task_num}/{total_tasks}] ✗ {university_name}: {error}")
            results['failed'].append((university_name, error))

        # Be respectful to Wikipedia servers (each worker waits 1 second)
        time.sleep(1)
        task_queue.task_done()

def main(csv_path, country=None, limit=None, output_file='output/wikipedia_us_universities.jsonl', workers=5):
    """
    Main pipeline to scrape Wikipedia data from baseline_df_full.csv (with parallel workers)

    Args:
        csv_path: Path to baseline_df_full.csv
        country: Filter by country (e.g., 'United States', 'India')
        limit: Maximum number of universities to scrape
        output_file: Path to output JSONL file
        workers: Number of parallel workers (default 5)
    """

    # Read the CSV
    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Total universities in CSV: {len(df):,}")

    # Filter by country if specified
    if country:
        df = df[df['country'].str.strip() == country]
        print(f"Filtered to {len(df):,} universities in {country}")

    # Remove rows with missing names
    df = df.dropna(subset=['name'])
    df = df[df['name'].str.strip() != '']
    print(f"Universities with valid names: {len(df):,}")

    # Apply limit
    if limit:
        df = df.head(limit)
        print(f"Limited to {len(df)} universities")

    # Create output directory if needed
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load already scraped universities
    scraped_names = load_scraped_names(output_path)
    print(f"Already scraped: {len(scraped_names)} universities")

    # Create task queue
    task_queue = Queue()
    print_lock = Lock()

    # Shared results dictionary
    results = {
        'success': len(scraped_names),
        'failed': []
    }

    # Add universities to queue
    task_num = 0
    total_to_scrape = 0
    for idx, row in df.iterrows():
        university_name = row['name'].strip('"').strip("'").strip()
        country_name = row.get('country', 'Unknown')

        # Skip if already scraped
        if university_name in scraped_names:
            continue

        task_num += 1
        total_to_scrape += 1

    # Reset and populate queue
    task_num = 0
    for idx, row in df.iterrows():
        university_name = row['name'].strip('"').strip("'").strip()
        country_name = row.get('country', 'Unknown')

        # Skip if already scraped
        if university_name in scraped_names:
            continue

        task_num += 1
        task_queue.put((university_name, country_name, task_num, total_to_scrape))

    print(f"\n{'='*60}")
    print(f"Starting Wikipedia scraping with {workers} workers...")
    print(f"Output: {output_file}")
    print(f"Tasks to process: {total_to_scrape}")
    print(f"{'='*60}\n")

    # Start worker threads
    threads = []
    for i in range(workers):
        t = Thread(target=worker, args=(task_queue, output_path, results, print_lock))
        t.start()
        threads.append(t)

    # Wait for all tasks to complete
    task_queue.join()

    # Stop workers
    for i in range(workers):
        task_queue.put(None)
    for t in threads:
        t.join()

    # Summary
    print(f"\n{'='*60}")
    print(f"Scraping complete!")
    print(f"{'='*60}")
    print(f"Total scraped: {results['success']}")
    print(f"Newly scraped: {total_to_scrape}")
    print(f"Failed: {len(results['failed'])}")

    if results['failed']:
        print(f"\nFailed universities:")
        for name, error in results['failed'][:20]:  # Show first 20
            print(f"  - {name}: {error}")
        if len(results['failed']) > 20:
            print(f"  ... and {len(results['failed']) - 20} more")

if __name__ == "__main__":
    import sys

    # Default path to CSV (relative to project root)
    csv_path = "../baseline_df_full.csv"

    # Parse command line arguments
    country = None
    limit = None
    workers = 5
    output_file = 'output/wikipedia_universities.jsonl'

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == '--workers':
            workers = int(sys.argv[i + 1])
            i += 2
        elif arg.isdigit():
            limit = int(arg)
            i += 1
        else:
            country = arg
            # Set output file based on country
            if country == "United States":
                output_file = 'output/wikipedia_us_universities.jsonl'
            elif country == "India":
                output_file = 'output/wikipedia_india_universities.jsonl'
            else:
                # Use normalized country name for file
                safe_country = country.lower().replace(' ', '_')
                output_file = f'output/wikipedia_{safe_country}_universities.jsonl'
            i += 1

    main(csv_path, country=country, limit=limit, output_file=output_file, workers=workers)
