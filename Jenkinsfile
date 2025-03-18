pipeline {
    agent any
    
    environment {
        PYTHON_PATH = "C:\\Users\\d.tanubudhi\\amazon_sales_estimation\\venv\\Scripts\\python.exe"
    }
    
    stages {
        stage('Clone Repository') {
            steps {
                echo "Cloning the repository..."
                git url: 'https://github.com/dtenzymedica/amazon_sales_estimation.git', branch: 'main'
                echo "Repository cloned successfully..."
            }
        }
        
        stage('Getting reports') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    script {
                        echo "Downloading reports from Amazon Seller Central..."
                        bat "\"%PYTHON_PATH%\" \"C:\\Users\\d.tanubudhi\\amazon_sales_estimation\\scraper\\business-report-download.py\""
                    }
                }
            }
        }
        
        stage('Data Cleaning') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    script {
                        echo "Cleaning data after downloading reports..."
                        bat "\"%PYTHON_PATH%\" \"C:\\Users\\d.tanubudhi\\amazon_sales_estimation\\scraper\\data-cleaning.py\""
                    }
                }
            }
        }
        
        stage('S3 Uploads') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    script {
                        echo "Uploading output reports to S3..."
                        bat "\"%PYTHON_PATH%\" \"C:\\Users\\d.tanubudhi\\amazon_sales_estimation\\uploads\\s3-uploads.py\""
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo 'Pipeline executed successfully. Files uploaded to AWS S3 bucket (amazon_sales_estimation).'
        }
        failure {
            echo 'Pipeline execution failed. Please check the logs for details.'
        }
    }
}
