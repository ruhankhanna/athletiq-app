# athletic_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
from webdriver_manager.chrome import ChromeDriverManager
from decouple import config
import tempfile
import shutil

_temp_dir = None  # global so you can clean it up

def get_driver():
    print("[SCRAPER DEBUG] Launching Chrome driver")

    global _temp_dir
    _temp_dir = tempfile.mkdtemp()

    print(f"[SCRAPER DEBUG] Using temp profile directory: {_temp_dir}")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=0")
    options.add_argument(f"--user-data-dir={_temp_dir}")

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)



# Credentials for athletic.net
EMAIL = config("SCRAPER_EMAIL")
PASSWORD = config("SCRAPER_PASSWORD")

# Set up Selenium Chrome Driver
driver = None

logged_in = False

def login_athletic_net():
    global logged_in, driver

    if logged_in:
        return
    

    driver = get_driver()
    driver.get("https://www.athletic.net/account/login")
    time.sleep(3)


    email_input = driver.find_element(By.XPATH, "//input[@placeholder='Enter Email']")
    email_input.clear()
    email_input.send_keys(EMAIL)

    password_input = driver.find_element(By.XPATH, "//input[@placeholder='Enter Password']")
    password_input.clear()
    password_input.send_keys(PASSWORD)

    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")
    # Try clicking login button
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
        time.sleep(1)
        login_button.click()
    except Exception:
        print("[SCRAPER WARNING] Login button click intercepted, retrying with JS")
        driver.execute_script("arguments[0].click();", login_button)


    time.sleep(3)

    if "login" in driver.current_url.lower():
        raise Exception("Login failed – check credentials")

    logged_in = True


def scrape_filtered_results(profile_url, expected_first, expected_last):
    """
    Returns a list of tuples:
      ( event_name, time_str, date_str, meet_name, place_str )
    """
    login_athletic_net()

    driver.get(profile_url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 3) Grab the athlete’s name anchor
    name_anchor = soup.select_one("a.me-2.text-sport")
    if not name_anchor:
        raise Exception("Could not find athlete name on profile page")
    scraped_name = name_anchor.get_text(strip=True).lower()
    form_name = f"{expected_first} {expected_last}".strip().lower()

    # 4) Validate
    if form_name not in scraped_name:
        raise Exception(
            f"Name mismatch: profile shows “{scraped_name}” but form submitted “{form_name}”"
        )


    results = []

    # find each event block
    tbodies = soup.select("shared-athlete-bio-result-table-tf tbody")

    for tbody in tbodies:
        # event header, e.g. "100 Meters"
        event_name_tag = tbody.find("h5")
        event_name = event_name_tag.text.strip() if event_name_tag else "Unknown Event"

        # skip the header row
        rows = tbody.find_all("tr")[1:]

        for row in rows:
            cols = row.find_all("td")
            # we expect at least: [place, meet, time, date, …]
            if len(cols) < 4:
                continue

            # 1) finishing place (e.g. "1st", "2nd")
            place_text = cols[0].text.strip()

            # 2) meet name
            # 2) meet name (should be in td[4])
            meet_link = cols[4].find("a")
            meet_name = meet_link.text.strip() if meet_link else cols[4].text.strip()


            # 3) time string
            time_tag = cols[2].find("a")
            time_text = time_tag.text.strip() if time_tag else cols[2].text.strip()

            # 4) date string
            date_text = cols[3].text.strip()

            results.append((event_name, time_text, date_text, meet_name, place_text))

    return results


def close_driver():
    global driver, _temp_dir
    if driver:
        driver.quit()
        driver = None
    if _temp_dir:
        shutil.rmtree(_temp_dir, ignore_errors=True)
        _temp_dir = None





__all__ = [
    "driver",
    "login_athletic_net",
    "scrape_filtered_results",
    "close_driver",
]






