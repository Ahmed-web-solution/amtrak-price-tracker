import json
import re
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

def test_real_search():
    fare_apis = []
    target_dt = datetime.now(timezone.utc) + timedelta(days=7)
    travel_date = target_dt.strftime("%m/%d/%Y")
    day_number = str(target_dt.day)

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

        def handle_response(response):
            if "amtrak.com" in response.url and "json" in response.headers.get("content-type", ""):
                if any(k in response.url.lower() for k in ["travel", "fare", "schedule", "train", "offer", "service", "dotcom"]):
                    try:
                        fare_apis.append({
                            "url": response.url,
                            "status": response.status,
                            "body_preview": str(response.json())[:1500]
                        })
                    except:
                        pass

        page.on("response", handle_response)

        try:
            page.goto("https://www.amtrak.com/home", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            # Cookie popup close karein
            cookie_btn = page.locator("#onetrust-accept-btn-handler")
            if cookie_btn.is_visible():
                cookie_btn.click()
                page.wait_for_timeout(1000)

            # 1. From Station: NYP likhein aur "(NYP)" wale dropdown item par click karein
            from_input = page.locator('input[aria-label="From"]:visible').first
            from_input.click()
            from_input.fill("NYP")
            page.wait_for_timeout(2000)
            page.locator('button:visible:has-text("(NYP)"), li:visible:has-text("(NYP)"), a:visible:has-text("(NYP)")').first.click()
            page.wait_for_timeout(1000)

            # 2. To Station: LAX likhein aur "(LAX)" wale dropdown item par click karein
            to_input = page.locator('input[aria-label="To"]:visible').first
            to_input.click()
            to_input.fill("LAX")
            page.wait_for_timeout(2000)
            page.locator('button:visible:has-text("(LAX)"), li:visible:has-text("(LAX)"), a:visible:has-text("(LAX)")').first.click()
            page.wait_for_timeout(1500)

            # 3. Date box click karein
            date_input = page.locator('input[data-julie="departdisplay_booking_oneway"]:visible, input[placeholder="MM/DD/YYYY"]:visible').first
            date_input.click()
            page.wait_for_timeout(1500)

            # Calendar mein target day click karein
            cal_day = page.locator(f'button.mat-calendar-body-cell:not([disabled]):has-text("{day_number}"), td[role="gridcell"]:not([aria-disabled="true"]):has-text("{day_number}")').first
            if cal_day.is_visible():
                cal_day.click()
            else:
                date_input.fill(travel_date)
                page.keyboard.press("Enter")

            page.wait_for_timeout(1000)

            # 4. Find Trains button click karein
            find_btn = page.locator('button:visible:has-text("Find Trains"), button:visible:has-text("FIND TRAINS")').first
            find_btn.click()

            # Search results aur prices load hone ka wait karein
            page.wait_for_timeout(12000)

            body_text = page.inner_text("body")
            prices_found = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', body_text)

            result = {
                "status": "success",
                "version": "v5_station_code",
                "current_url": page.url,
                "route": "NYP to LAX",
                "travel_date": travel_date,
                "prices_on_screen": list(dict.fromkeys(prices_found))[:15],
                "fare_apis_captured": fare_apis,
                "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            }

        except Exception as e:
            result = {
                "status": "error",
                "version": "v5_station_code",
                "message": str(e),
                "current_url": page.url
            }
        finally:
            browser.close()

        with open("prices.json", "w") as f:
            json.dump(result, f, indent=4)

if __name__ == "__main__":
    test_real_search()
