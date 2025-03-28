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

                    envVars.each {
                        def parts = it.split("=")
                        env[parts[0]] = parts[1]
                    }

                    echo "Environment variables set for pipeline and subprocesses."
                }
            }
        }

        stage('Run Main Processor') {
            steps {
                script {
                    echo "Executing the processor pipeline script..."
                    bat "\"%PYTHON_PATH%\" \"C:\\Users\\d.tanubudhi\\amazon_sales_estimation\\uploads\\s3-processor.py\""
                }
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
