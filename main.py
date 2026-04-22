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
            
    # Handle both commas and newlines as separators
    friends = []
    if friends_raw:
        # Replace newlines with commas, then split and strip
        friends = [f.strip() for f in friends_raw.replace("\n", ",").split(",") if f.strip()]
    
    # COOKIES_JSON should be the content of the cookies file as a string
    cookies_str = os.getenv("TIKTOK_COOKIES")
    
    # [NEW] Fallback to cookies.json if env var is missing (helpful for local testing)
    if not cookies_str and os.path.exists("cookies.json"):
        logger.info("TIKTOK_COOKIES env var not found. Loading from cookies.json...")
        try:
            with open("cookies.json", "r") as f:
                cookies_str = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read cookies.json: {str(e)}")

    if not cookies_str:
        logger.error("TIKTOK_COOKIES is missing (check your GitHub Secrets or cookies.json)!")
        return

    try:
        cookies = json.loads(cookies_str)
    except json.JSONDecodeError:
        logger.error("Failed to parse cookies. Ensure it is a valid JSON string.")
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
                clean_friend = friend.lstrip('@') if not friend.startswith("http") else friend
                profile_url = f"https://www.tiktok.com/@{clean_friend}" if not clean_friend.startswith("http") else clean_friend
                logger.info(f"Navigating to profile: {profile_url}")
                
                try:
                    # Use 'load' instead of 'networkidle' for better compatibility
                    page.goto(profile_url, wait_until="load", timeout=60000)
                    time.sleep(5)
                    
                    # SUPER DEBUG: Only log title and check for blocks
                    title = page.title()
                    logger.info(f"Page Title: {title}")
                    # Sanitize friend name for filename
                    safe_name = "".join([c for c in clean_friend if c.isalnum() or c in (" ", "-", "_")]).strip()

                    # [NEW] Check for 'Not Found' or blocks (Robust fuzzy matching)
                    title_lower = title.lower()
                    if "verify" in title_lower or "captcha" in title_lower or "cloudflare" in title_lower:
                        logger.error(f"BOT BLOCKED: TikTok is showing a Captcha/Verification screen for {friend}.")
                        page.screenshot(path=f"blocked_{safe_name}.png")
                        failed_friends.append(friend)
                        continue
                    
                    if "find this account" in title_lower or "not found" in title_lower:
                        logger.error(f"PROFILE NOT FOUND: TikTok says the account for '{friend}' does not exist.")
                        page.screenshot(path=f"not_found_{safe_name}.png")
                        failed_friends.append(friend)
                        continue
                except Exception as e:
                    logger.error(f"Profile for {friend} failed to load: {str(e)}")
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
                            page.screenshot(path=f"missing_button_{safe_name}_at_{attempt+1}.png")
                            raise Exception("Could not find Message button, link, or User ID")

                        # 2. Wait for chat input to ensure chat has loaded
                        time.sleep(random.uniform(5, 8)) # Give it some time to load
                        
                        chat_input_selectors = [
                            '[data-e2e="message-input-area"] [contenteditable="true"]',
                            '[contenteditable="true"]',
                            '.public-DraftEditor-content',
                            '[role="textbox"]'
                        ]
                        
                        found_input = False
                        input_element = None
                        for selector in chat_input_selectors:
                            try:
                                el = page.locator(selector).first
                                if el.is_visible(timeout=5000):
                                    input_element = el
                                    found_input = True
                                    break
                            except:
                                continue

                        if not found_input:
                            logger.info("Input field not found yet. Will try blind typing later.")

                        # --- CHECK HISTORY ONCE CHAT IS OPEN ---
                        logger.info("Checking if message was already sent today...")
                        page.screenshot(path=f"debug_chat_{safe_name}.png") # [DEBUG] See what the bot sees
                        
                        already_sent_today = False
                        today_str = time.strftime("%Y-%m-%d")
                        
                        try:
                            # TikTok uses virtual scrolling - only visible messages are in the DOM.
                            # We scroll up step-by-step, checking at each position, to find our outgoing message.
                            result_str = "SEND: No timestamps found in chat."
                            
                            js_check = """(today_str) => {
                                const allElements = Array.from(document.querySelectorAll('[class*="DivTimeContainer"], [class*="DivChatItemWrapper"]'));
                                
                                if (allElements.length === 0) return "CONTINUE: No elements found yet.";

                                let everFoundTodayTimestamp = false;
                                let everFoundOutgoingToday = false;
                                let currentSectionIsToday = false;
                                let oldestTimestamp = null;

                                for (const el of allElements) {
                                    const className = el.className || '';
                                    
                                    if (className.includes('DivTimeContainer')) {
                                        const timeText = (el.innerText || '').trim();
                                        if (!oldestTimestamp) oldestTimestamp = timeText;
                                        const isTime = /^\\d{1,2}[:.]\\d{2}(?:\\s?[AaPp][Mm])?$/.test(timeText);
                                        const hasToday = timeText.toLowerCase().includes('today') || timeText.includes(today_str);
                                        currentSectionIsToday = isTime || hasToday;
                                        if (currentSectionIsToday) everFoundTodayTimestamp = true;
                                    } 
                                    else if (className.includes('DivChatItemWrapper') && currentSectionIsToday) {
                                        let isOutgoing = false;
                                        
                                        const horizontalContainers = el.querySelectorAll('[class*="DivMessageHorizontalContainer"]');
                                        for (let i = 0; i < horizontalContainers.length; i++) {
                                            const hcStyle = window.getComputedStyle(horizontalContainers[i]);
                                            if (hcStyle.flexDirection === 'row-reverse' || hcStyle.justifyContent === 'flex-end') {
                                                isOutgoing = true;
                                            }
                                        }

                                        const avatars = el.querySelectorAll('[data-e2e="chat-avatar"]');
                                        for (let i = 0; i < avatars.length; i++) {
                                            if (avatars[i].getBoundingClientRect().left > window.innerWidth / 2) {
                                                isOutgoing = true;
                                            }
                                        }

                                        const textBubble = el.querySelector('[data-e2e="dm-new-message-text"]');
                                        if (textBubble && textBubble.getBoundingClientRect().left > window.innerWidth / 2) {
                                            isOutgoing = true;
                                        }

                                        const style = window.getComputedStyle(el);
                                        if (style.justifyContent === 'flex-end' || style.textAlign === 'right' || style.float === 'right') {
                                            isOutgoing = true;
                                        }

                                        if (isOutgoing) {
                                            everFoundOutgoingToday = true;
                                        }
                                    }
                                }

                                if (everFoundOutgoingToday) {
                                    return "SKIP: Found outgoing message under a today timestamp.";
                                }
                                
                                // Check if the oldest visible timestamp is NOT from today — means we've scrolled past all today's messages
                                if (oldestTimestamp) {
                                    const isOldTime = /^\\d{1,2}[:.]\\d{2}/.test(oldestTimestamp) === false && 
                                                      !oldestTimestamp.toLowerCase().includes('today') && 
                                                      !oldestTimestamp.includes(today_str);
                                    if (isOldTime && everFoundTodayTimestamp) {
                                        return "SEND: Scrolled through all today's messages, no outgoing found.";
                                    }
                                }
                                
                                if (everFoundTodayTimestamp) {
                                    return "CONTINUE: Today's messages visible but no outgoing yet, scroll more.";
                                }
                                
                                return "SEND: No today timestamps found.";
                            }"""
                            
                            # First check at current scroll position (bottom of chat)
                            result_str = page.evaluate(js_check, today_str)
                            logger.info(f"Scroll check 0: {result_str}")
                            
                            if result_str.startswith("CONTINUE"):
                                # Scroll up incrementally to find our outgoing message
                                for scroll_i in range(10):
                                    page.evaluate("""() => {
                                        const containers = document.querySelectorAll('[class*="DivChatMessageList"], [class*="DivMessageListContainer"], [class*="DivChatList"]');
                                        for (const c of containers) {
                                            if (c.scrollHeight > c.clientHeight) {
                                                c.scrollTop = Math.max(0, c.scrollTop - 500);
                                                return;
                                            }
                                        }
                                        // Fallback: scroll using mouse wheel on the chat area
                                        window.scrollBy(0, -500);
                                    }""")
                                    time.sleep(1)
                                    
                                    result_str = page.evaluate(js_check, today_str)
                                    logger.info(f"Scroll check {scroll_i + 1}: {result_str}")
                                    
                                    if not result_str.startswith("CONTINUE"):
                                        break
                            
                            logger.info(f"History Check Result: {result_str}")
                            already_sent_today = result_str.startswith("SKIP")
                            
                        except Exception as e:
                            logger.warning(f"Failed to check chat history (fail-open): {str(e)}")
                            
                        if already_sent_today:
                            logger.info(f"Skipped {friend} - already sent today")
                            success_count += 1
                            break

                        # --- SEND MESSAGE ---
                        if found_input and input_element:
                            try:
                                input_element.focus()
                                input_element.click()
                                time.sleep(2)
                                page.keyboard.type("โฟปริ้นลืมเติมไฟอีกแล้วจ้า ระบบสำรองไฟทำงาน😎", delay=200)
                                time.sleep(2)
                                page.keyboard.press("Enter")
                                time.sleep(1)
                                page.keyboard.press("Enter") # Double tap
                                
                                logger.info(f"Successfully sent message to {friend}")
                                success_count += 1
                                break
                            except Exception as e:
                                logger.warning(f"Failed to type in input field: {str(e)}")
                                found_input = False # Fallback to blind typing
                        
                        if not found_input:
                            # Blind typing attempt
                            logger.info("Input field not found. Trying Blind Typing...")
                            for _ in range(3): page.keyboard.press("Tab")
                            time.sleep(1)
                            page.keyboard.type("โฟปริ้นลืมเติมไฟอีกแล้วจ้า ระบบสำรองไฟทำงาน😎", delay=200)
                            page.keyboard.press("Enter")
                            time.sleep(1)
                            page.keyboard.press("Enter")
                            page.screenshot(path=f"blind_attempt_{safe_name}.png")
                            logger.info(f"Successfully sent message to {friend} (Blind Typing)")
                            found_input = True # Assume success for logging
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
