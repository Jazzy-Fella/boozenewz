from playwright.sync_api import sync_playwright
import time

def scrape_morrisons_deals():
    results = []

    urls = {
        "beer": "https://groceries.morrisons.com/categories/beer-wines-spirits/beer/f08192b4-67bc-4bf3-97ae-8b35e5ecdfdc?boolean=onOffer&sortBy=favorite",
        "spirits": "https://groceries.morrisons.com/categories/beer-wines-spirits/spirits-liqueurs/7dd6f544-d0a6-4cb3-833d-3d92d5277714?boolean=onOffer&sortBy=favorite"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Headless OFF for debugging
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

            # Scroll to bottom to load items
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(4)

            product_cards = page.locator("div.product-card-container")
            count = product_cards.count()
            print(f"🧩 Found {count} product cards")

            for i in range(count):
                try:
                    card = product_cards.nth(i)

                    # Scroll into view to trigger lazy rendering
                    card.scroll_into_view_if_needed(timeout=3000)
                    time.sleep(0.2)

                    # Extract title
                    title_locator = card.locator("h3[data-test='fop-title']")
                    title_locator.wait_for(state="visible", timeout=5000)
                    title = title_locator.inner_text()

                    # Extract price
                    price = card.locator("span[data-test='fop-price']").inner_text(timeout=3000)

                    # Extract promo text if available
                    try:
                        promo = card.locator("span[data-test='fop-offer-text']").inner_text(timeout=3000)
                    except:
                        promo = "No promo"

                    # Extract link
                    try:
                        rel_link = card.locator("a[data-test='fop-product-link']").first.get_attribute("href", timeout=3000)
                        link = f"https://groceries.morrisons.com{rel_link}" if rel_link else "No link"
                    except:
                        link = "No link"

                    results.append({
                        "store": "Morrisons",
                        "title": title,
                        "price": price,
                        "promo": promo,
                        "link": link,
                        "category": category
                    })

                except Exception as e:
                    print(f"⚠️ Error parsing item {i}: {str(e)}")

        browser.close()

    return results
