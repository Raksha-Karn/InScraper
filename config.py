import os
import logging
from dotenv import load_dotenv

load_dotenv()

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

EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD') 