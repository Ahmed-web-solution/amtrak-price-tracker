import json
import re
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

ROUTES = [
    {"from": "NYP", "to": "LAX", "route_name": "New York to Los Angeles"},
    {"from": "CHI", "to": "SEA", "route_name": "Chicago to Seattle"}
]

def scrape_all_routes():
    target_dt = datetime.now(timezone.utc) + timedelta(days=10)
    travel_date = target_dt.strftime("%m/%d/%Y")

    results_list = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 900}
        )
        page = context.new_page()

        for route in ROUTES:
            try:
                page.goto("https://amtrak.com", timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)

                cookie_btn = page.locator("#onetrust-accept-btn-handler")
                if cookie_btn.is_visible():
                    cookie_btn.click()
                    page.wait_for_timeout(1000)

                # 1. From Station select karein
                from_input = page.locator('input[aria-label="From"]:visible').first
                from_input.click(force=True)
                from_input.press_sequentially(route["from"], delay=150)
                page.wait_for_timeout(2000)
                page.locator('.station-suggestion:visible, [role="listbox"] button:visible, ul[role="listbox"] li:visible, div[class*="dropdown"] button:visible').first.click(force=True)
                page.wait_for_timeout(1000)

                # 2. To Station select karein
                to_input = page.locator('input[aria-label="To"]:visible').first
                to_input.click(force=True)
                to_input.press_sequentially(route["to"], delay=150)
                page.wait_for_timeout(2000)
                page.locator('.station-suggestion:visible, [role="listbox"] button:visible, ul[role="listbox"] li:visible, div[class*="dropdown"] button:visible').first.click(force=True)
                page.wait_for_timeout(1500)

                # 3. Date box mein direct MM/DD/YYYY type karein (force=True ke saath)
                date_input = page.locator('input[amt-auto-test-id="fare-finder-depart-date-oneway"]:visible').first
                date_input.click(force=True)
                date_input.fill(travel_date)
                page.keyboard.press("Tab")
                page.wait_for_timeout(1000)

                # 4. Find Trains click karein
                find_btn = page.locator('button:visible:has-text("Find Trains"), button:visible:has-text("FIND TRAINS")').first
                find_btn.click(force=True)

                # Search results page load hone ka wait karein
                page.wait_for_timeout(12000)

                body_text = page.inner_text("body")
                raw_prices = re.findall(r'\$\d+(?:,\d{3})*', body_text)
                valid_prices = [p for p in dict.fromkeys(raw_prices) if p != "$0"]
                lowest_price = valid_prices if valid_prices else "Sold Out"

                results_list.append({
                    "from": route["from"],
                    "to": route["to"],
                    "route_name": route["route_name"],
                    "travel_date": travel_date,
                    "lowest_fare": lowest_price,
                    "all_fares_found": valid_prices[:8],
                    "status": "success"
                })

            except Exception as e:
                results_list.append({
                    "from": route["from"],
                    "to": route["to"],
                    "route_name": route["route_name"],
                    "status": "error",
                    "error": str(e)
                })

        browser.close()

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "routes": results_list
    }

    with open("prices.json", "w") as f:
        json.dump(output, f, indent=4)

if __name__ == "__main__":
    scrape_all_routes()
