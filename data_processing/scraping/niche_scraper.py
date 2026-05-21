#!/usr/bin/env python3
"""
Niche.com scraper for university qualitative data.
Scrapes grades, rankings, and student reviews for each university.
"""

import json
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
UNIVERSITIES_FILE = Path(__file__).parent / "universities.txt"


def scrape_overview(page, slug: str) -> dict:
    """Scrape the main university page for grades and rankings."""
    url = f"https://www.niche.com/colleges/{slug}/"
    print(f"  Fetching overview: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(random.uniform(2, 4))

    data = {"slug": slug, "url": url, "grades": {}, "rankings": [], "overview": {}}

    # University name
    try:
        data["name"] = page.locator("h1").first.inner_text(timeout=5000).strip()
    except Exception:
        data["name"] = slug

    # Overall Niche grade
    try:
        overall = page.locator('[class*="overall-grade"]').first.inner_text(timeout=5000)
        data["grades"]["overall"] = overall.strip()
    except Exception:
        pass

    # Category grades (Academics, Value, Campus Life, etc.)
    try:
        grade_items = page.locator('[class*="report-card"] [class*="niche__grade"]').all()
        for item in grade_items:
            try:
                label = item.locator('[class*="label"], [class*="title"]').first.inner_text(timeout=3000).strip()
                grade = item.locator('[class*="grade"]').first.inner_text(timeout=3000).strip()
                if label and grade:
                    data["grades"][label] = grade
            except Exception:
                continue
    except Exception:
        pass

    # Rankings
    try:
        ranking_items = page.locator('[class*="rankings"] li, [class*="ranking"] li').all()
        for item in ranking_items:
            try:
                text = item.inner_text(timeout=3000).strip()
                if text:
                    data["rankings"].append(text)
            except Exception:
                continue
    except Exception:
        pass

    # Location / school type blurb
    try:
        blurb = page.locator('[class*="school-summary"], [class*="blurb"]').first.inner_text(timeout=5000)
        data["overview"]["blurb"] = blurb.strip()
    except Exception:
        pass

    return data


def scrape_reviews(page, slug: str, max_reviews: int = 20) -> list:
    """Scrape student reviews from the reviews page."""
    url = f"https://www.niche.com/colleges/{slug}/reviews/"
    print(f"  Fetching reviews: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(random.uniform(2, 4))

    reviews = []

    # Scroll to load more reviews
    for _ in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(1, 2))

    try:
        review_cards = page.locator('[class*="review"]').all()
        for card in review_cards[:max_reviews]:
            try:
                review = {}

                # Rating
                try:
                    rating = card.locator('[class*="stars"], [class*="rating"]').first.get_attribute("title", timeout=3000)
                    if rating:
                        review["rating"] = rating
                except Exception:
                    pass

                # Review text
                try:
                    body = card.locator('[class*="comment"], [class*="body"], p').first.inner_text(timeout=3000)
                    if body and len(body.strip()) > 20:
                        review["text"] = body.strip()
                except Exception:
                    pass

                # Reviewer type (e.g. "Current Student", "Alumni")
                try:
                    reviewer_type = card.locator('[class*="author"], [class*="reviewer"]').first.inner_text(timeout=3000)
                    review["reviewer_type"] = reviewer_type.strip()
                except Exception:
                    pass

                if review.get("text"):
                    reviews.append(review)
            except Exception:
                continue
    except Exception as e:
        print(f"    Warning: could not scrape reviews — {e}")

    return reviews


def scrape_university(page, slug: str) -> dict:
    """Scrape all data for a single university."""
    print(f"\nScraping: {slug}")
    data = scrape_overview(page, slug)
    data["reviews"] = scrape_reviews(page, slug)
    print(f"  Got {len(data['reviews'])} reviews, {len(data['grades'])} grades, {len(data['rankings'])} rankings")
    return data


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    slugs = [
        line.strip()
        for line in UNIVERSITIES_FILE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    print(f"Scraping {len(slugs)} universities from Niche.com...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        results = []
        for slug in slugs:
            try:
                data = scrape_university(page, slug)
                results.append(data)

                # Save individual file
                out_path = OUTPUT_DIR / f"{slug}.json"
                out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
                print(f"  Saved to {out_path.name}")
            except Exception as e:
                print(f"  ERROR scraping {slug}: {e}")

            # Polite delay between universities
            time.sleep(random.uniform(3, 6))

        browser.close()

    # Save combined file
    combined_path = OUTPUT_DIR / "all_universities.json"
    combined_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nDone. Combined data saved to {combined_path}")


if __name__ == "__main__":
    main()