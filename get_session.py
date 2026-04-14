"""
ONE-BUTTON Session ID Getter!

This script:
1. Opens Chrome
2. Goes to Instagram
3. Waits for you to log in (if needed)
4. Automatically copies your session ID
5. Saves it for you

Just press one button!
"""

import time
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import streamlit as st
import re


def get_session_automatic():
    """Opens Chrome, waits for login, extracts session ID automatically."""
    
    st.info("🔄 Opening Chrome... Please wait...")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--user-data-dir=chrome-session-temp")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-popup-blocking")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        return None, f"Could not open Chrome: {e}"
    
    try:
        st.info("🌐 Navigating to Instagram...")
        driver.get("https://www.instagram.com")
        
        # Wait for page to load
        time.sleep(2)
        
        st.info("""
        ⏳ **Please log in to Instagram if needed!**
        
        The browser will wait for you. Once you're logged in, come back here and click the button below.
        """)
        
        # Show current URL
        current_url = driver.current_url
        st.text(f"Current URL: {current_url}")
        
        return driver, "Browser opened. Log in to Instagram, then click the button below."
        
    except Exception as e:
        return None, f"Error: {e}"


def extract_session_id(driver):
    """Extract sessionid cookie from the browser."""
    try:
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie['name'] == 'sessionid' and cookie['value']:
                return cookie['value']
        
        # Try to refresh and check again
        driver.refresh()
        time.sleep(2)
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie['name'] == 'sessionid' and cookie['value']:
                return cookie['value']
                
        return None
    except Exception as e:
        return None


def save_session(session_id):
    """Save session ID to .env file."""
    env_path = Path(".env")
    existing = ""
    if env_path.exists():
        existing = env_path.read_text()
    
    if "INSTAGRAM_SESSIONID=" in existing:
        existing = re.sub(r'INSTAGRAM_SESSIONID=.*', f'INSTAGRAM_SESSIONID={session_id}', existing)
    else:
        existing += f"\nINSTAGRAM_SESSIONID={session_id}\n"
    
    env_path.write_text(existing.strip() + "\n")


def main():
    st.title("🔑 Get Instagram Session ID")
    st.markdown("*The easy one-button way!*")
    
    st.markdown("---")
    st.markdown("""
    ### How this works:
    
    1. Click the button below
    2. A Chrome window will open
    3. Log in to Instagram (if not already logged in)
    4. Come back here and click "Get Session ID"
    5. Done! Your session is saved automatically.
    
    ---
    """)
    
    if 'driver' not in st.session_state:
        st.session_state.driver = None
        st.session_state.status = "not_started"
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Open Chrome & Start", type="primary", use_container_width=True):
            driver, msg = get_session_automatic()
            if driver:
                st.session_state.driver = driver
                st.session_state.status = "waiting"
                st.rerun()
            else:
                st.error(msg)
    
    with col2:
        if st.button("🔑 Get Session ID", type="primary", use_container_width=True, disabled=(st.session_state.driver is None)):
            if st.session_state.driver:
                driver = st.session_state.driver
                
                st.info("Extracting session ID...")
                
                session_id = extract_session_id(driver)
                
                if session_id:
                    save_session(session_id)
                    st.success(f"✅ Session ID saved!")
                    st.balloons()
                    
                    # Close browser
                    try:
                        driver.quit()
                    except:
                        pass
                    st.session_state.driver = None
                    st.session_state.status = "done"
                    
                    st.markdown("""
                    ---
                    🎉 **You're all set!**
                    
                    Close this window and go to the Download Images page.
                    Your downloads will now work reliably!
                    """)
                else:
                    st.warning("""
                    Could not find session ID. Make sure you're:
                    1. Logged into Instagram
                    2. On the Instagram page in Chrome
                    
                    Try clicking "Get Session ID" again after confirming you're logged in.
                    """)
    
    if st.session_state.status == "waiting":
        st.markdown("""
        ---
        ✅ Chrome is open!
        
        1. Check the Chrome window
        2. Log in to Instagram if prompted
        3. Click **"🔑 Get Session ID"** button above
        """)
    
    if st.button("❌ Close Browser", disabled=(st.session_state.driver is None)):
        if st.session_state.driver:
            try:
                st.session_state.driver.quit()
            except:
                pass
        st.session_state.driver = None
        st.session_state.status = "not_started"
        st.rerun()


if __name__ == "__main__":
    main()
