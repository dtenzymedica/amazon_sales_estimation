import asyncio
import json
import os
import time
import logging
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv

logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
            ])
logger = logging.getLogger(__name__)

load_dotenv()

CONFIG = {
    "download_path": os.path.join(os.getcwd(), os.getenv("DOWNLOAD_PATH", "reports")),
    "cookies_path": os.path.join(os.getcwd(), os.getenv("COOKIES_PATH", "cookies.json")),
    "login_url": os.getenv("LOGIN_URL"),
    "credentials": {
        "email": os.getenv("AMAZON_SELLER_EMAIL"),
        "password": os.getenv("AMAZON_SELLER_PASSWORD")
    },
    "wait_time": {
        "short": int(os.getenv("WAIT_TIME_SHORT", 2000)) / 1000,
        "medium": int(os.getenv("WAIT_TIME_MEDIUM", 5000)) / 1000,
        "long": int(os.getenv("WAIT_TIME_LONG", 10000)) / 1000
    },
    "concurrency": int(os.getenv("CONCURRENCY", 7)),
    "headless": os.getenv("HEADLESS", "False").upper() == "False"
}

os.makedirs(CONFIG["download_path"], exist_ok=True)

async def save_cookies(context):
    cookies = await context.cookies()
    with open(CONFIG["cookies_path"], "w") as f:
        json.dump(cookies, f, indent=2)
    logger.info("Cookies saved successfully")

async def load_cookies(context):
    if os.path.exists(CONFIG["cookies_path"]):
        with open(CONFIG["cookies_path"], "r") as f:
            cookies = json.load(f)

        if cookies:
            await context.add_cookies(cookies)
            logger.info("✅ Cookies loaded successfully → Skipping login!")
            return True  # Skip login if cookies are valid
    
    logger.warning("⚠️ No valid cookies found → Login required!")
    return False  # Proceed with login

async def is_login_required(page):
    current_url = page.url
    if "signin" in current_url:
        return True
    is_logged_in = await page.evaluate("""
        () => !document.querySelector('input[name="email"]') && \
               !document.querySelector('input[name="password"]')
    """)
    return not is_logged_in

async def login(page):
    logger.info("🔑 Logging in to Amazon Seller Central...")

    await page.goto(CONFIG["login_url"], wait_until="networkidle")

    # Enter Email
    await page.fill("input[name='email']", CONFIG["credentials"]["email"])
    await page.click("input[type='submit']")
    
    # Enter Password
    await page.wait_for_selector("input[name='password']", timeout=10000)
    await page.fill("input[name='password']", CONFIG["credentials"]["password"])
    await page.click("input[id='signInSubmit']")
    
    # Check if MFA is required
    try:
        await page.wait_for_selector("input[name='otpCode']", timeout=5000)
        logger.info("🔐 2FA/MFA required! Enter OTP manually.")

        otp_code = input("Enter the OTP sent to your device: ")
        await page.fill("input[name='otpCode']", otp_code)
        await page.click("input[id='auth-signin-button']")
        await page.wait_for_load_state("networkidle")
        logger.info("✅ MFA Verification Complete!")
        
    except:
        
        logger.warning("✅ No 2FA prompt detected, proceeding...")

    # Save cookies after login
    await save_cookies(page.context)
    logger.info("✅ Login successful, cookies saved!")

async def download_report(page, start_date, end_date):
    formatted_start_date = start_date.strftime("%m/%d/%Y")
    formatted_end_date = end_date.strftime("%m/%d/%Y")
    logger.info(f"\n📊 Initiating report download for {formatted_start_date} to {formatted_end_date}...")

    # Navigate to Reports Repository
    await page.goto(CONFIG["login_url"], wait_until="networkidle")

    ## Step 1: Select "United States" Account
    logger.info("🌎 Selecting United States Account...")
    await page.wait_for_selector("button.full-page-account-switcher-account-details", timeout=30000)
    await page.evaluate('''
        () => {
            let buttons = document.querySelectorAll("button.full-page-account-switcher-account-details");
            for (let btn of buttons) {
                if (btn.innerText.includes("United States")) {
                    btn.click();
                    return;
                }
            }
        }
    ''')
    logger.info("✅ Selected 'United States'.")

    ## Step 2: Click "Select Account" Button
    logger.info("🔄 Clicking 'Select Account' button...")
    await page.wait_for_selector("button.kat-button--primary.kat-button--base:not([disabled])", timeout=100000)
    await page.click("button.kat-button--primary.kat-button--base:not([disabled])")
    logger.info("✅ Account selected.")

    ## Step 3: Navigate to "Payments" > "Report Repository"
    logger.info("📂 Navigating to 'Payments' → 'Report Repository'...")

    await page.wait_for_selector("div.nav-button", timeout=100000)
    await page.click("div.nav-button")
    logger.info("✅ Opened main navigation.")

    await page.wait_for_selector("span.nav-section-label:text('Payments')", timeout=100000)
    await page.click("span.nav-section-label:text('Payments')")
    logger.info("✅ Selected 'Payments'.")

    await page.wait_for_selector("a.flyout-menu-item-container[href*='payments/reports-repository']", timeout=50000)
    await page.click("a.flyout-menu-item-container[href*='payments/reports-repository']")
    logger.info("✅ Navigated to 'Report Repository'.")

    ## Step 4: Set Date Range for Report
    logger.info("📅 Setting date range for report...")

    await page.wait_for_selector("kat-input[name='startDate']", timeout=50000)
    await page.wait_for_selector("kat-input[name='endDate']", timeout=50000) 
    
    # Set "From Date" (Start Date)
    await page.evaluate("""
        (dateValue) => {
            let datePicker = document.querySelector("kat-date-picker[name='startDate']");
            if (datePicker) {
                datePicker.value = dateValue;
                datePicker.dispatchEvent(new Event('input', { bubbles: true }));
                datePicker.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                console.error("❌ Start Date picker not found!");
            }
        }
    """, formatted_start_date)

    # Set "To Date" (End Date)
    await page.evaluate("""
        (dateValue) => {
            let datePicker = document.querySelector("kat-date-picker[name='endDate']");
            if (datePicker) {
                datePicker.value = dateValue;
                datePicker.dispatchEvent(new Event('input', { bubbles: true }));
                datePicker.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                console.error("❌ End Date picker not found!");
            }
        }
    """, formatted_end_date)

    logger.info("✅ Date range set successfully.")

    ## Step 5: Click "Request Report"
    await page.wait_for_selector("kat-button#filter-generate-button", timeout=50000)

    # Click the button using JavaScript to ensure compatibility with Shadow DOM
    await page.evaluate("""
        () => {
            let requestButton = document.querySelector("kat-button#filter-generate-button");
            if (requestButton) {
                requestButton.click();
            } else {
                console.error("'Request Report' button not found!");
            }
        }
    """)

    logger.info("Report request submitted.")

    ## Step 6: Wait for Report to be Ready
    logger.info("Waiting for report to be ready...")
    
    while True:
        try:
            # Locate the first row in the report table
            report_row = await page.query_selector("kat-table-row:nth-child(1)")
            if not report_row:
                print("⚠️ Report row not found, retrying...")
                await asyncio.sleep(5)
                continue

            # Locate the refresh button inside the <kat-table-cell> in the shadow DOM
            refresh_button = await page.evaluate_handle('''
                (row) => {
                    if (!row || !row.shadowRoot) return null;
                    const tableCell = row.shadowRoot.querySelector("kat-table-cell.header-cell-report-action");
                    if (!tableCell || !tableCell.shadowRoot) return null;
                    return tableCell.shadowRoot.querySelector("kat-button");
                }
            ''', report_row)

            if not refresh_button:
                print("⚠️ Refresh button not found, retrying...")
                await asyncio.sleep(5)
                continue

            # Get the button text
            button_text = await refresh_button.evaluate('(button) => button.innerText')

            if "Download CSV" in button_text:
                print("✅ Download button detected. Initiating download...")
                await refresh_button.click()
                break  # Exit loop once the correct button appears

            print("🔄 Report not ready. Clicking refresh...")
            await refresh_button.click()
            await asyncio.sleep(5)  # Wait before retrying

        except Exception as e:
            print(f"⚠️ Error detecting refresh button: {e}")
            await asyncio.sleep(5)
    ## Step 8: Download Report
    await refresh_button.click()
    logger.info("Download started.")

    time.sleep(10)
    logger.info(f"Report for {formatted_start_date} to {formatted_end_date} downloaded successfully.")
    
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
        headless=False,  # Ensure browser UI is visible
        args=["--start-maximized"]  # Maximizes window
        )
        context = await browser.new_context(
        viewport={"width": 1920, "height": 1080}  # Optional: Set fixed resolution
        )
        page = await context.new_page()
        
        # Load Cookies, If Not Available → Perform Login
        cookies_loaded = await load_cookies(context)
        if not cookies_loaded:
            await login(page)

        logger.info("Navigating to Reports Page...")
        await page.goto(CONFIG["login_url"], wait_until="networkidle")

        today = datetime.today()
        for i in range(7):
            date = today - timedelta(days=i+1)
            await download_report(page, date, date)
        
        # await browser.close()
        logger.info("All reports downloaded successfully!")


if __name__ == "__main__":
    asyncio.run(main())