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
        logging.FileHandler(r'C:\Users\d.tanubudhi\amazon_sales_estimation\logs\data_processing.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)]
    )
logger = logging.getLogger(__name__)

class DataProcessing:
    def __init__(self):
        self.report_folder = r'C:\Users\d.tanubudhi\amazon_sales_estimation\reports'

    def get_the_latest_report(self):
        """Getting the latest report file from reports folder using regex."""
        FILE_PATTERN = re.compile(r"(\d{4}[A-Za-z]{3}\d{2})-(\d{4}[A-Za-z]{3}\d{2})CustomUnifiedTransaction\.csv")
        files = os.listdir(self.report_folder)

        valid_files = []
        for file in files:
            match = FILE_PATTERN.search(file)
            if match:
                date_str = match.group(1)  # Extract first date
                try:
                    date_obj = datetime.strptime(date_str, "%Y%b%d")
                    valid_files.append((date_obj, file, date_str))
                except ValueError:
                    logger.warning(f"Skipping invalid date format in filename: {file}")

        if not valid_files:
            logger.info("No valid report file found.")
            return None, None

        latest_file = max(valid_files, key=lambda x: x[0])
        latest_file_path = os.path.join(self.report_folder, latest_file[1])
        extracted_date = latest_file[2]
        logger.info(f"Latest report found: {latest_file_path} with extracted date {extracted_date}")
        return latest_file_path, extracted_date
    
    def read_material_master(self):
        """Material Master file to merge the reports."""
        try:
            logger.info("Reading Material Master file.")
            material_master_path = r"C:\Users\d.tanubudhi\amazon_sales_estimation\reports\Enzymedica - Material Master 03172025.xlsx"
            dff = pd.read_excel(material_master_path, sheet_name='All ASINs with Priority')
            dff = dff[['seller-sku', 'ASIN']].rename(columns={'seller-sku': 'sku'})
            dff['sku'] = dff['sku'].str.replace('FFP', '').replace(' FFP', '')
            logger.info("Completed loading Material Master file.")
            return dff
        except Exception as e:
            logger.warning("Couldn't read Material Master file.")
            return pd.DataFrame()

    def read_csv(self):
        """Reads and processes the latest report file."""
        latest_file, extracted_date = self.get_the_latest_report()
        if not latest_file:
            logger.error("No valid report file found. Exiting process.")
            return

        logger.info(f"Reading file: {latest_file}")
        df = pd.read_csv(latest_file, skiprows=7)

        df = df[~df['type'].isin(['Amazon Fees', 'FBA Inventory Fee'])]

        df.columns = df.columns.str.replace(' ', '_').str.replace('/', '_')

        df['data_time'] = pd.to_datetime(df['date/time'], errors='coerce')

        df = df.dropna(subset=['sku']).reset_index(drop=True)

        df['sku'] = df['sku'].str.replace(r'\s*FFP\s*', '', regex=True)

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
            df.get('selling_fees', 0).astype(float) +
            df.get('fba_fees').astype(float)
        ).round(2)

        # Remove unwanted columns
        columns_to_remove = [
            'product_sales', 'product_sales_tax', 'shipping_credits',
            'shipping_credits_tax', 'gift_wrap_credits', 'giftwrap_credits_tax', 'Regulatory_Fee',
            'Tax_On_Regulatory_Fee', 'promotional_rebates', 'promotional_rebates_tax',
            'marketplace_withheld_tax', 'data_time'
        ]

        df.drop(columns=[col for col in columns_to_remove if col in df.columns], inplace=True)

        material_master = self.read_material_master()
        df = df.merge(material_master, on='sku', how='left')

        rearrange_columns = [
            'date_time','settlement_id','type','order_id','sku','ASIN', 'description','quantity','marketplace',
            'account_type','fulfillment','order_city','order_state','order_postal','tax_collection_model',
            'other_transaction_fees','other','sales', 'discounts', 'amazon_fee', 'total'
        ]

        existing_columns = [col for col in rearrange_columns if col in df.columns]
        df = df[existing_columns]

        formatted_date = datetime.strptime(extracted_date, "%Y%b%d").strftime("%Y-%m-%d")

        output_folder = os.path.join(os.getcwd(), "outputfiles")
        os.makedirs(output_folder, exist_ok=True)
        output_file_path = os.path.join(output_folder, f"transaction_data_{formatted_date}.csv")

        df.to_csv(output_file_path, index=False)
        logger.info(f"Cleaned data saved to: {output_file_path}")

if __name__ == "__main__":
    processor = DataProcessing()
    processor.read_csv()
