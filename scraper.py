import json
import re
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# Yahan aap jitne marzi stations/routes add kar sakte hain:
ROUTES = [
    {"from": "NYP", "to": "LAX", "route_name": "New York to Los Angeles"},
    {"from": "CHI", "to": "SEA", "route_name": "Chicago to Seattle"}
]

def scrape_all_routes():
    # Aaj se 10 din baad ki tareekh (taake sold-out rush se bacha ja sake)
    target_dt = datetime.now(timezone.utc) + timedelta(days=10)
    travel_date = target_dt.strftime("%m/%d/%Y")
    day_number = str(target_dt.day)

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

                # Cookie popup close karein (agar nazar aaye)
                cookie_btn = page.locator("#onetrust-accept-btn-handler")
                if cookie_btn.is_visible():
                    cookie_btn.click()
                    page.wait_for_timeout(1000)

                # 1. From Station select karein
                from_input = page.locator('input[aria-label="From"]:visible').first
                from_input.click()
                from_input.fill(route["from"])
                page.wait_for_timeout(2000)
                page.locator(f'button:visible:has-text("({route["from"]})"), li:visible:has-text("({route["from"]})")').first.click()
                page.wait_for_timeout(1000)

                # 2. To Station select karein
                to_input = page.locator('input[aria-label="To"]:visible').first
                to_input.click()
                to_input.fill(route["to"])
                page.wait_for_timeout(2000)
                page.locator(f'button:visible:has-text("({route["to"]})"), li:visible:has-text("({route["to"]})")').first.click()
                page.wait_for_timeout(1500)

                # 3. Date select karein
                date_input = page.locator('input[data-julie="departdisplay_booking_oneway"]:visible, input[placeholder="MM/DD/YYYY"]:visible').first
                date_input.click()
                page.wait_for_timeout(1500)

                cal_day = page.locator(f'button.mat-calendar-body-cell:not([disabled]):has-text("{day_number}"), td[role="gridcell"]:not([aria-disabled="true"]):has-text("{day_number}")').first
                if cal_day.is_visible():
                    cal_day.click()
                else:
                    date_input.fill(travel_date)
                    page.keyboard.press("Enter")

                page.wait_for_timeout(1000)

                # 4. Find Trains click karein
                find_btn = page.locator('button:visible:has-text("Find Trains"), button:visible:has-text("FIND TRAINS")').first
                find_btn.click()

                # Results page (/tickets/departure.html) load hone ka wait
                page.wait_for_timeout(12000)

                # Screen se saare dollar fares ($482, $702, etc.) nikalein
                body_text = page.inner_text("body")
                raw_prices = re.findall(r'\$\d+(?:,\d{3})*', body_text)
                
                # $0 (cart icon) ko hata kar unique prices sort karein
                valid_prices = [p for p in dict.fromkeys(raw_prices) if p != "$0"]
                lowest_price = valid_prices[0] if valid_prices else "Sold Out"

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
