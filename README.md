
# 📰 Booze Newz  
### *Retro-styled supermarket alcohol deal aggregator*


**Booze Newz** is a Teletext-inspired web app that scrapes the latest alcohol deals from Tesco, Asda, and Morrisons, displaying them in glorious retro Ceefax style — pixel fonts, vivid colours, and CRT flicker included.

The app calculates savings on alcohol deals and sorts them so the best bargains always bubble to the top. It runs locally for scraping (using an agentic Playwright browser) and then serves the results via a simple static website.

---

## ⚡ How It Works

### 🔍 Scraping (Manual Run)
- Scrapes **Tesco**, **Morrisons**, and **Asda** alcohol deals.
- Uses **Playwright with a non-headless browser** to avoid bot detection.
- Handles multi-page navigation and cookie banners.
- Outputs the results to:  
  ```
  cache/deals.json
  ```
- Run locally on your machine (scraping requires the browser window to be open).

---

### 🎨 Display
- Hosted as a **static site on GitHub Pages**.
- Built with:
  - **HTML / CSS (VT323 pixel font)**  
  - **JavaScript (no frameworks)**  
  - CRT scanlines, RGB split effects, and retro colour palette.
- Fully responsive with:
  - 🏷️ Supermarket filters (All / Tesco / Morrisons / Asda)  
  - 🍺 Category filters (All / Beer / Spirits)  
  - 🔎 Live search bar  
  - 💰 Sorted by savings (highest to lowest)  

---

## 📱 PWA (Progressive Web App)
- Includes a `site.webmanifest` and `service-worker.js`.
- Installable on **iPhone and Android** (Add to Home Screen).
- Uses a **network-first caching strategy** to stay up-to-date.

---

## 🚀 How to Scrape and Update the Deals

1. Clone the repo:
   ```bash
   git clone https://github.com/Jazzy-Fella/boozenewz.git
   cd boozenewz
   ```

2. Activate your Python virtual environment (if using one):
   ```bash
   source venv/bin/activate
   ```

3. Run the scraper locally:
   ```bash
   python app.py --scrape
   ```

4. Commit and push the new deals:
   ```bash
   git add docs/deals.json
   git commit -m "Update deals.json with latest scraped data"
   git push
   ```

The live site will then update automatically via GitHub Pages.

---

## 🛠️ Tech Stack

| Feature          | Stack                                |
|------------------|----------------------------------------|
| Scraping         | Python + Playwright (non-headless agentic browser) |
| Frontend         | HTML / CSS / Vanilla JS               |
| Fonts & Styling  | VT323 pixel font + CRT flicker effects|
| Deployment       | GitHub Pages                          |
| PWA              | Manifest + Service Worker             |

---

## 📦 Project Structure

```
.
├── app.py                  # Main scraper controller
├── scraper_tesco.py        # Tesco scraper logic
├── scraper_morrisons.py    # Morrisons scraper logic
├── scraper_asda.py         # Asda scraper logic
├── cache/deals.json        # Scraped data output (pushed to GitHub)
├── docs/                   # Static site (index.html, style.css, manifest)
│   └── deals.json          # Live deals file for the frontend
```

---

## 🍻 FAQ

> **Q:** Is there an App for this?  
> **A:** Yes! For iPhone: tap the share button → “Add to Home Screen.”  
> For Android: tap the three-dot menu → “Add to Home Screen.”

> **Q:** Are you adding Sainsbury’s or Co-Op?  
> **A:** No. They are terrible for deals.


