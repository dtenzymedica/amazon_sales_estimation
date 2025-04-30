import os
import re
import sys
import time
import json
import pyotp
import random
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# LOGGING CONFIGURATION
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r'C:\Users\d.tanubudhi\amazon_sales_estimation\logs\enzyme-science-reports.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)]
    )
logger = logging.getLogger(__name__)

# LOAD ENVIRONMENT VARIABLES
load_dotenv()

# CONFIGURATION
CONFIG = {
    "enzyme_science_download_path": r'C:\Users\d.tanubudhi\amazon_sales_estimation\reports\enzyme-science-reports',
    "cookies_path": r"C:\Users\d.tanubudhi\amazon_sales_estimation\cookies.json",
    "login_url": os.getenv("LOGIN_URL"),
    "credentials": {
        "email": os.getenv("AMAZON_SELLER_EMAIL"),
        "password": os.getenv("AMAZON_SELLER_PASSWORD"),
        "totp_secret": os.getenv("TOTP_SECRET")  
    },
}

class BusinessReportDownloads:
    def __init__(self):
        """Initializing the Web Scraper."""
        self.driver = self.setup_driver()

    def setup_driver(self):
        """Setup Selenium WebDriver with optimized options."""
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option("prefs", {"download.default_directory": CONFIG["enzyme_science_download_path"]})
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless")

        return webdriver.Chrome(options=options)
    
    def random_delay(self, min_seconds=2, max_seconds=5):
        """Add a Random Delay Between Actions to Avoid Detection."""
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"Delaying for {delay:.2f} seconds...")
        time.sleep(delay)
    
    def load_cookies(self):
        """Load Cookies from File."""
        if os.path.exists(CONFIG["cookies_path"]):
            self.driver.get(CONFIG["login_url"])
            with open(CONFIG["cookies_path"], "r") as f:
                cookies = json.load(f)
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            logger.info("Cookies loaded successfully -> Skipping login!")

            self.random_delay(2, 4)
            self.driver.refresh()
            return True
        return False
    
    def save_cookies(self):
        """Save Cookies After Login."""
        with open(CONFIG["cookies_path"], 'w') as f: 
            json.dump(self.driver.get_cookies(), f, indent=2)
        logger.info("Cookies saved successfully!")

    def generate_otp(self):
        """Generate OTP using PyOTP"""
        totp_secret = CONFIG["credentials"]["totp_secret"]
        if not totp_secret:
            logger.error("TOTP Secret not found in environment variables.")
            return None

        totp = pyotp.TOTP(totp_secret)
        otp_code = totp.now()
        logger.info(f"Generated OTP: {otp_code}")
        return otp_code

    def login(self):
        """Handle Login and MFA (if required)."""
        self.driver.get(CONFIG["login_url"])
        try:
            logger.info("Logging in...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="ap_email"]'))
            ).send_keys(CONFIG["credentials"]["email"], Keys.RETURN)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="ap_password"]'))
            ).send_keys(CONFIG["credentials"]["password"], Keys.RETURN)

            self.random_delay(2, 4)

            # Handle OTP/MFA manually
            try:
                otp_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "otpCode"))
                )
                otp_code = self.generate_otp()  # Generate OTP dynamically
                if otp_code:
                    otp_input.send_keys(otp_code, Keys.RETURN)
                    self.random_delay(5, 10)
                else:
                    logger.error("Failed to generate OTP")
                    return
            except:
                logger.info("No OTP required")

            self.save_cookies()
            logger.info("Login was successful!")

        except Exception as e:
            logger.warning(f"Login failed: {e}")

    def navigate_to_reports(self):
        """Navigate to Reports Repository."""
        logger.info("Navigating to Reports Page...")
        self.driver.get(CONFIG['login_url'])
        self.random_delay(2, 4)

        try:
            account_select = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//span[text()="Enzyme Science"]/ancestor::button')
                )
            )
            account_select.click()
            logger.info('Selected Enzyme Science account.')

            us_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//span[text()="United States"]/ancestor::button')
                )
            )
            us_button.click()
            logger.info("Clicked on US button")

            select_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//button[contains(@class, "full-page-account-switcher-buttons")]')
                )
            )
            select_button.click()
            logger.info("Clicked on 'Select Account' button")
        except:
            logger.info("'United States' button not found")

        try:
            logger.info("Clicking on 'Skip button'")
            skip_button = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="react-joyride-step-0"]/div/div/div/div[2]/div/button')))
            skip_button.click()
            logger.info("Successfully clicked 'Skip button'.")
        except:
            logger.warning("'Skip button' not found")

    def expand_shadow_element(self, selector):
        """Expands Shadow DOM and Returns the Input Element Inside."""
        try:
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.querySelector(arguments[0]) !== null", selector)
            )
            shadow_host = self.driver.find_element(By.CSS_SELECTOR, selector)
            shadow_root = self.driver.execute_script("return arguments[0].shadowRoot", shadow_host)
            return shadow_root.find_element(By.CSS_SELECTOR, "input")
        except:
            logger.warning(f"Failed to expand shadow element '{selector}': {e}")
            return None
            

    def set_date_range(self, start_date, end_date):
        """Set Date Range in the Shadow DOM Date Picker."""
        logger.info(f"Setting date range: {start_date} -> {end_date}")

        try:
            # Expand Shadow DOM elements
            start_date_input = self.expand_shadow_element("kat-date-picker[name='startDate']")
            end_date_input = self.expand_shadow_element("kat-date-picker[name='endDate']")

            # Function to set date
            def set_date(input_element, date_value):
                self.driver.execute_script("arguments[0].value = arguments[1];", input_element, date_value)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_element)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", input_element)

            set_date(start_date_input, start_date)
            set_date(end_date_input, end_date)
            logger.info("Date range set successfully!")

        except Exception as e:
            logger.warning(f"Error setting date: {e}")

    def request_report(self):
        """Click 'Request Report' Button."""
        logger.info("Requesting report...")
        request_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "filter-generate-button"))
        )
        request_button.click()
        self.random_delay(3, 5)
        logger.info("Report request submitted.")

    def wait_for_report(self):
        """Wait for Report to be Ready and Download It."""
        logger.info("Waiting for report to be ready...")

        while True:
            try:
                # Click Refresh Button Every 2 Seconds
                refresh_button = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, "//kat-button[contains(@label, 'Refresh')]"))
                )
                refresh_button.click()
                logger.info("Clicked 'Refresh' button...")
                time.sleep(2)
                
                
                # Check if Download Button Exists
                download_button = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/article[3]/section/div/kat-card/div/div/div/div[1]/kat-table/kat-table-body/kat-table-row[1]/kat-table-cell[8]/div/kat-button'))
                )
                logger.info("Download button found.")
                if download_button:
                    logger.info("Report is ready! Clicking 'Download CSV' button...")
                    download_button.click()
                    self.random_delay(2, 4)
                    logger.info("Report downloaded successfully!")
                    return

            except:
                logger.warning("Report not ready, retrying in 2 seconds...")

    def check_new_file_downloaded(self, before_files):
        """Check if a new report file matching expected pattern has been downloaded."""
        pattern = re.compile(r"\d{4}[A-Za-z]{3}\d{1,2}-\d{4}[A-Za-z]{3}\d{1,2}CustomTransaction\.csv")
        after_files = set(os.listdir(CONFIG["enzyme_science_download_path"]))
        new_files = after_files - before_files

        for file in new_files:
            if pattern.match(file):
                logger.info(f"New file detected: {file}")
                return True
        logger.warning("No new matching file downloaded.")
        return False

if __name__ == "__main__":
    success = False
    attempts = 0
    max_attempts = 5

    while not success and attempts < max_attempts:
        getreports = BusinessReportDownloads()
        attempts += 1
        logger.info(f"Attempt #{attempts} to download the report...")

        try:
            getreports.login()
            getreports.navigate_to_reports()

            today = datetime.today()
            date = today - timedelta(days=1)
            formatted_start_date = date.strftime("%m/%d/%Y")
            formatted_end_date = date.strftime("%m/%d/%Y")

            before_files = set(os.listdir(CONFIG["enzyme_science_download_path"]))

            getreports.set_date_range(formatted_start_date, formatted_end_date)
            getreports.request_report()
            getreports.wait_for_report()

            success = getreports.check_new_file_downloaded(before_files)

        except Exception as e:
            logger.warning(f"Attempt failed due to: {e}")
        finally:
            getreports.driver.quit()

    if success:
        logger.info("Report downloaded successfully.")
    else:
        logger.error("Failed to download new report after multiple attempts.")