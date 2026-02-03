"""
Torrey Pines Waitlist Automation
Selenium-based form submission
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    # Stealth settings
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Chrome binary for Docker/Linux
    if os.path.exists('/usr/bin/google-chrome'):
        options.binary_location = '/usr/bin/google-chrome'
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_script_timeout(30)
    
    # Remove webdriver flag
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Set geolocation
    try:
        driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "accuracy": 100
        })
        logger.info(f"Geolocation set to: {LATITUDE}, {LONGITUDE}")
    except Exception as e:
        logger.warning(f"Could not set geolocation: {e}")
    
    return driver

