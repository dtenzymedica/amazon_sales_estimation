import os
import re
import json
import sys
import smtplib
import warnings
import pandas as pd
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
        self.master_file = r'C:\Users\d.tanubudhi\Documents\EnzymeScienceCustomTransaction.csv'
        self.report_folder = r'C:\Users\d.tanubudhi\amazon_sales_estimation\reports\enzyme-science-reports'
        self.material_master_path = r"C:\Users\d.tanubudhi\amazon_sales_estimation\reports\Enzymedica - Material Master 03172025.xlsx"
        self.output_path = r'c:\Users\d.tanubudhi\Documents\enzyme_science_sales_report.csv'

    def append_latest_report_master_file(self):
        FILE_PATTERN = re.compile(r"(\d{4}[A-Za-z]{3}\d{2})-(\d{4}[A-Za-z]{3}\d{2})CustomTransaction\.csv")
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
        df["date_time"] = pd.to_datetime(df["date_time"].str.replace(" PST", "", regex=False))
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

        columns_to_remove = [
            'product_sales_tax', 'shipping_credits', 'shipping_credits_tax', 'gift_wrap_credits',
            'giftwrap_credits_tax', 'Regulatory_Fee', 'Tax_On_Regulatory_Fee', 'promotional_rebates',
            'promotional_rebates_tax', 'marketplace_withheld_tax', 'data_time']
        df.drop(columns=[col for col in columns_to_remove if col in df.columns], inplace=True)

        rearrange_columns = [
            'date', 'time', 'weekday', 'settlement_id','type','order_id','sku', 'description','quantity','marketplace',
            'account_type','fulfillment','order_city','order_state','order_postal','tax_collection_model',
            'other_transaction_fees','other','product_sales']

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
        target_year = today.year
        target_month = today.month
        month_start = datetime(target_year, target_month, 1)
        month_cutoff = datetime(target_year, target_month, selected_date - 1)

        df_march = df_day_sales[
            (df_day_sales['date'] >= month_start) &
            (df_day_sales['date'] <= month_cutoff)]

        actual_sales_to_date = df_march['product_sales'].sum()
        logger.info(f"Sales from {month_start.date()} to {month_cutoff.date()}: {actual_sales_to_date:,.2f}")

        def get_dynamic_last_4_day_averages(df_estimation, cutoff_date):
            df_filtered = df_estimation[df_estimation['date'] < cutoff_date].copy()
            df_filtered['date'] = pd.to_datetime(df_filtered['date'])
            df_filtered['weekday'] = df_filtered['date'].dt.day_name()

            # Group by day and sum product_sales
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

                    # Day 1: last 4 rows (index 0 to 3)
                    day1 = weekday_rows.loc[0:3, 'product_sales'].mean()
                    points.append(day1)

                    # Day 2: rows 1-3 + 4
                    if len(weekday_rows) >= 5:
                        vals = list(weekday_rows.loc[1:3, 'product_sales']) + [weekday_rows.loc[4, 'product_sales']]
                        day2 = sum(vals) / 4
                        points.append(day2)

                    # Day 3: rows 2-3 + 4-5
                    if len(weekday_rows) >= 6:
                        vals = list(weekday_rows.loc[2:3, 'product_sales']) + list(weekday_rows.loc[4:5, 'product_sales'])
                        day3 = sum(vals) / 4
                        points.append(day3)

                    # Day 4: row 3 + rows 4-6 + row 0
                    if len(weekday_rows) >= 7:
                        vals = [weekday_rows.loc[3, 'product_sales']] + list(weekday_rows.loc[4:6, 'product_sales']) + [weekday_rows.loc[0, 'product_sales']]
                        day4 = sum(vals) / 4
                        points.append(day4)

                    avg_total = round(sum(points) / len(points), 2)
                    weekday_avgs[weekday] = avg_total
                else:
                    logger.warning(f"Not enough records for {weekday} to compute cascading 4-day average.\n")

            return pd.Series(weekday_avgs)


        weekday_avg_sales = get_dynamic_last_4_day_averages(df_day_sales, month_cutoff + timedelta(days=1))

        month_end = pd.Timestamp(f"{target_year}-{target_month}-01") + pd.offsets.MonthEnd(1)
        remaining_days = pd.date_range(start=month_cutoff + timedelta(days=1), end=month_end)
        remaining_weekdays = remaining_days.day_name()

        remaining_sales_estimate = pd.Series(remaining_weekdays.map(weekday_avg_sales)).sum()

        summary_message = (
            f"\nSales from {month_start.date()} to {month_cutoff.date()}: ${actual_sales_to_date:,.2f}\n"
            f"\nEstimated sales from {month_cutoff.date() + timedelta(days=1)} to {month_end.date()}: ${remaining_sales_estimate:,.2f}\n"
            f"Estimated Total {month_start.strftime('%B %Y')} Sales: ${(actual_sales_to_date + remaining_sales_estimate):,.2f}"
        )
        logger.info(summary_message)

        # Send email to stakeholders
        self.send_sales_estimation_email(
            subject=f"Amazon Sales Estimation (US Enzyme Science) - {month_start.strftime('%B %Y')}",
            message=summary_message,
            to_emails=["d.tanubudhi@enzymedica.com", "b.bechard@enzymedica.com", "g.cabrera@enzymedica.com", "carolyn@enzymedica.com"]
        )
            
    def send_sales_estimation_email(self, subject, message, to_emails):
        """Send sales estimation results via email."""
        try:
            smtp_server = "smtp.office365.com"
            smtp_port = 587
            sender_email = "d.tanubudhi@enzymedica.com"
            sender_password = os.getenv("EMAIL_PASSWORD") 

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ", ".join(to_emails)
            msg['Subject'] = subject

            html_message = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <h2> Enzyme Science US Amazon Sales Estimation Report</h2>
                    <p>{message.replace('\n', '<br>')}</p>

                    <p style="margin-top: 20px;">
                        <strong>Note:</strong> This report is auto-generated by the Amazon Sales Automation system.
                    </p>

                    <p style="margin-top: 40px;">Best regards,<br><strong>Automation Bot</strong></p>
                </body>
            </html>
            """

            msg.attach(MIMEText(html_message, 'html'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            logger.info("Sales estimation email sent successfully.")

        except Exception as e:
            logger.error(f"Failed to send email: {e}")

if __name__ == "__main__":
    logger.info("Sales Estimation Report started.")
    estimator = SalesEstimation()
    estimator.append_latest_report_master_file()
    estimator.data_cleaning_on_master_file()
    estimator.sales_estimation(selected_date=datetime.today().day)