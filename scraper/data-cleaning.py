import re
import os
import sys
import json
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
        self.report_folder = r'C:\Users\d.tanubudhi\amazon_sales_estimation\reports\enzymedica-sales-reports'
        self.json_path = r'C:\Users\d.tanubudhi\amazon_sales_estimation\sales-estimation\sku-asin.json'

    def get_the_latest_report(self):
        """Getting the latest report file from reports folder using regex."""
        FILE_PATTERN = re.compile(r"(\d{4}[A-Za-z]{3}\d{1,2})-(\d{4}[A-Za-z]{3}\d{1,2})CustomUnifiedTransaction\.csv")
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
            logger.info("Completed loading Material Master file.")
            return dff
        except Exception as e:
            logger.warning(f"Couldn't read Material Master file. {e}")
            return pd.DataFrame()

    def read_csv(self):
        """Reads and processes the latest report file."""
        latest_file, extracted_date = self.get_the_latest_report()
        if not latest_file:
            logger.error("No valid report file found. Exiting process.")
            return

        logger.info(f"Reading file: {latest_file}")
        df = pd.read_csv(latest_file, skiprows=7)
        df.columns = df.columns.str.replace(' ', '_').str.replace('/', '_')
        df["date_time"] = pd.to_datetime(df["date_time"].str.replace(" PST", "", regex=False))
        df["date"] = df["date_time"].dt.date
        df["time"] = df["date_time"].dt.time
        df["weekday"] = df["date_time"].dt.day_name()
        
        df['data_time'] = pd.to_datetime(df['date_time'], errors='coerce')

        numerical_columns = [
            'quantity', 'product_sales', 'product_sales_tax', 'shipping_credits',
            'shipping_credits_tax', 'gift_wrap_credits', 'giftwrap_credits_tax', 'Regulatory_Fee',
            'Tax_On_Regulatory_Fee', 'promotional_rebates', 'promotional_rebates_tax',
            'marketplace_withheld_tax', 'selling_fees', 'fba_fees', 'other_transaction_fees',
            'other', 'total']

        for col in numerical_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df['product_sales'] = df['product_sales'].astype(float).round(2)

        # Remove unwanted columns
        columns_to_remove = [
            'product_sales_tax', 'shipping_credits', 'shipping_credits_tax', 'gift_wrap_credits',
            'giftwrap_credits_tax', 'Regulatory_Fee', 'Tax_On_Regulatory_Fee', 'promotional_rebates',
            'promotional_rebates_tax', 'marketplace_withheld_tax', 'data_time']
        df.drop(columns=[col for col in columns_to_remove if col in df.columns], inplace=True)

        material_master = self.read_material_master()
        sku_asin_map = material_master.drop_duplicates(subset='sku').set_index('sku')['ASIN'].to_dict()

        with open(self.json_path, 'w') as f:
            json.dump(sku_asin_map, f, indent=1)

        df['ASIN'] = df['sku'].map(sku_asin_map)

        rearrange_columns = [
            'date', 'time', 'weekday', 'settlement_id','type','order_id','sku', 'ASIN', 'description','quantity','marketplace',
            'account_type','fulfillment','order_city','order_state','order_postal','tax_collection_model','other_transaction_fees', 
            'product_sales_tax', 'shipping_credits', 'shipping_credits_tax', 'gift_wrap_credits', 'giftwrap_credits_tax', 
            'Regulatory_Fee', 'Tax_On_Regulatory_Fee', 'promotional_rebates','promotional_rebates_tax', 'marketplace_withheld_tax', 
            'other','product_sales', 'total']

        existing_columns = [col for col in rearrange_columns if col in df.columns]
        df = df[existing_columns]

        formatted_date = datetime.strptime(extracted_date, "%Y%b%d").strftime("%Y-%m-%d")

        output_folder = os.path.join(os.getcwd(), "outputfiles")
        os.makedirs(output_folder, exist_ok=True)
        output_file_path = os.path.join(output_folder, f"enzymedica_transaction_data_{formatted_date}.csv")

        df.to_csv(output_file_path, index=False)
        logger.info(f"Cleaned data saved to: {output_file_path}")

if __name__ == "__main__":
    processor = DataProcessing()
    processor.read_csv()
