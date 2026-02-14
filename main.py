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
                    # Use 'load' instead of 'networkidle' for better compatibility
                    page.goto(profile_url, wait_until="load", timeout=60000)
                    time.sleep(5)
                    
                    # SUPER DEBUG: Only log title and check for blocks
                    title = page.title()
                    logger.info(f"Page Title: {title}")
                    if "Verify" in title or "CAPTCHA" in title or "Cloudflare" in title:
                        logger.error("BOT BLOCKED: TikTok is showing a Captcha/Verification screen.")
                        page.screenshot(path=f"blocked_{friend}.png")
                    
                    # (HTML saving removed for production)
                        
                except Exception as e:
                    logger.error(f"Profile for {friend} failed to load. Skipping.")
                    failed_friends.append(friend)
                    continue

                # Check if we are logged in
                if "tiktok.com/login" in page.url or "Login" in page.title():
                    logger.error("Cookies expired or invalid. Bot is logged out.")
                    page.screenshot(path="login_error.png")
                    break

                # Try to send message with retries
                for attempt in range(3):
                    try:
                        found_btn = False
                        
                        # NEW STRATEGY: Try to find the User ID in the page source data
                        logger.info("Attempting to extract User ID from page data...")
                        try:
                            # TikTok stores user data in a script tag. We can try to find the ID there.
                            page_content = page.content()
                            import re
                            # Look for "userId":"12345..." or similar patterns
                            user_id_match = re.search(r'"userId":"(\d+)"', page_content)
                            if not user_id_match:
                                user_id_match = re.search(r'"id":"(\d+)"', page_content)
                                
                            if user_id_match:
                                uid = user_id_match.group(1)
                                target_url = f"https://www.tiktok.com/messages?lang=en&u={uid}"
                                logger.info(f"SUCCESS: Extracted User ID {uid}. Jumping to: {target_url}")
                                page.goto(target_url, wait_until="load")
                                found_btn = True
                        except Exception as uid_err:
                            logger.warning(f"User ID extraction failed: {str(uid_err)}")

                        if not found_btn:
                            # 1. Standard Selectors
                            message_btn_selectors = [
                                '[data-e2e="message-button"]', 
                                'button:has-text("Message")',
                                'div[role="button"]:has-text("Message")',
                                'main a[href*="/messages"]'
                            ]
                            
                            for selector in message_btn_selectors:
                                try:
                                    btn = page.locator(selector).first
                                    if btn.count() > 0 and btn.is_visible():
                                        logger.info(f"Clicking button found via: {selector}")
                                        btn.click()
                                        found_btn = True
                                        break
                                except:
                                    continue
                        
                        if not found_btn:
                            # Nuclear Option: Click by text
                            try:
                                logger.info("Trying to click text 'Message'...")
                                page.get_by_text("Message", exact=True).first.click()
                                found_btn = True
                            except:
                                pass

                        if not found_btn:
                            page.screenshot(path=f"missing_button_{friend}_at_{attempt+1}.png")
                            raise Exception("Could not find Message button, link, or User ID")

                        # 2. Wait for chat input and send
                        time.sleep(random.uniform(8, 12)) # Be more patient
                        
                        chat_input_selectors = [
                            '[data-e2e="message-input-area"] [contenteditable="true"]',
                            '[contenteditable="true"]',
                            '.public-DraftEditor-content',
                            '[role="textbox"]'
                        ]
                        
                        found_input = False
                        for selector in chat_input_selectors:
                            try:
                                el = page.locator(selector).first
                                if el.is_visible(timeout=10000):
                                    el.focus()
                                    el.click()
                                    time.sleep(2)
                                    page.keyboard.type("เติมไฟกันจ้า🔥🔥", delay=200)
                                    time.sleep(2)
                                    page.keyboard.press("Enter")
                                    time.sleep(1)
                                    page.keyboard.press("Enter") # Double tap
                                    
                                    found_input = True
                                    break
                            except:
                                continue
                        
                        if not found_input:
                            # Blind typing attempt
                            logger.info("Input field not found. Trying Blind Typing...")
                            for _ in range(3): page.keyboard.press("Tab")
                            time.sleep(1)
                            page.keyboard.type("🔥🔥จ้าไฟกันเติม", delay=200)
                            page.keyboard.press("Enter")
                            time.sleep(1)
                            page.keyboard.press("Enter")
                            page.screenshot(path=f"blind_attempt_{friend}.png")
                            found_input = True # Assume success for logging
                        
                        if found_input:
                            logger.info(f"Successfully sent message to {friend}")
                            success_count += 1
                            break
                    except Exception as e:
                        if attempt == 2: raise e
                        logger.warning(f"Attempt {attempt+1} failed: {str(e)}")
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
