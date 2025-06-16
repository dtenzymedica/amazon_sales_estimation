import os
import json
import smtplib
import logging
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(r"C:\Users\d.tanubudhi\amazon_sales_estimation\logs\email_sales_estimation.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def send_sales_summary_email():
    try:
        report_date = date.today() - timedelta(days=1)
        report_date_key = report_date.strftime("%Y-%m-%d")
        json_path = r"C:\Users\d.tanubudhi\amazon_sales_estimation\sales-estimation\sales_results.json"

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"No JSON file found at {json_path}")

        with open(json_path, 'r') as f:
            sales_data = json.load(f)

        if report_date_key not in sales_data:
            raise ValueError(f"No sales data found for {report_date_key} in JSON.")

        eu_actual, eu_estimated, eu_total = 0.0, 0.0, 0.0
        grand_actual, grand_estimated, grand_total = 0.0, 0.0, 0.0
        eu_rows = []
        non_eu_rows = []

        for record in sales_data[report_date_key]:
            market = record['market']
            actual = record['actual_sales']
            estimated = record['estimated_sales']
            total = record['total_estimation']

            grand_actual += actual
            grand_estimated += estimated
            grand_total += total

            if "Enzymedica EU" in market:
                eu_actual += actual
                eu_estimated += estimated
                eu_total += total
                eu_rows.append(record)
            else:
                non_eu_rows.append(record)

        rows = ""

        # Add EU countries
        for r in eu_rows:
            rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{r['market']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">€{r['actual_sales']:,.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">€{r['estimated_sales']:,.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>€{r['total_estimation']:,.2f}</strong></td>
                </tr>
            """

        # EU Total
        rows += f"""
            <tr style="background-color: #f9f9f9; font-weight: bold;">
                <td style="padding: 8px; border: 1px solid #ddd;">Total Enzymedica EU</td>
                <td style="padding: 8px; border: 1px solid #ddd;">€{eu_actual:,.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">€{eu_estimated:,.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">€{eu_total:,.2f}</td>
            </tr>
        """

        # Non-EU markets
        for r in non_eu_rows:
            rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{r['market']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${r['actual_sales']:,.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${r['estimated_sales']:,.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>${r['total_estimation']:,.2f}</strong></td>
                </tr>
            """

        # Grand Total
        rows += f"""
            <tr style="background-color: #e6f2ff; font-weight: bold;">
                <td style="padding: 8px; border: 1px solid #ddd;">Grand Total</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${grand_actual:,.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${grand_estimated:,.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${grand_total:,.2f}</td>
            </tr>
        """

        month_start = report_date.replace(day=1)

        report_date_str = report_date.strftime("%B %#d, %Y")
        month_start_str = month_start.strftime("%B %#d, %Y")

        if month_start_str == report_date_str:
            date_range_str = f"for {report_date_str}"
        else:
            date_range_str = f"from {month_start_str} to {report_date_str}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Amazon Sales Estimation Report {date_range_str}</h2>
            <table style="border-collapse: collapse; width: 100%; margin-top: 20px;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd;">Market</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Actual Sales</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Estimated Sales</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Total Estimation</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            <p style="margin-top: 20px;">
                <strong>Note:</strong> This report is auto-generated by the Amazon Sales Automation system.
            </p>
            <div style="margin-top: 10px; font-size: 14px; background-color: #f9f9f9; border-left: 4px solid #0073e6; padding: 12px;">
            <strong>Column Guide:</strong><br>
            <ul style="margin: 6px 0 0 20px; padding: 0;">
                <li><strong>Actual Sales:</strong> Total sales from the beginning of the month up to the report date.</li>
                <li><strong>Estimated Sales:</strong> Projected sales from the report date through the end of the month, based on weekday trends. Returns 0 if no remaining days are left in the month.</li>
                <li><strong>Total Estimation:</strong> The combined value of actual and estimated sales for the entire month. If there are no remaining days in the month, this returns the actual sales value only.</li>
            </ul>
            </div>
            <p style="margin-top: 40px;">Best regards,<br><strong>Deepika</strong></p>
        </body>
        </html>
        """

        smtp_server = "smtp.office365.com"
        smtp_port = 587
        sender_email = "d.tanubudhi@enzymedica.com"
        sender_password = os.getenv("EMAIL_PASSWORD")
        recipients = [
            "b.bechard@enzymedica.com", "g.cabrera@enzymedica.com",
            "carolyn@enzymedica.com", "yamil.V@hatchecom.com",
            "fernando.T@hatchecom.com", "carlos.C@hatchecom.com"
            # "d.tanubudhi@enzymedica.com"
        ]

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = f"Amazon Sales Estimation Summary – {date_range_str}"
        msg.attach(MIMEText(html_content, "html"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        logging.info("Sales estimation summary email sent successfully.")

    except Exception as e:
        logging.error(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_sales_summary_email()
