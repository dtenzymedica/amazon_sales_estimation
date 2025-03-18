import re
import sys
import boto3
import logging
from datetime import datetime
from dotenv import load_dotenv
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(r"C:\Users\d.tanubudhi\amazon_sales_estimation\logs\s3-uploads.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class S3Uploader:
    def __init__(self):
        """Initialize S3Uploader by loading environment variables and setting up S3 client."""
        self.env_vars = self.load_environment_variables()
        self.s3_client = self.get_s3_client()
        self.bucket_name = self.env_vars["bucket_name"]
        self.local_files_dir = self.env_vars["local_files_dir"]
        self.base_s3_path = self.env_vars["base_s3_path"]
        self.reports_generation_date = self.env_vars["reports_generation_date"]

    def load_environment_variables(self):
        """Load environment variables and ensure required keys exist."""
        dotenv_path = os.path.join(os.getcwd(), ".env")
        load_dotenv(dotenv_path=dotenv_path, override=True)

        required_vars = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "S3_BUCKET_NAME",
            "LOCAL_FILES_DIR",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        return {
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "bucket_name": os.getenv("S3_BUCKET_NAME"),
            "local_files_dir": os.getenv("LOCAL_FILES_DIR"),
            "base_s3_path":  os.getenv("BASE_S3_PATH", "sales_estimation_reports"),
            "reports_generation_date": os.getenv(
                "REPORTS_GENERATION_DATE", datetime.now().strftime("%Y-%m-%d")
            ),
        }

    def get_s3_client(self):
        """Create and return an S3 client session."""
        try:
            session = boto3.session.Session(
                aws_access_key_id=self.env_vars["aws_access_key_id"],
                aws_secret_access_key=self.env_vars["aws_secret_access_key"],
            )
            return session.client("s3")
        except Exception as e:
            logger.error(f"Failed to create S3 client: {e}")
            raise

    def get_target_directory(self):
        """Generate S3 path structure: sales_estimation_reports/YYYY/MM/"""
        reports_date = datetime.strptime(self.reports_generation_date, "%Y-%m-%d")
        year = reports_date.strftime("%Y")
        month = reports_date.strftime("%m")
        return f"{year}/{month}"

    def check_and_create_folder(self, s3_prefix):
        """Check if the S3 folder exists and create it if not present."""
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name, Prefix=s3_prefix, MaxKeys=1
        )

        if "Contents" not in response:
            logger.info(f"Creating missing folder: {s3_prefix}")
            self.s3_client.put_object(Bucket=self.bucket_name, Key=s3_prefix)
        else:
            logger.info(f"Folder already exists: {s3_prefix}")

    def get_latest_file(self):
        """Find the latest file in the directory based on the naming pattern."""
        FILE_PATTERN = re.compile(r"transaction_data_(\d{4}-\d{2}-\d{2})\.csv")

        local_path = Path(self.local_files_dir)
        if not local_path.exists() or not local_path.is_dir():
            logger.error(f"Local directory does not exist: {self.local_files_dir}")
            return None

        valid_files = []
        for file_path in local_path.iterdir():
            if file_path.is_file():
                match = FILE_PATTERN.search(file_path.name)
                if match:
                    try:
                        date_obj = datetime.strptime(match.group(1), "%Y-%m-%d")
                        valid_files.append((date_obj, file_path))
                    except ValueError:
                        logger.warning(f"Skipping file with invalid date format: {file_path.name}")

        if not valid_files:
            logger.error("No valid transaction data files found.")
            return None

        latest_file = max(valid_files, key=lambda x: x[0])[1]
        logger.info(f"Latest file found: {latest_file}")
        return latest_file

    def upload_latest_file_to_s3(self):
        """Upload the latest file to S3 in year/month structure."""
        latest_file = self.get_latest_file()

        if not latest_file:
            logger.error("No valid file found for upload.")
            return False

        target_dir = self.get_target_directory()
        s3_prefix = f"{self.base_s3_path}/{target_dir}/"
        self.check_and_create_folder(s3_prefix)

        # Extract year and month from the file name
        file_name = latest_file.name
        match = re.search(r"transaction_data_(\d{4})-(\d{2})-(\d{2})\.csv", file_name)

        if not match:
            logger.error(f"Invalid filename format: {file_name}")
            return False

        s3_key = f"{s3_prefix}{file_name}"

        try:
            logger.info(f"Uploading {latest_file} to s3://{self.bucket_name}/{s3_key}")

            self.s3_client.upload_file(
                str(latest_file),
                self.bucket_name,
                s3_key,
            )

            logger.info(f"Successfully uploaded {latest_file} to s3://{self.bucket_name}/{s3_key}")
            return True

        except Exception as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False

    def close_s3_client(self):
        """Close the S3 client session."""
        self.s3_client.close()

if __name__ == "__main__":
    try:
        uploader = S3Uploader()
        success = uploader.upload_latest_file_to_s3()
        uploader.close_s3_client()

        if success:
            logger.info("File upload process completed successfully.")
        else:
            logger.error("File upload process failed.")

    except Exception as e:
        logger.error(f"An error occurred during the upload process: {e}")
