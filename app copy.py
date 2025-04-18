from flask import Flask, render_template, request
from scraper_tesco import scrape_tesco_deals
from scraper_morrisons import scrape_morrisons_deals
from scraper_asda import scrape_asda_deals

app = Flask(__name__)

# Global cache to store scraped deals.
cached_deals = None

def get_all_deals():
    global cached_deals
    if cached_deals is None:
        print("🔍 Running scrapers to build cache...")
        tesco_deals = scrape_tesco_deals()            # returns Tesco deals
        morrisons_deals = scrape_morrisons_deals()      # returns Morrisons deals
        asda_deals = scrape_asda_deals()                # returns Asda deals
        cached_deals = tesco_deals + morrisons_deals + asda_deals
    return cached_deals

@app.route("/")
def index():
    # Get filter values from query parameters; defaults to "all"
    filter_category = request.args.get("category", "all").lower()  # "all", "beer", "spirits"
    filter_store = request.args.get("store", "all").lower()  # "all", "tesco", "morrisons", "asda"

    # Get cached deals (scrape only once)
    all_deals = get_all_deals()

    # Filter deals by category (if needed)
    if filter_category != "all":
        filtered_deals = []
        for deal in all_deals:
            title_lower = deal.get("title", "").lower()
            if filter_category == "beer":
                if "beer" in title_lower:
                    filtered_deals.append(deal)
            elif filter_category == "spirits":
                if any(word in title_lower for word in ["gin", "rum", "vodka", "whiskey", "whisky", "liqueur"]):
                    filtered_deals.append(deal)
        all_deals = filtered_deals

    # Filter deals by store (if needed)
    if filter_store != "all":
        all_deals = [d for d in all_deals if d.get("store", "").lower() == filter_store]

    # Sort deals by saving (treat missing savings as 0)
    all_deals = sorted(all_deals, key=lambda d: d.get("saving") or 0, reverse=True)

    return render_template("index.html", deals=all_deals,
                           current_category=filter_category,
                           current_store=filter_store)

if __name__ == "__main__":
    app.run(debug=True)
