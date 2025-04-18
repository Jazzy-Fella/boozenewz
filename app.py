#!/usr/bin/env python3
import os
import sys
import json
import time
import argparse
from pathlib import Path
from flask import Flask, render_template, redirect, url_for
from jinja2 import TemplateNotFound

from scraper_tesco import scrape_tesco_deals
from scraper_morrisons import scrape_morrisons_deals
from scraper_asda import scrape_asda_deals

app = Flask(__name__)

CACHE_FILE = Path('cache/deals.json')
CACHE_TTL = 60 * 60  # 1 hour

def get_deals():
    """Scrape all stores and save to cache/deals.json"""
    print("🔍 Scraping Tesco deals...")
    tesco_deals = scrape_tesco_deals()

    print("🔍 Scraping Morrisons deals...")
    morrisons_deals = scrape_morrisons_deals()

    print("🔍 Scraping ASDA deals...")
    asda_deals = scrape_asda_deals()

    all_deals = tesco_deals + morrisons_deals + asda_deals

    # Normalize 'saving'
    for deal in all_deals:
        deal['saving'] = deal.get('saving') or 0.0

    sorted_deals = sorted(all_deals, key=lambda x: x['saving'], reverse=True)

    # Save to cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(sorted_deals, f, indent=2)

    print(f"✅ Scraped {len(sorted_deals)} deals (wrote {CACHE_FILE}).")
    return sorted_deals


@app.route('/')
def index():
    """Try to render local template, fallback to raw JSON view"""
    try:
        with open(CACHE_FILE, 'r') as f:
            deals = json.load(f)
        return render_template('index.html', deals=deals)
    except TemplateNotFound:
        return redirect(url_for('static', filename='../cache/deals.json'))
    except Exception as e:
        return f"<h2>Error: {e}</h2>"


@app.route('/refresh')
def refresh():
    """Force re-scrape via browser"""
    try:
        CACHE_FILE.unlink()
    except FileNotFoundError:
        pass
    get_deals()
    return redirect(url_for('index'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Booze Newz Runner")
    parser.add_argument('--scrape', action='store_true', help='Only run scraper and exit (non-headless)')
    args = parser.parse_args()

    if args.scrape:
       get_deals()
       sys.exit(0)
    else:
    # Only run scraper on first Flask boot (not reloader process)
       if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
          get_deals()
       app.run(debug=True, host='127.0.0.1', port=5000)

