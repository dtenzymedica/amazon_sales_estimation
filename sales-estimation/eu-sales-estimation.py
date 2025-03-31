import os
import sys
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
            "Germany": r'c:\Users\d.tanubudhi\Documents\GermanySalesReport.csv',
            "Italy": r"c:\Users\d.tanubudhi\Documents\ItalySalesReport.csv",
            "France": r"c:\Users\d.tanubudhi\Documents\FranceSalesReport.csv",
            "Spain": r"c:\Users\d.tanubudhi\Documents\SpainSalesReport.csv"
        }

    def multi_country_sales_estimation(self, selected_date):
        today = datetime.today()
        month_start = datetime(today.year, today.month, 1)
        month_cutoff = datetime(today.year, today.month, selected_date - 1)
        month_end = pd.Timestamp(month_start) + pd.offsets.MonthEnd(1)

        summary_message = (
            f"<p>This is the consolidated <strong>Amazon EU sales estimation</strong> report for the following markets:</p>"
            f"<ul>{''.join([f'<li>{country}</li>' for country in self.master_files.keys()])}</ul>"
            f"<p>The report includes actual and estimated sales data for the month of <strong>{month_start.strftime('%B %Y')}</strong>.</p><br>"
        )

        for country, file_path in self.master_files.items():
            try:
                df = pd.read_csv(file_path)
                df['date'] = pd.to_datetime(df['date'])

                df_day_sales = df[['date', 'time', 'weekday', 'sku', 'description', 'product_sales']].copy()
                df_day_sales['product_sales'] = df_day_sales['product_sales'].astype(float)
                df_day_sales['weekday'] = df_day_sales['date'].dt.day_name()

                df_march = df_day_sales[
                    (df_day_sales['date'] >= month_start) &
                    (df_day_sales['date'] <= month_cutoff)]

                actual_sales_to_date = df_march['product_sales'].sum()

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

                        if len(weekday_rows) >= 4:
                            points = []
                            day1 = weekday_rows.loc[0:3, 'product_sales'].mean()
                            points.append(day1)

                            if len(weekday_rows) >= 5:
                                vals = list(weekday_rows.loc[1:3, 'product_sales']) + [weekday_rows.loc[4, 'product_sales']]
                                points.append(sum(vals) / 4)

                            if len(weekday_rows) >= 6:
                                vals = list(weekday_rows.loc[2:3, 'product_sales']) + list(weekday_rows.loc[4:5, 'product_sales'])
                                points.append(sum(vals) / 4)

                            if len(weekday_rows) >= 7:
                                vals = [weekday_rows.loc[3, 'product_sales']] + list(weekday_rows.loc[4:6, 'product_sales']) + [weekday_rows.loc[0, 'product_sales']]
                                points.append(sum(vals) / 4)

                            avg_total = round(sum(points) / len(points), 2)
                            weekday_avgs[weekday] = avg_total

                    return pd.Series(weekday_avgs)

                weekday_avg_sales = get_dynamic_last_4_day_averages(df_day_sales, month_cutoff + timedelta(days=1))

                remaining_days = pd.date_range(start=month_cutoff + timedelta(days=1), end=month_end)
                remaining_weekdays = remaining_days.day_name()

                remaining_sales_estimate = pd.Series(remaining_weekdays.map(weekday_avg_sales)).sum()
                total_estimate = actual_sales_to_date + remaining_sales_estimate

                summary_message += (
                    f"<h3>{country}</h3>"
                    f"<p>Actual sales (from {month_start.date()} to {month_cutoff.date()}): ${actual_sales_to_date:,.2f} <br>"
                    f"Estimated sales (from {(month_cutoff + timedelta(days=1)).date()} to {month_end.date()}): ${remaining_sales_estimate:,.2f} <br>"
                    f"Estimated Total {month_start.strftime('%B %Y')} Sales: ${total_estimate:,.2f}</p><br>"
                )

            except Exception as e:
                logger.warning(f"Error processing {country}: {e}")
                summary_message += f"<h3>{country}</h3><p><strong style='color:red;'>Error: {e}</strong></p><br>"

        subject = f"Amazon EU Sales Estimation – {', '.join(self.master_files.keys())} – {month_start.strftime('%B %Y')}"
        self.send_sales_estimation_email(subject, summary_message)

    def send_sales_estimation_email(self, subject, message):
        try:
            smtp_server = "smtp.office365.com"
            smtp_port = 587
            sender_email = "d.tanubudhi@enzymedica.com"
            sender_password = os.getenv("EMAIL_PASSWORD")

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ", ".join([
                "d.tanubudhi@enzymedica.com"
                "b.bechard@enzymedica.com",
                "g.cabrera@enzymedica.com",
                "carolyn@enzymedica.com"
            ])
            msg['Subject'] = subject

            html_message = f"""
            <html>
                <body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333;'>
                    <h2>Amazon EU Sales Estimation Report</h2>
                    {message}
                    <p style='margin-top: 20px;'>
                        <strong>Note:</strong> This report is auto-generated by the Amazon Sales Automation system.
                    </p>
                    <p style='margin-top: 40px;'>Best regards,<br><strong>Automation Bot</strong></p>
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
    logger.info("Starting EU Sales Estimation Report...")
    estimator = SalesEstimation()
    estimator.multi_country_sales_estimation(selected_date=datetime.today().day)
