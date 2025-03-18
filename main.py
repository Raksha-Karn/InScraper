import json
import time
import os
import re
import schedule
import random
from supabase_client import supabase
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rotate_agents import rotate_user_agents
from selenium.webdriver.common.action_chains import ActionChains
from scraper import *
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

WEBSITE = "https://np.linkedin.com"
DRIVER_PATH = '/home/raksha/Downloads/chromedriver-linux64/chromedriver'
MAX_JOBS_TO_SCRAPE = 40
MAX_TOTAL_JOBS = 500

JOB_QUERIES = [
    "Python Developer",
    "Data Scientist",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "DevOps Engineer",
    "Machine Learning Engineer",
    "Software Engineer",
    "Data Analyst",
    "UI/UX Designer"
]

used_queries = []

def setup_driver():
    load_dotenv()
    chrome_options = Options()
    user_agent = rotate_user_agents()
    chrome_options.add_argument(f'user-agent={user_agent}')
    
    service = Service(DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver, ActionChains(driver)

def login_to_linkedin(driver, actions):
    try:
        driver.set_page_load_timeout(30)
        driver.get(WEBSITE)
        time.sleep(2)
        logging.info("Loaded page successfully.")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//a[contains(text(), "Sign in with email")]'))
        )
        sign_in_button = driver.find_element(By.XPATH, '//a[contains(text(), "Sign in with email")]')
        sign_in_button.click()
        actions.move_by_offset(100, 0).perform()
        time.sleep(1)
        
        email_input = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Email or phone"]')
        email_input.click()
        email_input.send_keys(os.getenv('EMAIL'))
        
        password_input = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Password"]')
        actions.move_by_offset(-100, 0).perform()
        password_input.click()
        password_input.send_keys(os.getenv('PASSWORD'))
        
        login_button = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Sign in"]')
        login_button.click()
        logging.info("Logged in successfully.")
        
        time.sleep(5)
        return True
    except Exception as e:
        logging.error(f"Login failed: {str(e)}")
        return False

def get_next_job_query():
    global used_queries
    
    if len(used_queries) >= len(JOB_QUERIES):
        used_queries = []
    
    available_queries = [q for q in JOB_QUERIES if q not in used_queries]
    
    if not available_queries:
        next_query = random.choice(JOB_QUERIES)
    else:
        next_query = random.choice(available_queries)
    
    used_queries.append(next_query)
    
    logging.info(f"Selected job query: {next_query}")
    return next_query

def search_for_jobs(driver, actions, query=None):
    if query is None:
        query = get_next_job_query()
        
    try:
        actions.move_by_offset(180, 23).perform()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div#global-nav-search'))
        )
        
        search_button = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Click to start a search"]')
        search_button.click()
        
        search_input = driver.find_element(By.CSS_SELECTOR, 'div#global-nav-search')
        search_input.click()
        time.sleep(2)
        
        search_input_element = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Search"]')
        search_input_element.click()
        search_input_element.send_keys(query)
        search_input_element.send_keys(Keys.RETURN)
        logging.info(f"Searching for '{query}'...")
        
        time.sleep(5)
        return True
    except Exception as e:
        logging.error(f"Search failed: {str(e)}")
        return False

def apply_easy_apply_filter(driver, actions):
    try:
        actions.move_by_offset(0, 100).perform()
        actions.move_by_offset(54, 117).perform()
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="f_AL=true"]'))
        )
        
        easy_apply_filter = driver.find_element(By.CSS_SELECTOR, 'a[href*="f_AL=true"]')
        easy_apply_filter.click()
        logging.info("Applied 'Easy Apply' filter.")
        
        time.sleep(5)
        return True
    except Exception as e:
        logging.error(f"Failed to apply filter: {str(e)}")
        return False


def collect_job_links(driver, num_pages=3):
    links = []

    try:
        logging.info("Collecting job links...")
        page = 1

        while page <= num_pages and len(links) < MAX_JOBS_TO_SCRAPE:
            logging.info(f"Processing page {page}...")

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'ul.zslYMAghXImmwmPOfcwBWohNqjlUItimevY'))
                )
                
            except Exception as e:
                logging.error(f"The selector for jobs container has been changed. Please update the selector in the code to run the scraper.")
                return []

            jobs_container = driver.find_element(By.CSS_SELECTOR, 'ul.zslYMAghXImmwmPOfcwBWohNqjlUItimevY')

            last_height = driver.execute_script("return arguments[0].scrollHeight", jobs_container)
            while True:
                driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", jobs_container)
                time.sleep(2)

                new_height = driver.execute_script("return arguments[0].scrollHeight", jobs_container)
                if new_height == last_height:
                    break
                last_height = new_height

            job_cards = driver.find_elements(By.CSS_SELECTOR, 'div.job-card-container')
            page_links = []

            for card in job_cards:
                try:
                    job_link = card.find_element(By.CSS_SELECTOR, 'a.job-card-container__link')
                    job_url = job_link.get_attribute('href')
                    if job_url and job_url not in links:
                        logging.info(f"Found new job link: {job_url}")
                        page_links.append(job_url)
                except Exception as e:
                    logging.error(f"Error extracting job link: {str(e)}")

            logging.info(f"Found {len(page_links)} new jobs on page {page}")
            links.extend(page_links)

            logging.info("Checking if we have enough links...")
            if len(links) >= MAX_JOBS_TO_SCRAPE:
                return links[:MAX_JOBS_TO_SCRAPE]

            logging.info("Checking if we need to go to the next page...")
            if page < num_pages:
                logging.info("Going to the next page...")
                try:
                    next_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, f'//button[contains(@aria-label, "Page {page + 1}")]'))
                    )
                    driver.execute_script("arguments[0].scrollIntoView();", next_button)
                    next_button.click()
                    logging.info(f"Navigating to page {page + 1}")
                    time.sleep(3)
                    page += 1
                except Exception as e:
                    logging.error(f"Error navigating to next page: {e}")
                    break
            else:
                break

        logging.info(f"Collected a total of {len(links)} job links")
        return links[:MAX_JOBS_TO_SCRAPE]
    except Exception as e:
        logging.error(f"Error collecting job links: {str(e)}")
        return links[:MAX_JOBS_TO_SCRAPE]

def extract_job_details(driver, job_url):
    try:
        driver.get(job_url)
        time.sleep(2)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.jobs-details h1'))
        )
        
        job_title_elem = driver.find_element(By.CSS_SELECTOR, 'div.jobs-details h1')
        job_title = job_title_elem.text if job_title_elem else "N/A"
        
        job_meta_div = driver.find_element(By.CSS_SELECTOR, 'div#job-details')
        desc = "\n".join([para.text.strip() for para in job_meta_div.find_elements(By.TAG_NAME, 'p')])
        
        top_container = driver.find_elements(By.CSS_SELECTOR,
                                           'div.job-details-jobs-unified-top-card__tertiary-description-container span')
        location = top_container[0].text if len(top_container) > 0 else "N/A"
        posted_date = top_container[4].text if len(top_container) > 4 else "N/A"
        
        job_details_container = driver.find_elements(By.CSS_SELECTOR, "div.job-details-preferences-and-skills__pill")
        
        salary = None
        job_type = None
        job_time = None

        salary_pattern = re.compile(
            r"[\$\€\£\₹\¥]\s?\d+[KMB]?(?:/\w+)?\s?-\s?[\$\€\£\₹\¥]?\d+[KMB]?(?:/\w+)?|\d+\s?(per\s?(hour|year|month|week))",
            re.IGNORECASE
        )

        for detail in job_details_container:
            text = detail.text.strip()
            match = salary_pattern.search(text)
            if match:
                salary = match.group(0)
                salary = salary.replace("\u20b9", "₹").replace(" - ", "-").strip() if salary else "N/A"
            elif "On-site" in text or "Remote" in text or "Hybrid" in text:
                job_type = text.split('\n')[0]
                if job_type:
                    job_type = job_type
                else:
                    job_type = "N/A"
            elif "Full-time" in text or "Part-time" in text or "Contract" in text or "Internship" or "Temporary" in text:
                job_time = text.split('\n')[0]
                if job_time:
                    job_time = job_time
                else:
                    job_time = "N/A"
        
        company_url = driver.find_element(By.CSS_SELECTOR,
                                        'div.job-details-jobs-unified-top-card__company-name a').get_attribute('href')
        company_title_element = driver.find_element(By.CSS_SELECTOR,
                                                  'div.job-details-jobs-unified-top-card__company-name a')
        company_title = company_title_element.text.strip() if company_title_element else "N/A"

        company_logo_url = driver.find_element(By.CSS_SELECTOR, 'div.p5 img').get_attribute('src')
        if not company_logo_url:
            company_logo_url = None
        
        logging.info(f"Extracted details for job: {job_title}")
        return {
            "title": job_title,
            "description": desc,
            "url": job_url,
            "salary": salary,
            "job_type": job_type,
            "job_time": job_time,
            "posted_date": posted_date,
            "location": location,
            "company_url": company_url,
            "company_title": company_title,
            "company_logo_url": company_logo_url
        }
    except Exception as e:
        logging.error(f"Error extracting job details: {str(e)}")
        return None

def save_jobs_to_file(job_list, filename='jobs.json'):
    try:
        with open(filename, 'w') as f:
            json.dump(job_list, f, indent=4)
        logging.info(f"Saved job list to {filename}")
        return True
    except Exception as e:
        logging.error(f"Error saving jobs to file: {str(e)}")
        return False

def save_jobs_to_supabase(job_list):
    try:
        if not job_list:
            logging.warning("No jobs to save to Supabase")
            return False
        
        response = supabase.table("raw_jobs_data").select("id", count="exact").execute()
        current_count = response.count if hasattr(response, 'count') else 0
        
        logging.info(f"Current jobs in database: {current_count}")
        
        available_slots = MAX_TOTAL_JOBS - current_count
        
        if available_slots <= 0:
            logging.warning(f"Database at capacity ({current_count}/{MAX_TOTAL_JOBS}). Removing oldest jobs.")
            
            to_delete = current_count - MAX_TOTAL_JOBS + len(job_list)
            if to_delete > 0:
                oldest_jobs = supabase.table("raw_jobs_data").select("id").order("created_at").limit(to_delete).execute()
                
                if hasattr(oldest_jobs, 'data') and oldest_jobs.data:
                    ids_to_delete = [job['id'] for job in oldest_jobs.data]
                    
                    supabase.table("raw_jobs_data").delete().in_("id", ids_to_delete).execute()
                    logging.info(f"Deleted {len(ids_to_delete)} oldest jobs")
        
        jobs_to_insert = job_list[:available_slots] if available_slots < len(job_list) else job_list
        if jobs_to_insert:
            existing_urls = []
            for job in jobs_to_insert:
                url_response = supabase.table("raw_jobs_data").select("id").eq("url", job["url"]).execute()
                if hasattr(url_response, 'data') and url_response.data:
                    existing_urls.append(job["url"])
            
            new_jobs = [job for job in jobs_to_insert if job["url"] not in existing_urls]
            
            if new_jobs:
                response = supabase.table("raw_jobs_data").insert(new_jobs).execute()
                logging.info(f"Saved {len(new_jobs)} new jobs to Supabase")
            else:
                logging.info("All jobs already exist in the database")
        
        return True
    except Exception as e:
        logging.error(f"Error saving to Supabase: {str(e)}")
        return False

def get_jobs():
    driver, actions = setup_driver()
    job_list = []
    
    try:
        if not login_to_linkedin(driver, actions):
            return []
        
        job_query = get_next_job_query()
        if not search_for_jobs(driver, actions, query=job_query):
            return []
        
        if not apply_easy_apply_filter(driver, actions):
            return []
        
        links = collect_job_links(driver, num_pages=3)
        logging.info(f"Collected {len(links)} job links to process")
        
        for index, job_url in enumerate(links):
            logging.info(f"Processing job {index + 1}/{len(links)}: {job_url}")
            job_details = extract_job_details(driver, job_url)
            
            if job_details:
                job_list.append(job_details)
                logging.info(f"Successfully extracted details for job {index + 1}")
            
            time.sleep(2)
        
        save_jobs_to_file(job_list)
        save_jobs_to_supabase(job_list)
        
        return job_list
        
    except Exception as e:
        logging.error(f"Error in job scraping process: {str(e)}")
        return []
    finally:
        driver.quit()
        logging.info("WebDriver closed")
        return job_list

def run_scheduled_job():
    logging.info(f"Starting scheduled job at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    get_jobs()
    logging.info(f"Completed scheduled job at {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    run_scheduled_job()
    
    schedule.every(30).minutes.do(run_scheduled_job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)