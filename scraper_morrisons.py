from playwright.sync_api import sync_playwright
import time

def scrape_morrisons_deals():
    results = []

    urls = {
        "beer": "https://groceries.morrisons.com/categories/beer-wines-spirits/beer/f08192b4-67bc-4bf3-97ae-8b35e5ecdfdc?boolean=onOffer&sortBy=favorite",
        "spirits": "https://groceries.morrisons.com/categories/beer-wines-spirits/spirits-liqueurs/7dd6f544-d0a6-4cb3-833d-3d92d5277714?boolean=onOffer&sortBy=favorite"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for category, url in urls.items():
            print(f"\n🔍 Scraping Morrisons deals for: {category.upper()}")
            page.goto(url, timeout=60000)
            time.sleep(3)

            # Accept cookie banner
            print("🍪 Checking for cookie banner...")
            try:
                cookie_btn = page.locator("button", has_text="Accept All Cookies")
                if cookie_btn.is_visible():
                    cookie_btn.click()
                    print("✅ Accepted cookie banner.")
                    time.sleep(2)
            except:
                print("⚠️ No cookie banner found or already accepted.")

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(4)

            product_cards = page.locator("div.product-card-container")
            count = product_cards.count()
            print(f"🧩 Found {count} product cards")

            for i in range(count):
                try:
                    card = product_cards.nth(i)
                    card.scroll_into_view_if_needed(timeout=3000)
                    time.sleep(0.2)

                    title_locator = card.locator("h3[data-test='fop-title']")
                    title_locator.wait_for(state="visible", timeout=5000)
                    title = title_locator.inner_text()

                    price = card.locator("span[data-test='fop-price']").inner_text(timeout=3000)

                    try:
                        promo = card.locator("span[data-test='fop-offer-text']").inner_text(timeout=3000)
                    except:
                        promo = ""

                    try:
                        rel_link = card.locator("a[data-test='fop-product-link']").first.get_attribute("href", timeout=3000)
                        link = f"https://groceries.morrisons.com{rel_link}" if rel_link else "No link"
                    except:
                        link = "No link"

                    saving = None
                    try:
                        if "Was £" in promo or "was £" in promo:
                            now_price_val = float(price.replace("£", "").strip())
                            old_price_str = promo.lower().split("was £")[-1].split()[0]
                            old_price_val = float(old_price_str)
                            saving = round(old_price_val - now_price_val, 2)
                    except Exception as e:
                        print(f"❌ Saving parse failed: {e}")

                    results.append({
                        "store": "Morrisons",
                        "title": title,
                        "price": price,
                        "promotion": promo,  # <-- This is the fixed field name
                        "saving": saving if saving and saving > 0 else None,
                        "link": link,
                        "category": category
                    })

                    print("DEBUG:", results[-1])

                except Exception as e:
                    print(f"⚠️ Error parsing item {i}: {str(e)}")

        browser.close()

    return results
