import os
import time
from datetime import date

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service
from tempfile import mkdtemp
import boto3


def lambda_handler(event, context):
    url = "https://github.com/SimplifyJobs/New-Grad-Positions"

    options = Options()
    options.add_argument("--headless=new")  # no GUI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument("--single-process")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-pipe")
    options.add_argument("--verbose")
    options.add_argument("--log-path=/tmp")
    options.binary_location = "/opt/chrome/chrome-linux64/chrome"

    service = Service(
        executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
        service_log_path="/tmp/chromedriver.log"
    )

    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(5)  # wait a few seconds for JS to load jobs; adjust as needed

    # Get final rendered HTML from Selenium
    page_source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_source, "lxml")

    table = soup.find("table", {"tabindex": "0"})
    if table:
        tbody = table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr") # find the README's container

            jobs = []
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 5:
                    company = cells[0].get_text(strip=True)
                    position = cells[1].get_text(strip=True)
                    if "data engineer" not in position.lower():
                        continue
                    location = cells[2].get_text(strip=True)

                    # Usually the 4th cell is an <a> tag with href
                    link_tag = cells[3].find("a", href=True)
                    link = link_tag["href"] if link_tag else ""

                    date = cells[4].get_text(strip=True)
                    job_id = f"{company}-{position}-{date}"
                    jobs.append({
                        "job_id": job_id,
                        "company": company,
                        "position": position,
                        "location": location,
                        "link": link,
                        "date": date
                    })

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table("job_tracker")  # Or read from env var

    new_jobs = []
    for job in jobs:
        response = table.get_item(Key={"job_id": job["job_id"]})
        if "Item" not in response:  # This means it's new
            table.put_item(Item=job)
            new_jobs.append(job)

    send_email_notification(new_jobs)
    # Return only the truly new ones
    return new_jobs

def send_email_notification(new_jobs):
    if not new_jobs:
        return
    ses_client = boto3.client('ses')
    sender = os.environ["SES_SENDER"]       # "verified-sender@example.com"
    recipient = os.environ["SES_RECIPIENT"] # "your-email@example.com"

    today_str = date.today().strftime('%Y-%m-%d')
    subject = f"New Data Engineer Jobs - {today_str}"

    # Build the email body with all the new jobs listed
    body_text = f"Hi,\n\nWe found {len(new_jobs)} new Data Engineer job(s) today:\n\n"
    for idx, job in enumerate(new_jobs, start=1):
        body_text += (
            f"Job #{idx}\n"
            f"Company: {job['company']}\n"
            f"Position: {job['position']}\n"
            f"Location: {job['location']}\n"
            f"Date: {job['date']}\n"
            f"Link: {job['link']}\n"
            "----------------------\n"
        )
    body_text += "\nRegards,\nYour Job Scraper"

    ses_client.send_email(
        Source=sender,
        Destination={"ToAddresses": [recipient]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body_text}}
        }
    )

# if __name__ == "__main__":
#     results = scrape_github_readme()
#     for job in results:
#         print(job)
