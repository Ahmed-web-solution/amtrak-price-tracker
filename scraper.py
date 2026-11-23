import json
import re
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

def test_real_search():
    fare_apis = []
    # Aaj se 7 din baad ki tareekh (MM/DD/YYYY)
    travel_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%m/%d/%Y")

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

        # Search ke baad jo JSON APIs call hon unhein capture karein
        def handle_response(response):
            if "amtrak.com" in response.url and "json" in response.headers.get("content-type", ""):
                if any(k in response.url.lower() for k in ["travel", "fare", "schedule", "train", "offer", "service"]):
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
            page.goto("https://amtrak.com", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            # Agar Cookie popup ho to accept karein
            cookie_btn = page.locator("#onetrust-accept-btn-handler")
            if cookie_btn.is_visible():
                cookie_btn.click()
                page.wait_for_timeout(1000)

            # 1. From Station (NYP)
            from_input = page.locator('input[aria-label="From"]').first
            from_input.click()
            from_input.fill("NYP")
            page.wait_for_timeout(1500)
            page.keyboard.press("Enter")

            # 2. To Station (LAX)
            to_input = page.locator('input[aria-label="To"]').first
            to_input.click()
            to_input.fill("LAX")
            page.wait_for_timeout(1500)
            page.keyboard.press("Enter")

            # 3. Departure Date
            date_input = page.locator('input[aria-label="Departure Date in MM/DD/YYYY format"]').first
            date_input.click()
            date_input.fill(travel_date)
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)

            # 4. Find Trains button click karein
            find_btn = page.locator('button:has-text("Find Trains"), button:has-text("FIND TRAINS")').first
            find_btn.click()

            # Search results aur prices load hone ka wait karein
            page.wait_for_timeout(12000)

            # Screen par nazar aane wale saare $ prices nikalein
            body_text = page.inner_text("body")
            prices_found = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', body_text)

            result = {
                "status": "success",
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
                "message": str(e),
                "current_url": page.url
            }
        finally:
            browser.close()

        with open("prices.json", "w") as f:
            json.dump(result, f, indent=4)

if __name__ == "__main__":
    test_real_search()
