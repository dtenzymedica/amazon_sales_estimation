import os
import sys
import json
import smtplib
import warnings
import pandas as pd
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
        self.master_files = {
            "Germany": r"C:\Users\d.tanubudhi\OneDrive - Enzymedica\Documents\GermanySalesReport.csv",
            "Italy": r"C:\Users\d.tanubudhi\OneDrive - Enzymedica\Documents\ItalySalesReport.csv",
            "France": r"C:\Users\d.tanubudhi\OneDrive - Enzymedica\Documents\FranceSalesReport.csv",
            "Spain": r"C:\Users\d.tanubudhi\OneDrive - Enzymedica\Documents\SpainSalesReport.csv"
        }

    def multi_country_sales_estimation(self, selected_date):
        today = datetime.today()
        cutoff_date = datetime(today.year, today.month, selected_date)
        report_date = cutoff_date - timedelta(days=1)
        month_start = datetime(today.year, today.month, 1)
        month_end = pd.Timestamp(month_start) + pd.offsets.MonthEnd(1)

        output_path = r"C:\Users\d.tanubudhi\amazon_sales_estimation\sales-estimation\sales_results.json"
        all_results = []

        for country, file_path in self.master_files.items():
            try:
                df = pd.read_csv(file_path)
                df['date'] = pd.to_datetime(df['date'])

                df_day_sales = df[['date', 'time', 'weekday', 'sku', 'description', 'product_sales']].copy()
                df_day_sales['product_sales'] = df_day_sales['product_sales'].astype(float)
                df_day_sales['weekday'] = df_day_sales['date'].dt.day_name()

                today = datetime.today()
                cutoff_date = datetime(today.year, today.month, selected_date)
                month_start = datetime(today.year, today.month, 1)

                # Actual sales: strictly before the cutoff date (excluding today's partial sales)
                df_actual = df_day_sales[
                    (df_day_sales['date'] >= month_start) &
                    (df_day_sales['date'] < cutoff_date)
                ]
                actual_sales_to_date = df_actual['product_sales'].sum()

                def get_dynamic_last_4_day_averages(df_estimation, cutoff_date):
                    df_filtered = df_estimation[df_estimation['date'] < cutoff_date].copy()
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

                        if len(weekday_rows) >= 4:
                            points = []
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

                            weekday_avgs[weekday] = round(sum(points) / len(points), 2)

                    return pd.Series(weekday_avgs)

                weekday_avg_sales = get_dynamic_last_4_day_averages(df_day_sales, cutoff_date)
                month_end = pd.Timestamp(f"{today.year}-{today.month}-01") + pd.offsets.MonthEnd(1)
                remaining_days = pd.date_range(start=cutoff_date, end=month_end)
                remaining_weekdays = remaining_days.day_name()

                remaining_sales_estimate = pd.Series(remaining_weekdays.map(weekday_avg_sales)).sum()
                total_estimate = actual_sales_to_date + remaining_sales_estimate

                result = {
                    "market": f"Enzymedica EU - {country}",
                    "actual_sales": round(actual_sales_to_date, 2),
                    "estimated_sales": round(remaining_sales_estimate, 2),
                    "total_estimation": round(total_estimate, 2)
                }

                all_results.append(result)

            except Exception as e:
                logger.warning(f"Error processing {country}: {e}")

        try:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                with open(output_path, 'r') as f:
                    all_data = json.load(f)
            else:
                all_data = {}

            report_date_key = report_date.strftime("%Y-%m-%d")
            if report_date_key not in all_data:
                all_data[report_date_key] = []

            # Remove old Enzymedica EU entries from that date
            all_data[report_date_key] = [
                x for x in all_data[report_date_key]
                if not x["market"].startswith("Enzymedica EU")
            ]

            # Append new EU results under the correct key
            all_data[report_date_key].extend(all_results)

            with open(output_path, 'w') as f:
                json.dump(all_data, f, indent=2)
            logger.info(f"Saved all EU sales estimation results to {output_path}")
        except Exception as e:
            logger.error(f"Failed to write EU results JSON: {e}")

if __name__ == "__main__":
    logger.info("Starting EU Sales Estimation Report...")
    estimator = SalesEstimation()
    estimator.multi_country_sales_estimation(selected_date=datetime.today().day)
