# Deployment Guide: Streamlit Community Cloud & GitHub Actions

This document provides step-by-step instructions for deploying the **Indian Equity Portfolio Management Terminal** to **Streamlit Community Cloud** and setting up automated weekday pipeline refreshes.

---

## 1. Prerequisites
- A **GitHub Account**.
- Access to the repository containing this codebase (`c:\equity portfolio`).
- A **Streamlit Community Cloud Account** (sign in with your GitHub account at [share.streamlit.io](https://share.streamlit.io)).

---

## 2. Step-by-Step Deployment Instructions

### Step 1: Push Code & Precomputed Parquet Files to GitHub
Ensure all repository files including production parquet datasets (`data/parquet/`) and workflow configurations (`.github/workflows/refresh.yml`) are committed and pushed to your GitHub repository:
```bash
git add .
git commit -m "Production release: Indian Equity Portfolio Management Terminal"
git push origin main
```

### Step 2: Deploy App on Streamlit Community Cloud
1. Log in to [share.streamlit.io](https://share.streamlit.io).
2. Click **"New app"** (or **"Create app"**).
3. Select your GitHub repository (`equity-portfolio`), branch (`main` or `master`), and set Main file path to:
   ```
   app.py
   ```
4. Click **"Deploy!"**. Streamlit will install dependencies from `requirements.txt` and launch the application.

### Step 3: Secrets Management (Optional API Keys)
If you configure external API keys in the future (e.g., custom Screener or financial data providers):
1. In the Streamlit Cloud app dashboard, click **Settings** -> **Secrets**.
2. Paste secrets using TOML format:
   ```toml
   [api_keys]
   screener_key = "your_screener_api_key_here"
   ```
3. Save changes. In code, secrets are accessible via `st.secrets["api_keys"]["screener_key"]`.

---

## 3. GitHub Actions Automated Pipeline Setup

The repository includes an automated workflow at `.github/workflows/refresh.yml` that runs every weekday at 19:30 IST (14:00 UTC).

### Step-by-Step Action Permissions Setup:
1. In your GitHub repository, navigate to **Settings** -> **Actions** -> **General**.
2. Under **Workflow permissions**, select **"Read and write permissions"**.
3. Check the box **"Allow GitHub Actions to create and approve pull requests"**.
4. Click **Save**.

Now, every weekday at 19:30 IST, GitHub Actions will:
- Execute `python -m pipeline.run`.
- Update historical price, index, option, and fundamental parquet files in `data/parquet/`.
- Commit and push updated datasets back to the repository.

---

## 4. Idle App Sleep & Wake-Up Strategy

Free Streamlit Community Cloud applications enter a **"sleeping"** state after 7 consecutive days of inactivity.

### Suggested Automated Wake-Up Approaches:
1. **GitHub Actions Keep-Alive Ping**:
   - The weekday GitHub Actions workflow commits fresh data to the repo, which automatically wakes up the Streamlit app.
2. **UptimeRobot / Health Check Ping**:
   - Register a free HTTP monitor at [uptimerobot.com](https://uptimerobot.com).
   - Add your deployed Streamlit URL (e.g., `https://your-app-name.streamlit.app`) to ping every 5 minutes.

---

## 5. Needs Your Input (Manual User Action Items)
To finalize live deployment on your personal accounts:
1. Push this repository to your GitHub account.
2. Link the repository on [share.streamlit.io](https://share.streamlit.io).
3. Enable **Read and write permissions** under GitHub Repository Settings -> Actions -> General.
