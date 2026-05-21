import requests
import json
import os
import time
from pathlib import Path

def read_universities():
    """Read university slugs from universities.txt"""
    with open('universities.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()]

def slug_to_wikipedia_title(slug):
    """Convert university slug to Wikipedia page title"""
    # Convert slug to title format
    # e.g., 'massachusetts-institute-of-technology' -> 'Massachusetts Institute of Technology'
    words = slug.split('-')

    # Handle special cases
    special_cases = {
        'massachusetts-institute-of-technology': 'Massachusetts Institute of Technology',
        'stanford-university': 'Stanford University',
        'harvard-university': 'Harvard University',
        'university-of-michigan-ann-arbor': 'University of Michigan',
        'university-of-texas-austin': 'University of Texas at Austin',
        'university-of-california-los-angeles': 'University of California, Los Angeles',
        'georgia-institute-of-technology': 'Georgia Institute of Technology',
        'university-of-florida': 'University of Florida',
        'new-york-university': 'New York University',
        'university-of-southern-california': 'University of Southern California'
    }

    return special_cases.get(slug, ' '.join(word.capitalize() for word in words))

def fetch_wikipedia_page(title):
    """Fetch Wikipedia page content as plain text using the Wikipedia API"""

    # Wikipedia API endpoint
    base_url = "https://en.wikipedia.org/w/api.php"

    # Parameters to get plain text extract
    params = {
        'action': 'query',
        'prop': 'extracts|categories|pageprops',
        'titles': title,
        'explaintext': True,  # Get plain text instead of HTML
        'exsectionformat': 'plain',
        'format': 'json'
    }

    # Wikipedia requires a User-Agent header
    headers = {
        'User-Agent': 'UniRecommenderBot/1.0 (Educational Project; Contact: github.com/user)'
    }

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            print(f"Error fetching {title}: {data['error'].get('info', 'Unknown error')}")
            return None

        # Extract the page data from the query response
        pages = data.get('query', {}).get('pages', {})
        if not pages:
            print(f"No page data found for {title}")
            return None

        # Get the first (and only) page
        page_data = list(pages.values())[0]

        if 'missing' in page_data:
            print(f"Page not found: {title}")
            return None

        return page_data

    except requests.exceptions.RequestException as e:
        print(f"Request failed for {title}: {e}")
        return None

def save_wikipedia_data(slug, data):
    """Save Wikipedia data to JSON file"""
    output_dir = Path('output/wikipedia')
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{slug}.json"

    # Create a clean output structure
    output = {
        'slug': slug,
        'title': data.get('title', ''),
        'pageid': data.get('pageid', ''),
        'text': data.get('extract', ''),  # Plain text content
        'categories': data.get('categories', []),
        'length': len(data.get('extract', ''))
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {output['length']:,} chars for {slug} to {output_file}")

def main(limit=None):
    """Main function to scrape Wikipedia data for all universities"""

    # Change to scraping directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    universities = read_universities()

    if limit:
        universities = universities[:limit]
        print(f"Processing {len(universities)} universities (limited)")
    else:
        print(f"Found {len(universities)} universities to scrape")

    success_count = 0
    failed_universities = []

    for i, slug in enumerate(universities, 1):
        print(f"\n[{i}/{len(universities)}] Processing: {slug}")

        title = slug_to_wikipedia_title(slug)
        print(f"Wikipedia title: {title}")

        data = fetch_wikipedia_page(title)

        if data and 'extract' in data:
            save_wikipedia_data(slug, data)
            success_count += 1
        else:
            failed_universities.append((slug, title))

        # Be respectful to Wikipedia servers
        time.sleep(1)

    print(f"\n{'='*50}")
    print(f"Scraping complete!")
    print(f"Successfully scraped: {success_count}/{len(universities)}")

    if failed_universities:
        print(f"\nFailed to scrape {len(failed_universities)} universities:")
        for slug, title in failed_universities:
            print(f"  - {slug} (Wikipedia: {title})")

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit=limit)
