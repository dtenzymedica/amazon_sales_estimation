import os
import re
import json
import sys
import warnings
import pandas as pd
import logging
from datetime import datetime, timedelta, date
from pandas.errors import ParserError

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# LOGGING CONFIGURATION
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r'C:\Users\d.tanubudhi\amazon_sales_estimation\logs\sales_estimation_report.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class SalesEstimation:
    def __init__(self):
        self.master_file = r"C:\Users\d.tanubudhi\OneDrive - Enzymedica\Documents\Sales_Estimations_Reports\MasterFiles\EnzymeScienceCustomTransaction.csv"
        self.report_folder = r'C:\Users\d.tanubudhi\amazon_sales_estimation\reports\enzyme-science-reports'
        self.material_master_path = r"C:\Users\d.tanubudhi\amazon_sales_estimation\reports\Enzymedica - Material Master 03172025.xlsx"
        self.output_path = r"C:\Users\d.tanubudhi\OneDrive - Enzymedica\Documents\Sales_Estimations_Reports\ReportFiles\EnzymeScienceSalesReport.csv"

    def append_latest_report_master_file(self):
        FILE_PATTERN = re.compile(r"(\d{4}[A-Za-z]{3}\d{1,2})-(\d{4}[A-Za-z]{3}\d{1,2})CustomTransaction\.csv")
        all_files = os.listdir(self.report_folder)
        logger.info(f"Files in folder: {all_files}")  # Optional debug log

        matching_files = [f for f in all_files if FILE_PATTERN.match(f)]

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
        df = df.loc[:, ~df.columns.duplicated()]  # remove dupes
        df["date_time"] = pd.to_datetime(df["date_time"].astype(str).str.replace(" PST", "", regex=False))

        df["date"] = df["date_time"].dt.date
        df["time"] = df["date_time"].dt.time
        df["weekday"] = df["date_time"].dt.day_name()

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

        columns_to_remove = ['data_time']
        df.drop(columns=[col for col in columns_to_remove if col in df.columns], inplace=True)

        rearrange_columns = [
            'date', 'time', 'weekday', 'settlement_id','type','order_id','sku', 'description',
            'quantity','marketplace', 'account_type','fulfillment','order_city','order_state','order_postal',
            'tax_collection_model', 'other_transaction_fees','other','product_sales', 'product_sales_tax', 
            'shipping_credits', 'shipping_credits_tax', 'gift_wrap_credits', 'giftwrap_credits_tax', 
            'Regulatory_Fee', 'Tax_On_Regulatory_Fee', 'promotional_rebates', 'promotional_rebates_tax', 
            'marketplace_withheld_tax',  'selling_fees', 'fba_fees', 'other_transaction_fees', 'other', 'total'
            ]

        existing_columns = [col for col in rearrange_columns if col in df.columns]
        df = df[existing_columns]

        df.to_csv(self.output_path, index=False)
        logger.info("Cleaned and saved report for sales estimation.")

    def sales_estimation(self, selected_date):
        df = pd.read_csv(self.output_path)
        df['date'] = pd.to_datetime(df['date'])

        df_day_sales = df[['date', 'time', 'weekday', 'sku', 'description', 'product_sales']].copy()
        df_day_sales['product_sales'] = df_day_sales['product_sales'].astype(float)
        df_day_sales['weekday'] = df_day_sales['date'].dt.day_name()

        today = datetime.today()
        cutoff_date = datetime(today.year, today.month, selected_date)
        report_date = cutoff_date - timedelta(days=1)
        month_start = report_date.replace(day=1)

        df_actual = df_day_sales[
            (df_day_sales['date'] >= month_start) &
            (df_day_sales['date'] <= report_date)
        ]
        actual_sales_to_date = df_actual['product_sales'].sum()

        logger.info(f"Actual sales from earliest record to {cutoff_date.date() - timedelta(days=1)}: {actual_sales_to_date:,.2f}")

        # Rolling 4-day cascading averages for each weekday
        def get_dynamic_last_4_day_averages(df_estimation, cutoff_date):
            df_filtered = df_estimation[df_estimation['date'] < cutoff_date].copy()
            df_filtered['date'] = pd.to_datetime(df_filtered['date'])
            df_filtered['weekday'] = df_filtered['date'].dt.day_name()

            df_grouped = (
                df_filtered.groupby(['date', 'weekday'])['product_sales']
                .sum()
                .reset_index()
                .sort_values(by='date', ascending=False)
                .reset_index(drop=True)
            )

            weekday_avgs = {}

            for weekday in df_grouped['weekday'].unique():
                weekday_rows = df_grouped[df_grouped['weekday'] == weekday].reset_index(drop=True)
                points = []

                if len(weekday_rows) >= 4:
                    points.append(weekday_rows.loc[0:3, 'product_sales'].mean())
                if len(weekday_rows) >= 5:
                    vals = list(weekday_rows.loc[1:3, 'product_sales']) + [weekday_rows.loc[4, 'product_sales']]
                    points.append(sum(vals) / 4)
                if len(weekday_rows) >= 6:
                    vals = list(weekday_rows.loc[2:3, 'product_sales']) + list(weekday_rows.loc[4:5, 'product_sales'])
                    points.append(sum(vals) / 4)
                if len(weekday_rows) >= 7:
                    vals = [weekday_rows.loc[3, 'product_sales']] + list(weekday_rows.loc[4:6, 'product_sales']) + [weekday_rows.loc[0, 'product_sales']]
                    points.append(sum(vals) / 4)

                if points:
                    avg_total = round(sum(points) / len(points), 2)
                    weekday_avgs[weekday] = avg_total
                    logger.info(f"{weekday} rolling avg from {len(points)} combinations: {avg_total}")
                else:
                    logger.warning(f"Not enough records for {weekday} to compute cascading 4-day average.")
                    weekday_avgs[weekday] = 0.0

            return pd.Series(weekday_avgs)

        weekday_avg_sales = get_dynamic_last_4_day_averages(df_day_sales, cutoff_date)

        report_month_end = report_date.replace(day=1) + pd.offsets.MonthEnd(0)
        is_last_day = report_date.date() == report_month_end.date()

        logger.info(f"Report date: {report_date.date()}, Month end: {report_month_end.date()}, Is last day? {is_last_day}")

        if not is_last_day:
            remaining_days = pd.date_range(start=cutoff_date, end=report_month_end)
            remaining_weekdays = remaining_days.day_name()
            remaining_sales_estimate = pd.Series(remaining_weekdays.map(weekday_avg_sales)).fillna(0).sum()
            total_estimation = actual_sales_to_date + remaining_sales_estimate
        else:
            logger.info("Report is for the last day of the month. Using actuals only.")
            remaining_sales_estimate = 0
            total_estimation = actual_sales_to_date

        result = {
            "market": "Enzyme Science US",
            "actual_sales": round(actual_sales_to_date, 2),
            "estimated_sales": round(remaining_sales_estimate, 2),
            "total_estimation": round(total_estimation, 2)
        }

        # Save to JSON
        report_date = cutoff_date - timedelta(days=1)
        report_date_key = report_date.strftime("%Y-%m-%d")
        output_path = r"C:\Users\d.tanubudhi\amazon_sales_estimation\sales-estimation\sales_results.json"
        try:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                with open(output_path, 'r') as f:
                    all_data = json.load(f)
            else:
                all_data = {}

            if report_date_key  not in all_data:
                all_data[report_date_key] = []

            all_data[report_date_key] = [x for x in all_data[report_date_key] if x["market"] != result["market"]]
            all_data[report_date_key].append(result)

            with open(output_path, 'w') as f:
                json.dump(all_data, f, indent=2)

            logger.info(f"Saved sales estimation for {result['market']} to JSON.")
        except Exception as e:
            logger.error(f"Failed to write JSON: {e}")

        return result
    
if __name__ == "__main__":
    logger.info("Sales Estimation Report started.")
    estimator = SalesEstimation()
    estimator.append_latest_report_master_file()
    estimator.data_cleaning_on_master_file()
    estimator.sales_estimation(selected_date=datetime.today().day)
