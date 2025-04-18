from playwright.sync_api import sync_playwright
import time

def scrape_tesco_deals(category="beer"):
    print(f"🔍 Scraping Tesco deals for: {category.upper()}")
    base_url = f"https://www.tesco.com/groceries/en-GB/search?query={category}+special+offers&count=48"

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

                name_lower = name.lower()
                if any(x in name_lower for x in ['alcohol free', '0%', 'ginger beer', 'onion rings', 'chips']):
                    continue

                block = link_el.locator('xpath=../../../../..')
                deal_price_el = block.locator('p.ddsweb-value-bar__content-text')
                deal_price = deal_price_el.first.inner_text(timeout=1000).strip()

                old_price_el = block.locator('p.styled__PriceText-sc-v0qv7n-1')
                old_price = old_price_el.first.inner_text(timeout=1000).strip()

                def parse_price(p):
                    return float(p.replace("£", "").split()[0]) if "£" in p else 0.0

                saving = round(parse_price(old_price) - parse_price(deal_price), 2)

                items.append({
                    "name": name,
                    "old_price": old_price,
                    "deal_price": deal_price,
                    "link": full_link,
                    "saving": saving
                 })


            except Exception:
                continue

        return items

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=50)
            context = browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            page = context.new_page()

            print(f"🧭 Navigating to: {base_url}")
            page.goto(base_url, timeout=90000, wait_until="networkidle")
            page.wait_for_timeout(2000)

            for _ in range(10):
                page.mouse.wheel(0, 3000)
                time.sleep(0.3)

            print(f"🔍 Extracting {category} deal data (Page 1)...")
            all_items = extract_deals(page)

            try:
                next_button = page.locator('[data-testid="next"]')
                if next_button.is_visible():
                    print("➡️ Attempting to go to page 2...")
                    next_button.click()
                    page.wait_for_timeout(3000)
                    for _ in range(10):
                        page.mouse.wheel(0, 3000)
                        time.sleep(0.3)
                    print("🔍 Extracting page 2 data...")
                    all_items += extract_deals(page)
            except Exception as e:
                print(f"❌ Page 2 failed: {e}")

            try:
                next_button = page.locator('[data-testid="next"]')
                if next_button.is_visible():
                    print("➡️ Attempting to go to page 3...")
                    next_button.click()
                    page.wait_for_timeout(3000)
                    for _ in range(10):
                        page.mouse.wheel(0, 3000)
                        time.sleep(0.3)
                    print("🔍 Extracting page 3 data...")
                    all_items += extract_deals(page)
            except Exception as e:
                print(f"❌ Page 3 failed: {e}")

            browser.close()
            print(f"✅ Scraped {len(all_items)} {category} deals across 3 pages")
            return sorted(all_items, key=lambda x: x["saving"], reverse=True)

    except Exception as e:
        print(f"💥 Scrape error: {e}")
        return []
