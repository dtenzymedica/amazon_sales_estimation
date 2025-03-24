pipeline {
    agent any
    
    environment {
        ENV_FILE = "C:\\Users\\d.tanubudhi\\amazon_sales_estimation\\.env"
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

        stage('Load Environment Variables') {
            steps {
                script {
                    def envVars = readFile(ENV_FILE).trim().split("\n").collect { line ->
                        def keyValue = line.split("=")
                        return keyValue.length == 2 ? "${keyValue[0]}=${keyValue[1].trim()}" : null
                    }.findAll { it != null }  

                    withEnv(envVars) {
                        echo "Environment variables loaded successfully!"
                    }
                }
            }
        }
        stage('Running Pipeline') {
            steps {
                script {
                    echo "Excuting the pipeline"
                    bat "\"%PYTHON_PATH%\" \"C:\\Users\\d.tanubudhi\\amazon_sales_estimation\\uploads\\processor.py\""
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
