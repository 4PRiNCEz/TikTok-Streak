import json
import os
from playwright.sync_api import sync_playwright

def export_cookies():
    print("--- TikTok Cookie Exporter (Stealth Mode) ---")
    print("1. A browser will open shortly.")
    print("2. Log into TikTok manually.")
    print("3. Once you see your 'For You' feed, come back here and press Enter.")
    
    with sync_playwright() as p:
        # Using a real-looking User Agent to avoid 'Maximum attempts' error
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        
        # Launch browser with some 'human' arguments
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(user_agent=user_agent)
        
        page = context.new_page()
        
        # Navigate to TikTok
        page.goto("https://www.tiktok.com/login")
        
        input("\n[ACTION REQUIRED]: Log in manually in the browser window, then press Enter here...")
        
        # Capture cookies
        cookies = context.cookies()
        
        with open("cookies.json", "w") as f:
            json.dump(cookies, f)
            
        print("\n✅ SUCCESS: Cookies saved to cookies.json!")
        print("Copy the contents of cookies.json to your GitHub Secrets as TIKTOK_COOKIES.")
        browser.close()

if __name__ == "__main__":
    export_cookies()