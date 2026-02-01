# 🚀 TikTok Streak Automation Bot

A simple, beginner-friendly automation system to maintain your TikTok streaks while you're away (like at a 5-day camp!). Built using Python, Playwright, and GitHub Actions.

## 🌟 Features
- **Automatic Daily Runs**: Scheduled via GitHub Actions.
- **Easy Setup**: No coding required for configuration.
- **Secure**: Uses GitHub Secrets to store your login data.
- **Friend Management**: Easily add or remove friends to maintain streaks with.
- **Error Handling**: Retries and logs activities for troubleshooting.

---

## �️ Step-by-Step Setup (Under 30 Minutes)

### 1. The Fork Procedure
To get your own private copy of this bot:
- **GitHub Web UI**: Navigate to the top of this repository and click the **Fork** button (top right). Select your account as the owner.
- **GitHub CLI**: Run `gh repo fork [ORIGINAL_REPO_URL] --clone`.

### 2. Get Your TikTok Cookies (The "Login" Step)
Since TikTok has strict login security, we use "cookies" to stay logged in.
1. On your local computer, open a terminal/command prompt.
2. Clone your forked repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/TikTok-Streak.git
   cd TikTok-Streak
   ```
3. Install the setup tool:
   ```bash
   pip install playwright
   playwright install chromium
   ```
4. Run the cookie exporter:
   ```bash
   python get_cookies.py
   ```
5. A browser will open. **Log into TikTok manually**.
6. Once logged in, go back to the terminal and press **Enter**.
7. A file named `cookies.json` will be created. **Open it and copy all its contents.**

### 3. Add GitHub Secrets (Environment Variables)
Go to your GitHub repository settings:
1. Navigate to **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret**.
3. Name: `TIKTOK_COOKIES` -> Paste the contents of `cookies.json`.
4. Click **New repository secret** again.
5. Name: `FRIENDS_LIST` -> Paste a comma-separated list of TikTok usernames (e.g., `friend1,friend2`).

### 4. Enable & Test GitHub Actions
1. Click the **Actions** tab in your GitHub repository.
2. Click **"I understand my workflows, go ahead and enable them"**.
3. Select **Daily TikTok Streak Maintenance** from the left sidebar.
4. Click **Run workflow** to test it immediately.

---

## 🚀 Deployment & Reliability Guide (Camp-Ready)

### Why GitHub Actions for "Cloud Hosting"?
We use **GitHub Actions** because it stays online 24/7, requires **no credit card**, and is triggered automatically by the cloud.

### Uptime Monitoring & Health Checks
1. **GitHub Action Notifications**: Ensure your emails are on in **Settings > Notifications**. GitHub will email you if the bot fails.
2. **Logs**: After every run, a `streak-bot-logs` file is saved in the Actions tab.

### Rollback & Self-Healing
- **Rollback**: If a change breaks the bot, go to the **Actions** tab, find a working run, and use `git revert [COMMIT_HASH]` to go back to that version.
- **Self-Healing**: The bot automatically retries 3 times per friend if a page fails to load or a button isn't clickable.

---

## 🧪 Testing Locally
Before deploying, you can test on your own computer:
1. Create a file named `.env` in the project folder.
2. Add:
   ```env
   FRIENDS_LIST=friend1,friend2
   TIKTOK_COOKIES=[{"name": "...", "value": "..."}]
   ```
3. Run: `python main.py`

---

## 🏁 30-Minute Pre-Camp Checklist
- [ ] **Manual Run**: Triggered the workflow in the "Actions" tab successfully.
- [ ] **Log Verification**: Checked `streak-bot-logs` and saw "Successfully sent message".
- [ ] **Secret Verification**: `TIKTOK_COOKIES` is valid JSON (starts with `[`).
- [ ] **Notification Check**: GitHub notifications are enabled for failed runs.
- [ ] **Friend Check**: All usernames in `FRIENDS_LIST` are correct.

---

## 🛡️ Security Best Practices
- **Never** share your `cookies.json` file.
- If your account is compromised, log out of all devices to invalidate the cookies.

## ⚖️ Disclaimer
This project is for educational use. Use at your own risk.
