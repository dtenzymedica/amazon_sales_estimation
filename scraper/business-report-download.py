import asyncio
import json
import os
import time
from datetime import datetime, timedelta

from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "login_url": os.getenv("LOGIN_URL"),
    "download_path": os.path.join(os.getcwd(), os.getenv("DOWNLOAD_PATH", "reports")),
    "cookies_path": os.path.join(os.getcwd(), os.getenv("COOKIES_PATH", "cookies.json")),
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
    "headless": os.getenv("HEADLESS", "TRUE").upper() == "TRUE"
}

os.makedirs(CONFIG["download_path"], exist_ok=True)

def save_cookies(context):
    cookies = asyncio.run(context.cookies())
    with open(CONFIG["cookies_path"], "w") as f:
        json.dump(cookies, f, indent=2)
    print("Cookies saved successfully")
    
async def load_cookies(context):
    if os.path.exists(CONFIG["cookies_path"]):
        if os.stat(CONFIG["cookies_path"]).st_size == 0:
            print("Cookies file is empty. Logging in and saving new cookies.")
            return False  # Force a new login

        with open(CONFIG["cookies_path"], "r") as f:
            try:
                cookies = json.load(f)
                await context.add_cookies(cookies)
                print("Cookies loaded successfully")
                return True
            except json.JSONDecodeError:
                print("Cookies file is corrupted. Deleting and generating new cookies.")
                os.remove(CONFIG["cookies_path"])  # Remove the corrupted file
                return False  # Force a new login
    return False

async def get_otp():
    return input("Enter the OTP sent to your device: ")

async def login(page):
    print("Logging in to Amazon Seller Central...")

    await page.goto(CONFIG["login_url"], wait_until="domcontentloaded")

    await page.wait_for_selector("input[name='email']", timeout=10000)
    await page.fill("input[name='email']", CONFIG["credentials"]["email"])
    await page.click("input[type='submit']")

    await page.wait_for_selector("input[name='password']", state="visible", timeout=10000)
    
    # Fill password and submit
    await page.fill("input[name='password']", CONFIG["credentials"]["password"])
    await page.click("input[id='signInSubmit']")
    
    try:
        # Wait for potential 2FA
        await page.wait_for_selector("input[name='otpCode']", timeout=5000)
        print("2FA required")
        otp = await get_otp()
        await page.fill("input[name='otpCode']", otp)
        await page.click("input[id='auth-signin-button']")
        await page.wait_for_load_state("networkidle")
    except:
        print("No 2FA prompt detected or already handled")
    
    print("Login successful")


async def download_report(page, start_date, end_date):
    formatted_start_date = start_date.strftime("%Y-%m-%d")
    formatted_end_date = end_date.strftime("%Y-%m-%d")

    print(f"Downloading report for {formatted_start_date} to {formatted_end_date}...")
    report_url = f"{CONFIG['report_url']}&fromDate={formatted_start_date}&toDate={formatted_end_date}"
    await page.goto(report_url, wait_until="networkidle")

    await page.click(".css-pacyhg > kat-button:nth-child(1)")
    time.sleep(10) 
    print(f"Report for {formatted_start_date} to {formatted_end_date} downloaded successfully")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=CONFIG["headless"])
        context = await browser.new_context()
        page = await context.new_page()
        
        if not await load_cookies(context):
            await login(page)
            save_cookies(context)
        
        today = datetime.today()
        for i in range(7):
            date = today - timedelta(days=i+1)
            await download_report(page, date, date)
        
        await browser.close()
        print("All reports downloaded successfully")

if __name__ == "__main__":
    asyncio.run(main())
