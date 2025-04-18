from playwright.sync_api import sync_playwright
import time

def scrape_tesco_beer_deals():
    print("🍻 Looking for beer deals on Tesco...\n")

    base_url = "https://www.tesco.com/groceries/en-GB/search?query=beer+special+offers&count=48"

    def extract_deals(page):
        items = []
        product_blocks = page.locator('a.ddsweb-title-link__link')

        count = product_blocks.count()
        print(f"🧩 Found {count} product links. Processing...\n")

        for i in range(count):
            try:
                link_el = product_blocks.nth(i)
                name = link_el.locator('span.ddsweb-link__text').inner_text(timeout=1000).strip()
                href = link_el.get_attribute('href')
                full_link = f"https://www.tesco.com{href}"

                # Filter unwanted items
                name_lower = name.lower()
                if any(x in name_lower for x in ['alcohol free', '0%', 'ginger beer', 'onion rings', 'chips']):
                    continue

                # Price block
                block = link_el.locator('xpath=../../../../..')
                deal_price_el = block.locator('p.ddsweb-value-bar__content-text')
                deal_price = deal_price_el.first.inner_text(timeout=1000).strip()

                # Old price
                old_price_el = block.locator('p.styled__PriceText-sc-v0qv7n-1')
                old_price = old_price_el.first.inner_text(timeout=1000).strip()

                items.append({
                    "name": name,
                    "old_price": old_price,
                    "deal_price": deal_price,
                    "link": full_link
                })

            except Exception:
                continue

        return items

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print(f"🧭 Navigating to: {base_url}")
        page.goto(base_url, timeout=60000)
        page.wait_for_timeout(2000)

        print("📜 Scrolling to trigger lazy-load...")
        for _ in range(10):
            page.mouse.wheel(0, 3000)
            time.sleep(0.3)

        print("🔍 Extracting beer deal data...\n")
        all_items = extract_deals(page)

        # Attempt to go to next page
        print("➡️ Attempting to go to page 2 via button...")
        try:
            next_button = page.locator('[data-testid="next"]')
            if next_button.is_visible():
                next_button.click()
                page.wait_for_timeout(3000)
                print("📜 Scrolling on page 2...")
                for _ in range(10):
                    page.mouse.wheel(0, 3000)
                    time.sleep(0.3)
                print("🔍 Extracting page 2 data...\n")
                page_2_items = extract_deals(page)
                all_items.extend(page_2_items)
            else:
                print("❌ Page 2 button not visible.")
        except Exception as e:
            print(f"❌ Failed to go to page 2: {e}")

        browser.close()

        print(f"✅ Found {len(all_items)} beer deals.\n")
        print("📝 Results:\n")
        for item in all_items:
            print(f"• {item['name']} — {item['old_price']} → {item['deal_price']} — {item['link']}")

        return all_items
