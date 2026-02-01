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
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        
        # Add cookies to context
        context.add_cookies(cookies)
        
        page = context.new_page()
        
        success_count = 0
        failed_friends = []

        for friend in friends:
            logger.info(f"Processing streak for: {friend}")
            try:
                # Navigate to the profile page
                profile_url = f"https://www.tiktok.com/@{friend}" if not friend.startswith("http") else friend
                logger.info(f"Navigating to profile: {profile_url}")
                
                try:
                    page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    logger.warning(f"Navigation to profile for {friend} timed out, trying to proceed...")

                # Check if we are logged in
                if "tiktok.com/login" in page.url:
                    logger.error("Cookies expired or invalid. Redirected to login page.")
                    break

                # Try to send message with retries
                for attempt in range(3):
                    try:
                        # 1. Click the Message button on profile
                        message_btn_selectors = [
                            '[data-e2e="message-button"]',
                            'a[href*="/messages"]',
                            'button:has-text("Message")',
                            'a.link-a11y-focus'
                        ]
                        
                        found_btn = False
                        for selector in message_btn_selectors:
                            try:
                                btn = page.locator(selector).first
                                if btn.is_visible(timeout=5000):
                                    btn.click()
                                    found_btn = True
                                    logger.info(f"Clicked Message button using: {selector}")
                                    break
                            except:
                                continue
                        
                        if not found_btn:
                            raise Exception("Could not find Message button on profile")

                        # 2. Wait for chat input and send
                        # Give it a moment to load the chat page
                        time.sleep(random.uniform(5, 8))
                        
                        chat_input_selectors = [
                            '[data-e2e="message-input-area"] [contenteditable="true"]',
                            '[contenteditable="true"]',
                            '.public-DraftEditor-content'
                        ]
                        
                        found_input = False
                        for selector in chat_input_selectors:
                            try:
                                el = page.locator(selector).first
                                if el.is_visible(timeout=10000):
                                    logger.info(f"Found input field with: {selector}")
                                    el.focus()
                                    el.click()
                                    time.sleep(2)
                                    
                                    # Type the message
                                    page.keyboard.type("เติมไฟกันจ้า🔥🔥", delay=150)
                                    time.sleep(2)
                                    
                                    # TikTok usually has a send icon (SVG) that becomes clickable after typing
                                    # We try to click anything inside the input area that looks like a send button
                                    send_btn_selectors = [
                                        '[data-e2e="chat-send"]',
                                        'div[role="button"] svg',
                                        'button[aria-label="Send"]',
                                        'svg path[d*="M12"]' # Common path for send icons
                                    ]
                                    
                                    for s_selector in send_btn_selectors:
                                        try:
                                            s_btn = page.locator(s_selector).last
                                            if s_btn.is_visible(timeout=3000):
                                                s_btn.click()
                                                logger.info(f"Clicked send icon using: {s_selector}")
                                                found_input = True
                                                break
                                        except:
                                            continue
                                    
                                    if not found_input:
                                        logger.info("Send icon not found, trying Enter key...")
                                        page.keyboard.press("Enter")
                                        found_input = True
                                    
                                    break
                            except:
                                continue
                        
                        if found_input:
                            logger.info(f"Successfully sent message to {friend}")
                            success_count += 1
                            break
                        else:
                            logger.warning(f"Attempt {attempt+1} failed. Reloading...")
                            page.reload()
                            time.sleep(5)
                    except Exception as e:
                        if attempt == 2: raise e
                        logger.warning(f"Attempt {attempt+1} failed: {str(e)}")
                        page.reload()
                        time.sleep(5)

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
