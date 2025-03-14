import re
import os
import sys
import logging
import pandas as pd
from datetime import datetime
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# LOGGING CONFIGURATION
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs\data_processing.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)]
    )
logger = logging.getLogger(__name__)

class DataProcessing:
    def __init__(self):
        self.report_folder = os.path.join(os.getcwd(), 'reports')

    def get_the_latest_report(self):
        """Getting the latest report file from reports folder using regex."""
        FILE_PATTERN = re.compile(r"(\d{4}[A-Za-z]{3}\d{2})-(\d{4}[A-Za-z]{3}\d{2})CustomUnifiedTransaction\.csv")
        files = os.listdir(self.report_folder)

        valid_files = []
        for file in files:
            match = FILE_PATTERN.search(file)
            if match:
                date_str = match.group(1) 
                try:
                    date_obj = datetime.strptime(date_str, "%Y%b%d") 
                    valid_files.append((date_obj, file))
                except ValueError:
                    logger.warning(f"Skipping invalid date format in filename: {file}")

        if not valid_files:
            logger.info("No valid report file found.")
            return None

        latest_file = max(valid_files, key=lambda x: x[0])[1]
        latest_file_path = os.path.join(self.report_folder, latest_file)
        logger.info(f"Latest report found: {latest_file_path}")
        return latest_file_path

    def read_csv(self):
        """Reads and processes the latest report file."""
        latest_file = self.get_the_latest_report()
        if not latest_file:
            logger.error("No valid report file found. Exiting process.")
            return

        logger.info(f"Reading file: {latest_file}")
        df = pd.read_csv(latest_file, skiprows=7)

        df = df[~df['type'].isin(['Amazon Fees', 'FBA Inventory Fee'])]

        df.columns = df.columns.str.replace(' ', '_')

        df['data_time'] = pd.to_datetime(df['date/time'], errors='coerce')

        numerical_columns = [
            'quantity', 'product_sales', 'product_sales_tax', 'shipping_credits',
            'shipping_credits_tax', 'gift_wrap_credits', 'giftwrap_credits_tax', 'Regulatory_Fee',
            'Tax_On_Regulatory_Fee', 'promotional_rebates', 'promotional_rebates_tax',
            'marketplace_withheld_tax', 'selling_fees', 'fba_fees', 'other_transaction_fees',
            'other', 'total'
        ]

        for col in numerical_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df['sales'] = (
            df.get('product_sales', 0).astype(float) +
            df.get('product_sales_tax', 0).astype(float) +
            df.get('shipping_credits', 0).astype(float) +
            df.get('shipping_credits_tax', 0).astype(float) +
            df.get('gift_wrap_credits', 0).astype(float) +
            df.get('giftwrap_credits_tax', 0).astype(float) +
            df.get('Regulatory_Fee', 0).astype(float)
        ).round(2)

        df['discounts'] = (
            df.get('promotional_rebates', 0).astype(float) + 
            df.get('promotional_rebates_tax', 0).astype(float)
        ).round(2)

        df['amazon_fee'] = (
            df.get('marketplace_withheld_tax', 0).astype(float) +
            df.get('selling_fees', 0).astype(float)
        ).round(2)

        # Remove unwanted columns
        columns_to_remove = [
            'product_sales', 'product_sales_tax', 'shipping_credits',
            'shipping_credits_tax', 'gift_wrap_credits', 'giftwrap_credits_tax', 'Regulatory_Fee',
            'Tax_On_Regulatory_Fee', 'promotional_rebates', 'promotional_rebates_tax',
            'marketplace_withheld_tax', 'selling_fees', 'data_time'
        ]

        df.drop(columns=[col for col in columns_to_remove if col in df.columns], inplace=True)

        # Save processed file
        current_date = datetime.now().strftime("%Y-%m-%d")
        output_folder = os.path.join(os.getcwd(), "outputfiles")
        os.makedirs(output_folder, exist_ok=True)
        output_file_path = os.path.join(output_folder, f"transaction_data_{current_date}.csv")

        df.to_csv(output_file_path, index=False)
        logger.info(f"Cleaned data saved to: {output_file_path}")

if __name__ == "__main__":
    processor = DataProcessing()
    processor.read_csv()