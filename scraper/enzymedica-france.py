import os
import sys
import re
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
import pandas as pd
from pandas.errors import ParserError

# LOGGING CONFIGURATION
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r'C:\Users\d.tanubudhi\amazon_sales_estimation\logs\eu-enzymedica-reports.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)]
    )
logger = logging.getLogger(__name__)

# LOAD ENVIRONMENT VARIABLES
load_dotenv()

# CONFIGURATION
CONFIG = {
    "europe_download_path": r'C:\Users\d.tanubudhi\amazon_sales_estimation\reports\europe-sales-reports\france',
    "cookies_path": r"C:\Users\d.tanubudhi\amazon_sales_estimation\cookies.json",
    "login_url": 'https://sellercentral.amazon.de/payments/reports-repository/ref=xx_rrepo_dnav_xx',
    "credentials": {
        "email": os.getenv("EU_AMAZON_SELLER_EMAIL"),
        "password": os.getenv("EU_SELLER_PASSWORD"),
        "totp_secret": os.getenv("EU_TOTP_SECRET")  
    },
}

class EuropeBusinessReportDownloads:
    def __init__(self):
        """Initializing the Web Scraper."""
        self.driver = self.setup_driver()
        self.master_file = r"C:\Users\d.tanubudhi\OneDrive - Enzymedica\Documents\Sales_Estimations_Reports\MasterFiles\FranceCustomTransaction.csv"
        self.report_folder = r"C:\Users\d.tanubudhi\amazon_sales_estimation\reports\europe-sales-reports\france"
        self.output_file = r"C:\Users\d.tanubudhi\OneDrive - Enzymedica\Documents\Sales_Estimations_Reports\ReportFiles\FranceSalesReport.csv"

    def setup_driver(self):
        """Setup Selenium WebDriver with optimized options."""
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option("prefs", {"download.default_directory": CONFIG["europe_download_path"]})
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless")
        options.add_argument("--log-level=3")

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
            france_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='France']]"))
            )
            france_button.click()
            logger.info("Clicked on France button")

            select_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//button[contains(@class, "full-page-account-switcher-buttons")]')
                )
            )
            select_button.click()
            logger.info("Clicked on 'Select Account - France' button")

        except:
            logger.info("'France' button not found")

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
    
    def rename_latest_download(self):
        """Rename the latest downloaded report file."""
        folder = CONFIG["europe_download_path"]
        files = [f for f in os.listdir(folder) if f.endswith("CustomTransaction.csv")]

        if not files:
            logger.warning("No CustomTransaction.csv file found to rename.")
            return

        latest_file = max([os.path.join(folder, f) for f in files], key=os.path.getmtime)

        # Extract date from filename
        match = re.search(
            r"(\d{4}[A-Za-z]{3}\d{1,2})-\d{4}[A-Za-z]{3}\d{1,2}CustomTransaction\.csv",
            os.path.basename(latest_file)
        )
        if not match:
            logger.warning("Filename format doesn't match expected pattern.")
            return

        date_str = match.group(1)
        try:
            date_obj = datetime.strptime(date_str, "%Y%b%d")
        except ValueError as e:
            logger.error(f"Date parsing failed: {e}")
            return

        formatted_date = date_obj.strftime("%Y-%m-%d")
        new_filename = f"france_sales_{formatted_date}.csv"
        new_filepath = os.path.join(folder, new_filename)

        os.rename(latest_file, new_filepath)
        logger.info(f"Renamed file to: {new_filepath}")
    
    def append_latest_report_master_file(self):
        FILE_PATTERN = re.compile(r"france_sales_\d{4}-\d{2}-\d{2}\.csv")
        matching_files = [
            f for f in os.listdir(self.report_folder)
            if FILE_PATTERN.match(f)
        ]

        if not matching_files:
            logger.info("No matching report files found.")
            return

        matching_files_paths = [os.path.join(self.report_folder, f) for f in matching_files]
        latest_file = max(matching_files_paths, key=os.path.getmtime)
        logger.info(f"Latest downloaded file: {latest_file}")

        try:
            master_df = pd.read_csv(self.master_file, low_memory=False)
        except ParserError as e:
            if "Expected 1 fields in line 8" in str(e):
                master_df = pd.read_csv(self.master_file, skiprows=7, low_memory=False)
                logger.warning("ParserError encountered. Retried reading file with skiprows=7.")
            else:
                raise e
        new_df = pd.read_csv(latest_file, skiprows=7)

        combined_df = pd.concat([master_df, new_df], ignore_index=True)
        combined_df.to_csv(self.master_file, index=False)
        logger.info("Appended latest report to master successfully.")

    def data_cleaning_on_master_file(self):
        df = pd.read_csv(self.master_file)
        df.columns = df.columns.str.replace(' ', '_').str.replace('/', '_')
        column_rename_map = {
                "date_heure": "date_time",
                "numéro_de_versement": "settlement_id",
                "type": "type",
                "numéro_de_la_commande": "order_id",
                "sku": "sku",
                "description": "description",
                "quantité": "quantity",
                "Marketplace": "marketplace",
                "traitement": "fulfillment",
                "ville_d'où_provient_la_commande": "order_city",
                "Région_d'où_provient_la_commande": "order_state",
                "code_postal_de_la_commande": "order_postal",
                "Modèle_de_perception_des_taxes": "tax_collection_model",
                "ventes_de_produits": "product_sales",
                "autres_frais_de_transaction": "other_transaction_fees",
                "autre": "other"
            }
        
        df.rename(columns=column_rename_map, inplace=True)
        month_map = {
            'janv.': 'Jan', 'févr.': 'Feb', 'mars': 'Mar', 'avr.': 'Apr',
            'mai': 'May', 'juin': 'Jun', 'juil.': 'Jul', 'août': 'Aug',
            'sept.': 'Sep', 'oct.': 'Oct', 'nov.': 'Nov', 'déc.': 'Dec'
        }

        for fr, eng in month_map.items():
            df["date_time"] = df["date_time"].str.replace(fr"(?<=\d\s){re.escape(fr)}(?=\s)", eng, regex=True)

        df["date_time"] = pd.to_datetime(df["date_time"], format='mixed', dayfirst=True)

        print(df["date_time"].head())  # Check after parse

        df["date"] = df["date_time"].dt.date
        df["time"] = df["date_time"].dt.time
        df["weekday"] = df["date_time"].dt.day_name()

        numerical_columns = [
            'product_sales','selling_fees', 'fba_fees', 'other_transaction_fees',
            'other', 'total']

        for col in numerical_columns:
            if col in df.columns:
                df[col] = (
                    df[col].astype(str)
                    .str.replace('.', '', regex=False)   
                    .str.replace(',', '.', regex=False)  
                )
                df[col] = pd.to_numeric(df[col], errors='coerce')

        columns_to_remove = [
                "Taxes sur la vente des produits",
                "crédits d'expédition",
                "taxe sur les crédits d’expédition",
                "crédits sur l'emballage cadeau",
                "Taxes sur les crédits cadeaux",
                "Rabais promotionnels",
                "Taxes sur les remises promotionnelles",
                "Taxes retenues sur le site de vente"
            ]
            
        df.drop(columns=[col for col in columns_to_remove if col in df.columns], inplace=True)

        rearrange_columns = [
            'date', 'time', 'weekday', 'settlement_id','type','order_id','sku', 'description','quantity','marketplace',
            'account_type','fulfillment','order_city','order_state','order_postal','tax_collection_model',
            'other_transaction_fees','other','product_sales']

        existing_columns = [col for col in rearrange_columns if col in df.columns]
        df = df[existing_columns]

        df.to_csv(self.output_file, index=False)
        logger.info("Cleaned and saved report for sales estimation.")

    def check_new_file_downloaded(self, before_files):
        """Check if a new report file matching expected pattern has been downloaded."""
        pattern = re.compile(r"\d{4}[A-Za-z]{3}\d{1,2}-\d{4}[A-Za-z]{3}\d{1,2}CustomTransaction\.csv")
        after_files = set(os.listdir(CONFIG["europe_download_path"]))
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
        getreports = EuropeBusinessReportDownloads()
        attempts += 1
        logger.info(f"Attempt #{attempts} to download the France report...")

        try:
            getreports.login()
            getreports.navigate_to_reports()

            date = datetime.today() - timedelta(days=1)
            formatted_start_date = formatted_end_date = date.strftime("%m/%d/%Y")

            before_files = set(os.listdir(CONFIG["europe_download_path"]))

            getreports.set_date_range(formatted_start_date, formatted_end_date)
            getreports.request_report()
            getreports.wait_for_report()

            success = getreports.check_new_file_downloaded(before_files)
            if success:
                getreports.rename_latest_download()
                time.sleep(2)
                getreports.append_latest_report_master_file()
                time.sleep(2)
                getreports.data_cleaning_on_master_file()
                logger.info("France reports downloaded and processed successfully!")
            else:
                logger.warning("No new file found, skipping rename and processing.")
        except Exception as e:
            logger.warning(f"Files didn't download: {e}")
        finally:
            getreports.driver.quit()

        if not success:
            time.sleep(3)

    if success:
        logger.info("Report download completed successfully.")
    else:
        logger.error("Failed to download new report after multiple attempts.")

