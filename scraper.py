import json
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# Yahan aap jitne marzi stations/routes add kar sakte hain:
ROUTES = [
    {"from": "NYP", "to": "LAX", "route_name": "New York to Los Angeles"},
    {"from": "CHI", "to": "SEA", "route_name": "Chicago to Seattle"}
]

def scrape_all_routes():
    # Aaj se 20 din baad ki tareekh (December 2026 jo calendar mein pehle hi dikhti hai)
    target_dt = datetime.now(timezone.utc) + timedelta(days=20)
    travel_date = target_dt.strftime("%m/%d/%Y")
    # Exact aria-label format: e.g. "Monday, December 14, 2026"
    exact_aria_label = f"{target_dt.strftime('%A')}, {target_dt.strftime('%B')} {target_dt.day}, {target_dt.year}"

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

                # 3. Depart Date label par click karke calendar kholein
                depart_label = page.locator('label:visible:has-text("Depart Date")').first
                depart_label.click()
                page.wait_for_timeout(1500)

                # Exact ngb-dp-day cell par click karein
                day_cell = page.locator(f'div.ngb-dp-day[aria-label="{exact_aria_label}"]:visible').first
                day_cell.click()
                page.wait_for_timeout(1000)

                # Agar calendar mein "Done" button ho to click karein
                done_btn = page.locator('button:visible:has-text("Done")').first
                if done_btn.is_visible():
                    done_btn.click()
                    page.wait_for_timeout(1000)

                # 4. Find Trains button click karein
                find_btn = page.locator('button[amt-auto-test-id="fare-finder-findtrains-button"]:visible').first
                find_btn.click()

                # Results page (/tickets/departure.html) load hone ka wait karein
                page.wait_for_timeout(15000)

                # Screen text se Coach, Business, aur Private Rooms fares nikalein
                extracted_fares = page.evaluate("""() => {
                    const textSource = document.body.innerText;

                    const coachMatch = textSource.match(/Coach\\s*(?:from)?\\s*(\\$[0-9,]+)/i);
                    const businessMatch = textSource.match(/Business\\s*(?:from)?\\s*(\\$[0-9,]+)/i);
                    const roomMatch = textSource.match(/Private Rooms?\\s*(?:from)?\\s*(\\$[0-9,]+)/i);

                    const allMatches = [...textSource.matchAll(/(?:Coach|Business|Private Rooms?)\\s*(?:from)?\\s*(\\$[0-9,]+)/gi)].map(m => m);

                    return {
                        current_url: window.location.href,
                        coach: coachMatch ? coachMatch : null,
                        business: businessMatch ? businessMatch : null,
                        private_room: roomMatch ? roomMatch : null,
                        all_matched_fares: [...new Set(allMatches)]
                    };
                }""")

                lowest = (
                    extracted_fares["coach"]
                    or extracted_fares["business"]
                    or extracted_fares["private_room"]
                    or (extracted_fares["all_matched_fares"] if extracted_fares["all_matched_fares"] else "Sold Out")
                )

                results_list.append({
                    "from": route["from"],
                    "to": route["to"],
                    "route_name": route["route_name"],
                    "travel_date": travel_date,
                    "lowest_fare": lowest,
                    "fares_breakdown": {
                        "coach": extracted_fares["coach"] or "Sold Out / N/A",
                        "business": extracted_fares["business"] or "Not Offered / Sold Out",
                        "private_room": extracted_fares["private_room"] or "Sold Out / N/A"
                    },
                    "debug_url": extracted_fares["current_url"],
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
