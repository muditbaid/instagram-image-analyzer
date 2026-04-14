"""
Instagram Session ID Getter - PROPER VERSION

Uses a fresh Chrome profile - user logs in once, session is saved.
"""

import time
import re
import os
import sys
from pathlib import Path


def main():
    print("=" * 60)
    print("INSTAGRAM SESSION ID GETTER")
    print("=" * 60)
    print()
    print("This will open Chrome and save your Instagram session.")
    print("You'll need to log in ONE TIME only.")
    print()
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        print("Installing required packages...")
        os.system("pip install selenium webdriver-manager")
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    
    # Create fresh temp profile
    temp_profile = os.path.join(os.getenv("TEMP"), "chrome_insta_session")
    
    # Remove old profile if exists
    if os.path.exists(temp_profile):
        import shutil
        shutil.rmtree(temp_profile)
    
    print("Starting Chrome...")
    
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-data-dir={temp_profile}")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    print("Opening Instagram...")
    driver.get("https://www.instagram.com")
    
    print()
    print("-" * 60)
    print("INSTRUCTIONS:")
    print("-" * 60)
    print("1. Look at the Chrome window that opened")
    print("2. LOG IN to Instagram if not already logged in")
    print("3. Wait for your Instagram feed to appear")
    print("4. Come back here and press ENTER")
    print("-" * 60)
    print()
    input("Press ENTER after Instagram is loaded and you're logged in: ")
    
    print()
    print("Getting session ID...")
    time.sleep(2)
    
    # Get cookies
    cookies = driver.get_cookies()
    session_id = None
    
    for cookie in cookies:
        if cookie['name'] == 'sessionid' and cookie['value']:
            session_id = cookie['value']
            break
    
    driver.quit()
    
    # Save session
    if session_id and len(session_id) > 10:
        env_path = Path(".env")
        existing = ""
        if env_path.exists():
            existing = env_path.read_text()
        
        if "INSTAGRAM_SESSIONID=" in existing:
            existing = re.sub(r'INSTAGRAM_SESSIONID=.*', f'INSTAGRAM_SESSIONID={session_id}', existing)
        else:
            existing += f"\nINSTAGRAM_SESSIONID={session_id}\n"
        
        env_path.write_text(existing.strip() + "\n")
        
        print()
        print("=" * 60)
        print("SUCCESS! Session ID saved to .env file!")
        print("=" * 60)
        print()
        print("You can close Chrome now.")
        print()
        print("Next time you run this, it will remember your login!")
    else:
        print()
        print("ERROR: Could not find session ID")
        print("Make sure you logged into Instagram")
        print()
        print("Try running this script again.")


if __name__ == "__main__":
    main()
