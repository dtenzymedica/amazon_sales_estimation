pipeline {
    agent any

    environment {
        PYTHON_PATH = "C:\\Users\\d.tanubudhi\\amazon_sales_estimation\\venv\\Scripts\\python.exe"
        PROCESSOR = "C:\\Users\\d.tanubudhi\\amazon_sales_estimation\\uploads\\s3-processor.py"
    }

    stages {
        stage('Clone Repository') {
            steps {
                echo "Cloning the repository..."
                git url: 'https://github.com/dtenzymedica/amazon_sales_estimation.git', branch: 'main'
                echo "Repository cloned successfully..."
            }
        }

        stage('Run Main Processor') {
            steps {
                echo "Running processor script..."
                bat "\"%PYTHON_PATH%\" \"%PROCESSOR%\""
            }
        }
    }

    post {
        success {
            echo 'Pipeline executed successfully.'
        }
        failure {
            echo 'Pipeline execution failed. Check logs for details.'
        }
    }
}
