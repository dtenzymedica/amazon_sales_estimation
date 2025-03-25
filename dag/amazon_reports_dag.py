from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import subprocess

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

def run_script(path):
    subprocess.run(['python', path], check=True)

with DAG(
    'amazon_report_pipeline',
    default_args=default_args,
    description='Automate Amazon report tasks',
    schedule_interval='@daily',  # Change as needed
    start_date=datetime(2025, 3, 25),
    catchup=False,
    tags=['amazon'],
) as dag:
    
    download = PythonOperator(
        task_id='download_report',
        python_callable=run_script,
        op_args=['C:/Users/d.tanubudhi/amazon_sales_estimation/scraper/business-report-download.py']
    )

    clean = PythonOperator(
        task_id='clean_data',
        python_callable=run_script,
        op_args=['C:/Users/d.tanubudhi/amazon_sales_estimation/scraper/data-cleaning.py']
    )

    upload = PythonOperator(
        task_id='upload_to_s3',
        python_callable=run_script,
        op_args=['C:/Users/d.tanubudhi/amazon_sales_estimation/uploads/s3-uploads.py']
    )

    download >> clean >> upload
