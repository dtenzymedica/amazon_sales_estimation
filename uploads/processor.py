import subprocess
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r'C:\Users\d.tanubudhi\amazon_sales_estimation\logs\pipeline_process.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

PYTHON_PATH = r'C:\Users\d.tanubudhi\amazon_sales_estimation\venv\Scripts\python.exe'
SCRIPTS = [
    r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\business-report-download.py",
    r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\data-cleaning.py",
    r"C:\Users\d.tanubudhi\amazon_sales_estimation\uploads\s3-uploads.py"
]

def run_scripts():
    for script in SCRIPTS:
        logging.info(f"Running scripts: {script}")
        result = subprocess.run([PYTHON_PATH, script], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"Successfully excuted {script}\n{result.stdout}")
        else:
            logging.error(f"Error excuted {script}\n{result.stderr}")
            break

if __name__ == "__main__":
    run_scripts()
