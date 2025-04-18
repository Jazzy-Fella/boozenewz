import os
import json
import time
from pathlib import Path
from flask import Flask, render_template, redirect, url_for
from scraper_tesco import scrape_tesco_deals
from scraper_morrisons import scrape_morrisons_deals
from scraper_asda import scrape_asda_deals

app = Flask(__name__)
CACHE_FILE = Path('cache/deals.json')
CACHE_TTL = 60 * 60  # 1 hour

def get_deals():
    # if cache exists and is fresh, load it
    if CACHE_FILE.exists() and time.time() - CACHE_FILE.stat().st_mtime < CACHE_TTL:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    # otherwise scrape, sort by saving desc, write cache
    all_deals = []
    all_deals += scrape_tesco_deals()
    all_deals += scrape_morrisons_deals()
    all_deals += scrape_asda_deals()
    # ensure we have a numeric saving field
    for d in all_deals:
        d['saving'] = d.get('saving') or 0.0
    sorted_deals = sorted(all_deals, key=lambda x: x['saving'], reverse=True)
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(sorted_deals, f)
    return sorted_deals

@app.route('/')
def index():
    deals = get_deals()
    return render_template('index.html', deals=deals)

@app.route('/refresh')
def refresh():
    try:
        CACHE_FILE.unlink()
    except FileNotFoundError:
        pass
    get_deals()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
