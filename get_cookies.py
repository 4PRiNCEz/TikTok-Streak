import json
from playwright.sync_api import sync_playwright

def export_cookies():
    print("This script will open a browser window for you to log into TikTok.")
    print("Once you are logged in, come back here and press Enter.")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Must be visible to log in
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.tiktok.com/login")
        
        input("Log in manually in the browser window, then press Enter here to save cookies...")
        
        cookies = context.cookies()
        with open("cookies.json", "w") as f:
            json.dump(cookies, f)
            
        print("Cookies saved to cookies.json!")
        print("Copy the contents of cookies.json and add it to your GitHub Secrets as TIKTOK_COOKIES.")
        browser.close()

if __name__ == "__main__":
    export_cookies()
