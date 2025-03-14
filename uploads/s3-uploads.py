import os
import sys
import boto3
from datetime import datetime
from dotenv import load_dotenv
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs\s3-uploads.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)]
    )
logger = logging.getLogger(__name__)

def load_environment_variables():
    load_dotenv()
    
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'S3_BUCKET_NAME', 'LOCAL_FILES_DIR']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return {
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'bucket_name': os.getenv('S3_BUCKET_NAME'),
        'local_files_dir': os.getenv('LOCAL_FILES_DIR'),
        'base_s3_path': os.getenv('BASE_S3_PATH', 'enzymedica/business_report_sales_by_child_test'),
        'reports_generation_date': os.getenv('REPORTS_GENERATION_DATE', datetime.now())
    }

def get_s3_client(aws_access_key_id, aws_secret_access_key):
    try:
        session = boto3.session.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        s3_client = session.client('s3')
        return s3_client
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        raise


def get_target_directory(reports_generation_date):
    if type(reports_generation_date) == str:
        reports_generation_date = datetime.strptime(reports_generation_date, "%Y-%m-%d")
    year = reports_generation_date.strftime('%Y')
    month = reports_generation_date.strftime('%m')
    day = reports_generation_date.strftime('%d')
    
    return f"{year}/{month}/{day}"

def upload_files_to_s3(s3_client, bucket_name, local_dir, base_s3_path, reports_generation_date):
    """Upload all files from local directory to S3 with date-based directory structure."""
    target_dir = get_target_directory(reports_generation_date)
    s3_prefix = f"{base_s3_path}/{target_dir}/"
    
    local_path = Path(local_dir)
    
    if not local_path.exists() or not local_path.is_dir():
        logger.error(f"Local directory does not exist: {local_dir}")
        return False
    
    files_uploaded = 0
    
    try:
        for file_path in local_path.iterdir():
            if file_path.is_file():
                file_name = file_path.name
                s3_key = f"{s3_prefix}{file_name}"
                
                logger.info(f"Uploading {file_path} to s3://{bucket_name}/{s3_key}")
                
                s3_client.upload_file(
                    str(file_path),
                    bucket_name,
                    s3_key
                )
                
                files_uploaded += 1
        
        logger.info(f"Successfully uploaded {files_uploaded} files to s3://{bucket_name}/{s3_prefix}")
        return True
    
    except Exception as e:
        logger.error(f"Error uploading files to S3: {e}")
        return False

def main():
    """Main function to orchestrate the S3 upload process."""
    try:
        # Load environment variables
        env_vars = load_environment_variables()
        
        # Create S3 client
        s3_client = get_s3_client(
            env_vars['aws_access_key_id'],
            env_vars['aws_secret_access_key']
        )
        
        # Upload files
        success = upload_files_to_s3(
            s3_client,
            env_vars['bucket_name'],
            env_vars['local_files_dir'],
            env_vars['base_s3_path'],
            env_vars['reports_generation_date']
        )
        
        s3_client.close()

        if success:
            logger.info("File upload process completed successfully")
        else:
            logger.error("File upload process failed")
    
    except Exception as e:
        logger.error(f"An error occurred during the upload process: {e}")


if __name__ == "__main__":
    main()
