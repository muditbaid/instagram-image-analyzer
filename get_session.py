"""
One-Button Session ID Getter

Run this, it opens Chrome, saves session ID automatically.
"""

import time
import re
from pathlib import Path
import os

def get_session():
    print("=" * 50)
    print("INSTAGRAM SESSION GETTER")
    print("=" * 50)
    print()
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        print("Installing required packages...")
        os.system("pip install selenium webdriver-manager")
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
    
    print("Setting up Chrome...")
    
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1200,800")
    
    # Use a clean temporary profile
    temp_dir = os.path.join(os.getenv("TEMP"), "chrome_session_temp")
    options.add_argument(f"--user-data-dir={temp_dir}")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"Error: {e}")
        print("\nTrying without user data dir...")
        options2 = Options()
        options2.add_argument("--disable-blink-features=AutomationControlled")
        options2.add_argument("--no-sandbox")
        options2.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options2)
    
    try:
        print("Opening Instagram...")
        driver.get("https://www.instagram.com")
        
        print()
        print("-" * 50)
        print("INSTRUCTIONS:")
        print("-" * 50)
        print("1. Wait for Instagram to load")
        print("2. If it asks you to LOG IN -> do that now!")
        print("3. Wait for your feed to appear")
        print("4. Come back here and press ENTER")
        print("-" * 50)
        print()
        input("Press ENTER after Instagram is loaded: ")
        
        print("Getting session ID...")
        time.sleep(2)
        
        cookies = driver.get_cookies()
        session_id = None
        for cookie in cookies:
            if cookie['name'] == 'sessionid' and cookie['value']:
                session_id = cookie['value']
                break
        
        if session_id:
            print("\n" + "=" * 50)
            print("SUCCESS!")
            print("=" * 50)
            
            # Save to .env
            env_path = Path(".env")
            existing = ""
            if env_path.exists():
                existing = env_path.read_text()
            
            if "INSTAGRAM_SESSIONID=" in existing:
                existing = re.sub(r'INSTAGRAM_SESSIONID=.*', f'INSTAGRAM_SESSIONID={session_id}', existing)
            else:
                existing += f"\nINSTAGRAM_SESSIONID={session_id}\n"
            
            env_path.write_text(existing.strip() + "\n")
            print("Session ID saved to .env file!")
            print("Close Chrome and you're done!")
        else:
            print("\nERROR: Session not found")
            print("Make sure you're logged in to Instagram")
            print("Cookies found:", [c['name'] for c in cookies])
        
        input("\nPress ENTER to close Chrome...")
        
    finally:
        driver.quit()
        # Clean up temp directory
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass

if __name__ == "__main__":
    get_session()
