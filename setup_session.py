"""
Get your Instagram Session ID - The EASY way!

Run this, and it opens Chrome directly to the right spot.
"""

import webbrowser
from pathlib import Path


def main():
    print("=" * 60)
    print("  INSTAGRAM SESSION ID SETUP (SUPER EASY)")
    print("=" * 60)
    print()
    print("STEP 1: Click the button that opens Chrome")
    print()
    print("STEP 2: In Chrome, go to: https://www.instagram.com")
    print("        (Make sure you're logged in!)")
    print()
    print("STEP 3: Come back here and press ENTER when done")
    print()
    
    input("Press ENTER to open Chrome...")
    
    webbrowser.open("https://www.instagram.com")
    
    print()
    print("STEP 4: Once logged in, press F12")
    print("        (Or right-click anywhere and select 'Inspect')")
    print()
    print("STEP 5: Click the 'Application' tab (at the top)")
    print()
    print("STEP 6: On the left, click 'Cookies' → 'instagram.com'")
    print()
    print("STEP 7: Scroll down and find 'sessionid' in the list")
    print("        Click on it, then copy the 'Value' column")
    print()
    print("-" * 60)
    print()
    session_id = input("Paste your session ID here: ").strip()
    
    if not session_id:
        print("No session ID provided. That's okay - downloads may still work!")
        return
    
    # Save to .env
    env_path = Path(".env")
    existing = ""
    if env_path.exists():
        existing = env_path.read_text()
    
    if "INSTAGRAM_SESSIONID=" in existing:
        import re
        existing = re.sub(r'INSTAGRAM_SESSIONID=.*', f'INSTAGRAM_SESSIONID={session_id}', existing)
    else:
        existing += f"\nINSTAGRAM_SESSIONID={session_id}\n"
    
    env_path.write_text(existing.strip() + "\n")
    
    print()
    print("=" * 60)
    print("  ✅ SAVED! Now your downloads will be super reliable!")
    print("=" * 60)
    print()
    print("Run: streamlit run app.py")


if __name__ == "__main__":
    main()
