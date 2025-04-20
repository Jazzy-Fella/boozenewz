from playwright.sync_api import sync_playwright
import re

def scrape_asda_deals():
    print("🔍 Scraping ASDA deals for BEER and SPIRITS")

    urls = {
        "beer": [
            "https://groceries.asda.com/special-offers/all-offers/by-department/1215685911554-1215345814764",
            "https://groceries.asda.com/special-offers/all-offers/by-department/1215685911554-1215345814764?page=2"
        ],
        "spirits": [
            "https://groceries.asda.com/special-offers/all-offers/by-department/1215685911554-1215685911575",
            "https://groceries.asda.com/special-offers/all-offers/by-department/1215685911554-1215685911575?page=2"
        ]
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            items = []
            for category, url_list in urls.items():
                for url in url_list:
                    print(f"🧭 Navigating to: {url}")
                    page.goto(url, timeout=90000)
                    page.wait_for_timeout(3000)

                    # Accept cookies if banner appears
                    try:
                        print("🍪 Checking for cookie banner...")
                        btn = page.locator('[data-testid="privacy-banner-accept"]')
                        if btn.is_visible():
                            btn.click()
                            print("✅ Cookie banner accepted")
                            page.wait_for_timeout(1000)
                    except:
                        print("⚠️ No cookie banner or accept failed")

                    cards = page.locator("li.co-item")
                    total = cards.count()
                    print(f"🧩 Found {total} product cards. Processing...")

                    for i in range(total):
                        try:
                            card = cards.nth(i)

                            # Title & link
                            title_el = card.locator("h3.co-product__title a")
                            title = title_el.inner_text(timeout=2000).strip()
                            href  = title_el.get_attribute("href")
                            link  = "https://groceries.asda.com" + href

                            # Price
                            now_el = card.locator("strong.co-product__price")
                            price = now_el.inner_text().replace("now", "").replace("\n", "").strip()
                            price = price if "£" in price else f"£{price}"

                            # Promotion
                            promo = None
                            try:
                                promo_el = card.locator("div.link-save-banner-large__meat-sticker")
                                if promo_el.is_visible():
                                    promo = promo_el.inner_text().strip()
                            except:
                                pass
                            # “Was” override
                            try:
                                was_el = card.locator("span.co-product__was-price")
                                if was_el.is_visible():
                                    promo = was_el.inner_text().strip()
                            except:
                                pass

                            # Saving → always a float
                            saving_val = None
                            try:
                                save_el = card.locator("span.co-product__saving")
                                if save_el.is_visible():
                                    raw = save_el.inner_text().strip()
                                    # extract first number
                                    m = re.search(r'([\d\.,]+)', raw)
                                    if m:
                                        # remove commas, parse
                                        saving_val = float(m.group(1).replace(",",""))
                            except:
                                pass

                            items.append({
                                "store":      "Asda",
                                "category":   category,
                                "title":      title or "",
                                "price":      price or "",
                                "promotion":  promo  or "",
                                "saving":     saving_val,
                                "link":       link
                            })
                        except Exception as e:
                            print(f"⚠️ Failed item {i}: {e}")

            print(f"✅ Scraped {len(items)} ASDA deals total")
            browser.close()
            return items

    except Exception as e:
        print(f"💥 Scrape error: {e}")
        return []

