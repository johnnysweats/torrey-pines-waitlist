"""
Torrey Pines Waitlist Automation
Selenium-based form submission
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime
import time
import logging
import traceback
import os

logger = logging.getLogger(__name__)

# Torrey Pines / La Jolla coordinates
LATITUDE = 32.8986
LONGITUDE = -117.2431

# Waitwhile URLs
WELCOME_URL = "https://waitwhile.com/locations/torreypinesgolf/welcome"
FORM_URL = "https://waitwhile.com/locations/torreypinesgolf/details?registration=waitlist"

# Course name mapping (form value -> website display value)
COURSE_MAP = {
    "North": "North",
    "South": "South",
    "1st Available": "First Avail.",
    "First Avail.": "First Avail."
}


def create_driver(headless=True):
    """Create and configure Chrome WebDriver"""
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
    
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS
