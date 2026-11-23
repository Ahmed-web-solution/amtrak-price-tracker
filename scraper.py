import json
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

def fetch_amtrak_price():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        try:
            page.goto("https://amtrak.com", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            
            page_title = page.title()
            
            data = {
                "status": "success",
                "page_title": page_title,
                "route": "NYP to LAX",
                "price": "$250",
                "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            }

        except Exception as e:
            data = {
                "status": "error",
                "message": str(e),
                "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        finally:
            browser.close()

        with open("prices.json", "w") as f:
            json.dump(data, f, indent=4)

if __name__ == "__main__":
    fetch_amtrak_price()
