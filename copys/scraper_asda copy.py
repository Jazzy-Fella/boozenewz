from playwright.sync_api import sync_playwright

def scrape_asda_deals():
    print(f"🔍 Scraping ASDA deals for BEER and SPIRITS")

    url_groups = {
        "Beer": [
            "https://groceries.asda.com/special-offers/all-offers/by-department/1215685911554-1215345814764",
            "https://groceries.asda.com/special-offers/all-offers/by-department/1215685911554-1215345814764?page=2"
        ],
        "Spirits": [
            "https://groceries.asda.com/special-offers/all-offers/by-department/1215685911554-1215685911575",
            "https://groceries.asda.com/special-offers/all-offers/by-department/1215685911554-1215685911575?page=2"
        ]
    }

    all_items = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=50)
            context = browser.new_context()
            page = context.new_page()

            for category, urls in url_groups.items():
                for idx, url in enumerate(urls):
                    print(f"\n🧭 Navigating to: {url}")
                    page.goto(url, timeout=90000)
                    page.wait_for_timeout(3000)

                    if idx == 0:
                        # Accept cookies once at the beginning
                        try:
                            print("🍪 Checking for cookie banner...")
                            cookie_button = page.locator('[data-testid="privacy-banner-accept"]')
                            if cookie_button.is_visible():
                                cookie_button.click()
                                print("✅ Cookie banner accepted")
                                page.wait_for_timeout(1000)
                        except Exception:
                            print("⚠️ No cookie banner or accept failed")

                    cards = page.locator("li.co-item")
                    count = cards.count()
                    print(f"🧩 Found {count} product cards. Processing...")

                    for i in range(count):
                        try:
                            card = cards.nth(i)
                            title = card.locator("h3.co-product__title a").inner_text(timeout=2000).strip()
                            link = "https://groceries.asda.com" + card.locator("h3.co-product__title a").get_attribute("href")

                            now_price_el = card.locator("strong.co-product__price")
                            price = now_price_el.inner_text().replace("now", "").replace("\n", "").strip()
                            price = price if "£" in price else f"£{price}"

                            promo_text = "No promo"
                            try:
                                promo_el = card.locator("div.link-save-banner-large__meat-sticker")
                                if promo_el.is_visible():
                                    spans = promo_el.locator("span.link-save-banner-large__config")
                                    promo_parts = [sp.inner_text().strip() for sp in spans.all()]
                                    promo_text = " ".join(promo_parts)
                            except Exception:
                                pass

                            try:
                                was_el = card.locator("span.co-product__was-price")
                                if was_el.is_visible():
                                    promo_text = was_el.inner_text().strip()
                            except Exception:
                                pass

                            all_items.append({
                                "store": "Asda",
                                "category": category,
                                "title": title,
                                "price": price,
                                "promotion": promo_text,
                                "link": link
                            })

                        except Exception as e:
                            print(f"⚠️ Error processing item {i}: {e}")
                            continue

            print(f"\n✅ Scraped {len(all_items)} ASDA deals total")
            browser.close()
            return all_items

    except Exception as e:
        print(f"💥 Scrape error: {e}")
        return []
