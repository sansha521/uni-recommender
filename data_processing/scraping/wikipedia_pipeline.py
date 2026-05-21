import pandas as pd
import requests
import json
import os
import time
import re
from pathlib import Path

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
    """Append Wikipedia data to JSONL file (one line per university)"""

    # Minimal structure: just name and text
    output = {
        'name': university_name,
        'text': wiki_data['text']
    }

    # Append to JSONL file
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

def main(csv_path, country=None, limit=None, output_file='output/wikipedia_us_universities.jsonl'):
    """
    Main pipeline to scrape Wikipedia data from baseline_df_full.csv

    Args:
        csv_path: Path to baseline_df_full.csv
        country: Filter by country (e.g., 'United States', 'India')
        limit: Maximum number of universities to scrape
        output_file: Path to output JSONL file
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

    # Track results
    success_count = len(scraped_names)
    failed = []
    processed = 0

    print(f"\n{'='*60}")
    print(f"Starting Wikipedia scraping...")
    print(f"Output: {output_file}")
    print(f"{'='*60}\n")

    for idx, row in df.iterrows():
        university_name = row['name'].strip('"').strip("'").strip()
        country_name = row.get('country', 'Unknown')

        # Check if already scraped
        if university_name in scraped_names:
            continue

        processed += 1
        print(f"[{processed}/{len(df) - len(scraped_names)}] {university_name} ({country_name})")

        # Fetch from Wikipedia
        wiki_data, error = fetch_wikipedia_page(university_name)

        if wiki_data:
            try:
                save_to_jsonl(university_name, wiki_data, output_path)
                print(f"  ✓ Saved {wiki_data['length']:,} chars")
                success_count += 1
                scraped_names.add(university_name)
            except Exception as e:
                print(f"  ✗ Failed to save: {e}")
                failed.append((university_name, f"Save error: {e}"))
        else:
            print(f"  ✗ {error}")
            failed.append((university_name, error))

        # Be respectful to Wikipedia servers
        time.sleep(1)

    # Summary
    print(f"\n{'='*60}")
    print(f"Scraping complete!")
    print(f"{'='*60}")
    print(f"Total scraped: {success_count}")
    print(f"Newly scraped: {processed}")
    print(f"Failed: {len(failed)}")

    if failed:
        print(f"\nFailed universities:")
        for name, error in failed[:20]:  # Show first 20
            print(f"  - {name}: {error}")
        if len(failed) > 20:
            print(f"  ... and {len(failed) - 20} more")

if __name__ == "__main__":
    import sys

    # Default path to CSV (relative to project root)
    csv_path = "../baseline_df_full.csv"

    # Parse command line arguments
    country = None
    limit = None
    output_file = 'output/wikipedia_universities.jsonl'

    if len(sys.argv) > 1:
        # Check if first arg is a number (limit) or country name
        if sys.argv[1].isdigit():
            limit = int(sys.argv[1])
        else:
            country = sys.argv[1]
            # Set output file based on country
            if country == "United States":
                output_file = 'output/wikipedia_us_universities.jsonl'
            elif country == "India":
                output_file = 'output/wikipedia_india_universities.jsonl'
            else:
                # Use normalized country name for file
                safe_country = country.lower().replace(' ', '_')
                output_file = f'output/wikipedia_{safe_country}_universities.jsonl'

    if len(sys.argv) > 2:
        limit = int(sys.argv[2])

    main(csv_path, country=country, limit=limit, output_file=output_file)
