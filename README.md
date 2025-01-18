# AWS Lambda Web Scraping with Selenium, ChromeDriver, DynamoDB, SES, and EventBridge

This README documents the **steps** I performed to create a fully automated web-scraping solution using **AWS Lambda**, **Selenium** (with **ChromeDriver**), **DynamoDB**, **SES**, and **EventBridge**. The goal was to run browser-based automation (e.g., scraping) in a serverless environment, handle duplicate records gracefully, send alerts by email, and schedule the entire process periodically.

---

## Table of Contents

1. [Project Scope](#project-scope)  
2. [Initial Lambda Setup (Headless Chrome & Selenium)](#initial-lambda-setup-headless-chrome--selenium)  
3. [Containerizing the Project (Docker + AWS ECR)](#containerizing-the-project-docker--aws-ecr)  
4. [DynamoDB for Deduplication](#dynamodb-for-deduplication)  
5. [Email Notifications via SES](#email-notifications-via-ses)  
6. [Scheduling with EventBridge](#scheduling-with-eventbridge)
7. [Conclusion](#conclusion)

---

## 1. Project Scope

1. **Automate** a web-scraping task in AWS Lambda, using a real browser (Selenium + headless Chrome).  
2. **Avoid** repeated notifications by **deduplicating** results in DynamoDB.  
3. **Email** newly discovered data via **SES**.  
4. **Schedule** the scraping to run at a specific time each day using **EventBridge**.

I initially approached this by testing a simple Lambda function that references Selenium and headless Chrome. As the dependencies grew, I decided to package everything inside a Docker container for cleaner deployment to AWS Lambda.

---

## 2. Containerizing the Project (Docker + AWS ECR)

1. **Created a Dockerfile**  
   - Started from `amazon/aws-lambda-python:3.12`, installing essential libraries (like `libX*`, `alsa-lib`, etc.) for Chrome to function.  
   - Included a `chrome-installer.sh` script that fetched the latest stable Chrome and ChromeDriver from Google’s “chrome-for-testing” JSON.  
   - Installed the libraries from requirements.txt 
   - Finally, I copied the Python script (e.g., `main.py`) and set `CMD ["main.lambda_handler"]` to run under Lambda.

2. **Built Locally**  
   - Used `docker build -t my-selenium-lambda .` to build the image.  

3. **Pushed to AWS ECR**  
   - Tagged the container with my ECR repository name, e.g., `docker tag my-selenium-lambda <account_id>.dkr.ecr.<region>.amazonaws.com/myrepo:v1`.  
   - Authenticated with ECR using the AWS CLI and ran `docker push ...` to upload.

4. **Created a Lambda Function from the Container**  
   - In the AWS Lambda console, I selected “Container image” as the deployment source.  
   - Pointed it to the ECR image tag and set appropriate memory/timeout.  
   - Testing in the console showed that headless Chrome started successfully, and Selenium commands ran smoothly.

---

## 4. DynamoDB for Deduplication
   - Used the AWS console (or CLI) to create a `job_tracker` table with `job_id` as the primary key (string).
   - After the Lambda scraped new items, I invoked `dynamodb.get_item(Key={"job_id": job_id})`.  
   - If **no item** existed, I `put_item` to store it and flagged this result as “new.”  
   - This logic ensures I only process or notify about fresh content.

---

## 5. Email Notifications via SES

- In the Lambda function, after finding “new” records, I used `boto3.client('ses').send_email(...)` to send a **single** consolidated email listing them.
---

## 6. Scheduling with EventBridge

   - Created a rule in **EventBridge** with `cron(0 10 * * ? *)` to run daily at 10:00 AM UTC.  
   - Chose the Lambda function (container-based) as the rule’s target.

---

## 7. Conclusion

Throughout this project, I:

- **Set up a basic Lambda** with headless Chrome and Selenium.  
- **Shifted** to a **Docker container** to handle large binaries.  
- **Added DynamoDB** for deduplication, **SES** for email, and **EventBridge** to schedule daily runs.

This has provided a fully automated, serverless solution for web scraping or browser automation tasks. I can now maintain a single Dockerfile to keep Chrome, ChromeDriver, and Python libraries current, easily push updates to AWS ECR, and rely on Lambda’s auto-scaling and cost-effective model.
