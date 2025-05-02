import subprocess
import logging
import os
from dotenv import load_dotenv

env_path = r'C:\Users\d.tanubudhi\amazon_sales_estimation\.env'
load_dotenv(dotenv_path=env_path)

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
    r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\enzymedica-sales-report-scraper.py",
    r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\data-cleaning.py",
    r"C:\Users\d.tanubudhi\amazon_sales_estimation\uploads\s3-uploads.py",
    # r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\enzyme-science-scraper.py",
    r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\enzymedica_germany.py",
    r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\enzymedica-france.py",
    r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\enzymedica-italy.py",
    r"C:\Users\d.tanubudhi\amazon_sales_estimation\scraper\enzymedica-spain.py"
]

def run_scripts():
    env_vars = os.environ.copy()  

    for script in SCRIPTS:
        logging.info(f"Running script: {script}")
        result = subprocess.run([PYTHON_PATH, script], capture_output=True, text=True, env=env_vars)

        if result.returncode == 0:
            logging.info(f"Successfully executed {script}\n{result.stdout}")
        else:
            logging.error(f"Error executing {script}\n{result.stderr}")
            break

if __name__ == "__main__":
    run_scripts()