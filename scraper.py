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
    # Aaj se 21 din baad ki tareekh taake seats available hon aur "Sold Out" na aaye
    target_dt = datetime.now(timezone.utc) + timedelta(days=21)
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

                # 1. From Station
                from_input = page.locator('input[aria-label="From"]:visible').first
                from_input.click(force=True)
                from_input.press_sequentially(route["from"], delay=150)
                page.wait_for_timeout(2000)
                page.locator('.station-suggestion:visible, [role="listbox"] button:visible, ul[role="listbox"] li:visible, div[class*="dropdown"] button:visible').first.click(force=True)
                page.wait_for_timeout(1000)

                # 2. To Station
                to_input = page.locator('input[aria-label="To"]:visible').first
                to_input.click(force=True)
                to_input.press_sequentially(route["to"], delay=150)
                page.wait_for_timeout(2000)
                page.locator('.station-suggestion:visible, [role="listbox"] button:visible, ul[role="listbox"] li:visible, div[class*="dropdown"] button:visible').first.click(force=True)
                page.wait_for_timeout(1500)

                # 3. Date
                date_input = page.locator('input[amt-auto-test-id="fare-finder-depart-date-oneway"]:visible').first
                date_input.click(force=True)
                date_input.fill(travel_date)
                page.keyboard.press("Tab")
                page.wait_for_timeout(1000)

                # 4. Find Trains
                find_btn = page.locator('button:visible:has-text("Find Trains"), button:visible:has-text("FIND TRAINS")').first
                find_btn.click(force=True)

                # Jab tak actual search results page (/tickets/departure.html) load na ho, wait karein
                page.wait_for_url("**/tickets/departure.html**", timeout=30000)
                page.wait_for_timeout(8000)

                # Sirf search result cards ke andar se Coach, Business aur Private Room fares nikalein
                extracted_fares = page.evaluate("""() => {
                    const results = [];
                    // Har train row / search result card ko check karein
                    const cards = document.querySelectorAll('[class*="search-results"], [class*="journey-card"], .am-card, app-train-route');
                    const textSource = cards.length > 0 
                        ? Array.from(cards).map(c => c.innerText).join('\\n')
                        : document.body.innerText;

                    // Sirf "Coach from $XXX", "Business from $XXX", "Private Rooms from $XXX" pattern match karein
                    const coachMatch = textSource.match(/Coach\\s*(?:from)?\\s*(\\$[0-9,]+)/i);
                    const businessMatch = textSource.match(/Business\\s*(?:from)?\\s*(\\$[0-9,]+)/i);
                    const roomMatch = textSource.match(/Private Rooms?\\s*(?:from)?\\s*(\\$[0-9,]+)/i);

                    // Saare valid train fares (jo $0 na hon)
                    const allMatches = [...textSource.matchAll(/(?:Coach|Business|Private Rooms?)\\s*(?:from)?\\s*(\\$[0-9,]+)/gi)].map(m => m[1]);

                    return {
                        coach: coachMatch ? coachMatch : null,
                        business: businessMatch ? businessMatch : null,
                        private_room: roomMatch ? roomMatch : null,
                        all_matched_fares: [...new Set(allMatches)]
                    };
                }""")

                # Lowest valid fare decide karein
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
