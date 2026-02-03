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

LATITUDE = 32.8986
LONGITUDE = -117.2431

WELCOME_URL = "https://waitwhile.com/locations/torreypinesgolf/welcome"
FORM_URL = "https://waitwhile.com/locations/torreypinesgolf/details?registration=waitlist"

COURSE_MAP = {
    "North": "North",
    "South": "South",
    "1st Available": "First Avail.",
    "First Avail.": "First Avail."
}


def create_driver(headless=True):
    options = Options()
    
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-default-apps")
    options.add_argument("--no-first-run")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    if os.path.exists('/usr/bin/google-chrome'):
        options.binary_location = '/usr/bin/google-chrome'
    
    service = Service('/usr/local/bin/chromedriver')
    service.log_path = '/tmp/chromedriver.log'
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_script_timeout(30)
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
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


def wait_for_element(driver, by, value, timeout=10, clickable=False):
    wait = WebDriverWait(driver, timeout)
    if clickable:
        return wait.until(EC.element_to_be_clickable((by, value)))
    return wait.until(EC.presence_of_element_located((by, value)))


def click_element(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.2)
    driver.execute_script("arguments[0].click();", element)


def fill_input(driver, element_id, value):
    element = wait_for_element(driver, By.ID, element_id, timeout=5)
    element.clear()
    element.send_keys(value)
    logger.info(f"Filled {element_id}: {value}")


def select_dropdown(driver, input_id, option_text):
    input_elem = wait_for_element(driver, By.ID, input_id, timeout=5, clickable=True)
    click_element(driver, input_elem)
    time.sleep(0.3)
    
    option_xpath = f"//div[contains(@class, 'option') and text()='{option_text}']"
    option = wait_for_element(driver, By.XPATH, option_xpath, timeout=5, clickable=True)
    click_element(driver, option)
    time.sleep(0.3)
    
    logger.info(f"Selected dropdown option: {option_text}")


def wait_for_join_button(driver, max_attempts=120, refresh_interval=2):
    logger.info("Waiting for 'Join waitlist' button...")
    
    for attempt in range(max_attempts):
        try:
            button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'wwpp-primary-button')]"))
            )
            logger.info(f"'Join waitlist' button found after {attempt + 1} attempts")
            return button
        except:
            timestamp = datetime.now().strftime('%H:%M:%S')
            logger.info(f"[{timestamp}] Button not ready, refreshing... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(refresh_interval)
            driver.refresh()
    
    raise Exception(f"'Join waitlist' button not available after {max_attempts} attempts")


def check_submission_result(driver, timeout=15):
    start = time.time()
    original_url = driver.current_url
    
    while time.time() - start < timeout:
        current_url = driver.current_url
        page_text = driver.page_source.lower()
        
        if any([
            "you're on the list" in page_text,
            "you are on the list" in page_text,
            "confirmation" in current_url,
            "/status" in current_url,
            "position" in page_text and "line" in page_text,
        ]):
            return True, f"Successfully joined waitlist! URL: {current_url}"
        
        if current_url != original_url and "registration=waitlist" not in current_url:
            return True, f"Form submitted, redirected to: {current_url}"
        
        if "error" in page_text and "try again" in page_text:
            return False, "Submission error detected on page"
        
        time.sleep(0.5)
    
    if "registration=waitlist" in driver.current_url:
        return False, "Form did not submit - still on registration page"
    
    return True, f"Submission completed. Final URL: {driver.current_url}"


def run_waitlist_automation(first_name, last_name, email, phone, course, players, headless=True):
    logger.info("=" * 50)
    logger.info("TORREY PINES WAITLIST AUTOMATION")
    logger.info("=" * 50)
    logger.info(f"Name: {first_name} {last_name}")
    logger.info(f"Email: {email}")
    logger.info(f"Phone: {phone}")
    logger.info(f"Course: {course}")
    logger.info(f"Players: {players}")
    logger.info("=" * 50)
    
    driver = None
    
    try:
        logger.info("[1/6] Starting browser...")
        driver = create_driver(headless=headless)
        logger.info("Browser started")
        
        logger.info("[2/6] Navigating to Torrey Pines waitlist...")
        driver.get(WELCOME_URL)
        wait_for_element(driver, By.TAG_NAME, "body", timeout=10)
        logger.info(f"Page loaded: {driver.current_url}")
        
        logger.info("[3/6] Waiting for waitlist to open...")
        join_button = wait_for_join_button(driver, max_attempts=120, refresh_interval=2)
        click_element(driver, join_button)
        logger.info("Clicked 'Join waitlist' button")
        time.sleep(1)
        
        logger.info("[4/6] Filling out form...")
        fill_input(driver, "form_firstName", first_name)
        fill_input(driver, "form_lastName", last_name)
        fill_input(driver, "form_email", email)
        fill_input(driver, "form_phone", phone)
        logger.info("Form fields filled")
        
        logger.info("[5/6] Selecting course and players...")
        website_course = COURSE_MAP.get(course, course)
        select_dropdown(driver, "react-select-2-input", website_course)
        select_dropdown(driver, "react-select-3-input", str(players))
        logger.info("Dropdowns selected")
        
        logger.info("[6/6] Submitting form...")
        
        submit_button = wait_for_element(
            driver, 
            By.CSS_SELECTOR, 
            "button[data-cy='form-button']", 
            timeout=5,
            clickable=True
        )
        
        if submit_button.get_attribute("disabled"):
            return {
                'status': 'error',
                'message': 'Submit button is disabled - waitlist may be closed'
            }
        
        pre_submit_url = driver.current_url
        click_element(driver, submit_button)
        logger.info("Clicked submit button")
        
        time.sleep(2)
        
        success, message = check_submission_result(driver, timeout=15)
        
        if success:
            logger.info(f"SUCCESS: {message}")
            return {'status': 'success', 'message': message}
        else:
            try:
                debug_path = f"/tmp/debug_{int(time.time())}.png"
                driver.save_screenshot(debug_path)
                logger.error(f"Debug screenshot saved: {debug_path}")
            except:
                pass
            
            logger.error(f"FAILED: {message}")
            return {'status': 'error', 'message': message}
    
    except Exception as e:
        error_msg = f"Automation error: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        if driver:
            try:
                debug_path = f"/tmp/error_{int(time.time())}.png"
                driver.save_screenshot(debug_path)
                logger.error(f"Error screenshot saved: {debug_path}")
            except:
                pass
        
        return {'status': 'error', 'message': error_msg}
    
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Browser closed")
            except:
                pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    result = run_waitlist_automation(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        phone="555-123-4567",
        course="North",
        players="2",
        headless=False
    )
    
    print("\n" + "=" * 50)
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print("=" * 50)
