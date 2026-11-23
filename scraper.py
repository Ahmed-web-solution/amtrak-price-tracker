import json
from playwright.sync_api import sync_playwright

def discover_amtrak_api():
    api_calls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        # Har network response ko listen karein
        def handle_response(response):
            if "amtrak.com" in response.url and "json" in response.headers.get("content-type", ""):
                api_calls.append({
                    "url": response.url,
                    "status": response.status
                })

        page.on("response", handle_response)

        try:
            page.goto("https://amtrak.com", timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(3000)

            # Page par maujood saare input fields ke placeholders/names nikalein
            inputs = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('input')).map(i => ({
                    id: i.id,
                    name: i.name,
                    placeholder: i.placeholder,
                    ariaLabel: i.getAttribute('aria-label')
                }));
            }""")

            result = {
                "status": "success",
                "inputs_found": inputs,
                "json_apis_called": api_calls
            }

        except Exception as e:
            result = {"status": "error", "message": str(e)}
        finally:
            browser.close()

        with open("prices.json", "w") as f:
            json.dump(result, f, indent=4)

if __name__ == "__main__":
    discover_amtrak_api()
