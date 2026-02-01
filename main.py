import os
import json
import time
import random
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("streak_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def run_automation():
    # Load configuration from environment variables
    # FRIENDS_LIST should be a comma-separated list of TikTok usernames or profile URLs
    friends_raw = os.getenv("FRIENDS_LIST", "")
    
    if not friends_raw and os.path.exists("friends.txt"):
        with open("friends.txt", "r") as f:
            friends_raw = ",".join([line.strip() for line in f if line.strip()])
            
    friends = [f.strip() for f in friends_raw.split(",") if f.strip()]
    
    # COOKIES_JSON should be the content of the cookies file as a string
    cookies_str = os.getenv("TIKTOK_COOKIES")
    
    if not cookies_str:
        logger.error("TIKTOK_COOKIES environment variable is missing!")
        return

    if not friends:
        logger.warning("FRIENDS_LIST is empty. No streaks to maintain.")
        return

    try:
        cookies = json.loads(cookies_str)
    except json.JSONDecodeError:
        logger.error("Failed to parse TIKTOK_COOKIES. Ensure it is a valid JSON string.")
        return

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True) # Run headless for GitHub Actions
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Add cookies to context
        context.add_cookies(cookies)
        
        page = context.new_page()
        
        success_count = 0
        failed_friends = []

        for friend in friends:
            logger.info(f"Processing streak for: {friend}")
            try:
                # Navigate to the direct message page
                profile_url = f"https://www.tiktok.com/@{friend}" if not friend.startswith("http") else friend
                logger.info(f"Navigating to: {profile_url}")
                page.goto(profile_url, wait_until="networkidle")
                
                # Check if we are logged in
                if page.url.startswith("https://www.tiktok.com/login"):
                    logger.error("Cookies expired or invalid. Redirected to login page.")
                    break

                # Try to send message with retries
                for attempt in range(3):
                    try:
                        # Random delay before action to look human
                        time.sleep(random.uniform(5, 10))
                        
                        # Wait for the 'Message' button
                        message_btn_selector = '[data-e2e="user-message"]'
                        page.wait_for_selector(message_btn_selector, timeout=15000)
                        page.click(message_btn_selector)
                        
                        # Wait for the chat to open
                        page.wait_for_selector('div[contenteditable="true"]', timeout=15000)
                        
                        # Type message with a slight delay
                        time.sleep(random.uniform(2, 4))
                        page.fill('div[contenteditable="true"]', "🔥 Streak maintenance!")
                        time.sleep(random.uniform(1, 2))
                        page.keyboard.press("Enter")
                        
                        logger.info(f"Successfully sent streak message to {friend}")
                        success_count += 1
                        break
                    except Exception as e:
                        if attempt == 2: raise e
                        logger.warning(f"Attempt {attempt+1} failed for {friend}. Retrying...")
                        page.reload()
                        time.sleep(random.uniform(10, 15))

                # Longer randomized delay between different friends (15-30 seconds)
                # This is crucial for "All-In" with 42 friends
                wait_time = random.uniform(15, 30)
                logger.info(f"Waiting {wait_time:.2f} seconds before next friend...")
                time.sleep(wait_time)

            except PlaywrightTimeoutError:
                logger.error(f"Timeout while processing {friend}. The UI might have changed or the user was not found.")
                failed_friends.append(friend)
            except Exception as e:
                logger.error(f"An error occurred for {friend}: {str(e)}")
                failed_friends.append(friend)

        browser.close()
        
        # Final Report
        logger.info(f"--- Automation Complete ---")
        logger.info(f"Total Friends: {len(friends)}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {len(failed_friends)}")
        if failed_friends:
            logger.info(f"Failed friends: {', '.join(failed_friends)}")

if __name__ == "__main__":
    run_automation()
