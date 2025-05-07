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

    def upload_all_reports_to_s3(self):
        """Upload all files in the directory to S3 under base_s3_path root (flat structure)."""
        local_path = Path(self.local_files_dir)
        if not local_path.exists() or not local_path.is_dir():
            logger.error(f"Local directory does not exist: {self.local_files_dir}")
            return False

        s3_prefix = f"{self.base_s3_path}/"
        report_files = [f for f in local_path.iterdir() if f.is_file()]
        
        if not report_files:
            logger.warning(f"No files found in directory: {local_path}")
            return False

        all_success = True

        for file in report_files:
            s3_key = f"{s3_prefix}{file.name}"
            try:
                logger.info(f"Uploading {file} to s3://{self.bucket_name}/{s3_key}")
                self.s3_client.upload_file(str(file), self.bucket_name, s3_key)
                logger.info(f"Successfully uploaded: {file.name}")
            except Exception as e:
                logger.error(f"Failed to upload {file.name}: {e}")
                all_success = False

        return all_success

    def close_s3_client(self):
        """Close the S3 client session."""
        self.s3_client.close()

if __name__ == "__main__":
    try:
        uploader = S3Uploader()
        success = uploader.upload_all_reports_to_s3()
        uploader.close_s3_client()

        if success:
            logger.info("File upload process completed successfully in S3.")
        else:
            logger.error("File upload process failed.")

    except Exception as e:
        logger.error(f"An error occurred during the upload process: {e}")
