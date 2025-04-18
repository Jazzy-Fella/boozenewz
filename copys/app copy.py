from flask import Flask, render_template
from scraper_tesco import scrape_tesco_deals
from scraper_morrisons import scrape_morrisons_deals
from scraper_asda import scrape_asda_deals

app = Flask(__name__)

@app.route("/")
def index():
    # Get deals from each scraper
    tesco_deals = scrape_tesco_deals()            # This returns Tesco deals (both beer and spirits).
    morrisons_deals = scrape_morrisons_deals()      # This returns Morrisons deals.
    asda_deals = scrape_asda_deals()                # This returns Asda deals.

    # Combine all deals into one list
    all_deals = tesco_deals + morrisons_deals + asda_deals

    # Optionally, sort the deals by saving (treating None as zero)
    # all_deals = sorted(all_deals, key=lambda d: d.get("saving") or 0, reverse=True)

    return render_template("index.html", deals=all_deals)

if __name__ == "__main__":
    app.run(debug=True)
