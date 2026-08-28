# 🚀 Step-by-Step 24/7 Cloud Deployment & Telegram Alerts Guide

This guide walks you through:
1. Setting up your free **Telegram Alert Bot** (takes 2 minutes).
2. Deploying this terminal to **Streamlit Community Cloud via GitHub** (100% Free, runs 24/7 without your laptop).

---

## 📱 PART 1: Set Up Telegram Alerts (2 Minutes)

### Step 1: Create your Telegram Bot
1. Open the Telegram app on your phone or PC.
2. Search for **`@BotFather`** and click **Start**.
3. Send the command:
   ```text
   /newbot
   ```
4. Follow the prompts:
   - Give your bot a display name (e.g. `My Crude Signals`).
   - Give your bot a username ending in `bot` (e.g. `crude_pro_signals_bot`).
5. **Copy the HTTP API Token** provided by BotFather (it looks like `7123456789:AAFlxyz...`).

### Step 2: Get Your Private Chat ID
1. Search for **`@userinfobot`** in Telegram and click **Start**.
2. It will reply with your personal **Id** (e.g., `987654321`). Copy this number.
3. Open your new bot (the one you just created with BotFather) and click **Start** (this allows the bot to message you).

### Step 3: Test It in Your Terminal UI
1. Open your terminal at **`http://localhost:8501`**.
2. Under **Live Execution & Signals**, click the **`📲 Telegram Alerts`** button.
3. Paste your **Bot Token** and **Chat ID**, then click **`📲 Test Ping`**.
4. You will instantly receive a test message on your phone!

---

## ☁️ PART 2: Deploy to Streamlit Community Cloud (Runs 24/7)

Streamlit Community Cloud is **100% free** and hosts your terminal continuously on Google/AWS cloud servers so you receive signals even when your laptop is turned off.

### Step 1: Push Project to a Private GitHub Repository
1. Open GitHub (https://github.com) and create a **New Repository**:
   - Repository Name: `crude-signal-dashboard`
   - Privacy: **Private** (recommended)
2. Open PowerShell in your project folder (`C:\Users\admin\.gemini\antigravity\scratch\crude-signal-dashboard`) and run:
   ```powershell
   git init
   git add .
   git commit -m "Initial release with Telegram alerts and Strategy Vault"
   git branch -M main
   git remote add origin https://github.com/YOUR_GITHUB_USERNAME/crude-signal-dashboard.git
   git push -u origin main
   ```

### Step 2: Deploy on Streamlit Cloud
1. Go to **[https://share.streamlit.io](https://share.streamlit.io)** and log in with your GitHub account.
2. Click **"New App"**.
3. Select your repository: `crude-signal-dashboard`, Branch: `main`, Main file path: `dashboard.py`.
4. Click **"Advanced Settings"** (or go to App Settings > Secrets after deployment).
5. In the **Secrets** box, paste:
   ```toml
   UPSTOX_ACCESS_TOKEN = "your_upstox_token_here"
   TELEGRAM_BOT_TOKEN = "your_telegram_bot_token_here"
   TELEGRAM_CHAT_ID = "your_telegram_chat_id_here"
   ENABLE_TELEGRAM = true
   ```
6. Click **Deploy!**

---

### 🎉 You're All Set!
Your terminal is now live on the cloud at your custom URL (e.g., `https://crude-pro-terminal.streamlit.app`).
* It monitors MCX Crude Oil market feeds 24/7.
* Whenever a high-probability trade aligns with Setup 1, 2, or 3, you will receive an instant, formatted trade alert directly on your Telegram!
