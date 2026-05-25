🛒 SmartPrice-Tracker
https://img.shields.io/badge/Python-3.10%252B-3776AB?logo=python&logoColor=white
https://img.shields.io/badge/React-18.2-61DAFB?logo=react&logoColor=white
https://img.shields.io/badge/Flask-2.3-000000?logo=flask&logoColor=white
https://img.shields.io/badge/Vite-4.5-646CFF?logo=vite&logoColor=white
https://img.shields.io/badge/License-MIT-green

Real‑time price intelligence across 5 major e‑commerce platforms —
An academic project by first‑year students at Zewail City of Science, Technology and Innovation
(School of Computational Sciences and Artificial Intelligence | AI & Data Science)

#📖 Overview
SmartPrice-Tracker is a full‑stack price comparison and analytics dashboard. It scrapes live product data from Amazon, Jumia, Noon, eBay, and Walmart, normalizes prices (USD → EGP), and presents the results in a modern React dashboard.

The system provides:

🔍 Instant scraping of the best price, rating, and reviews for any electronics query.

📊 Interactive visualizations (bar charts, 3D scatter plots, network graphs).

🔐 User authentication with persistent search history.

🤖 Telegram bot that lets you search, receive results, and email summaries from your phone.

📧 Email reports – send any search result directly to your inbox.

Built as a first‑year group project, it demonstrates modular design, hybrid scraping strategies (Requests/BeautifulSoup + SerpAPI + headless browser fallbacks), and a clean separation between backend API and frontend SPA.

##✨ Features
Feature	Description
Multi‑site scraping	Amazon (SerpAPI), Jumia (Requests + Selenium fallback), Noon (API + Selenium), eBay (SerpAPI), Walmart (SerpAPI)
Currency normalisation	Live USD → EGP exchange rate (with fallback)
Price history & alerts	Detects price drops and sends Telegram/email alerts
Interactive dashboard	Bar charts, radar charts, price trends, 3D scatter plots (Plotly)
User system	Register/login with JWT – history stored per user
Telegram bot	/search, /best, /history, /send_email, /login, /register
Email reports	Send a formatted HTML table of results to any email address
CLI dashboard	Quick terminal‑based summary (best/worst/average price)
Modular scrapers	Each platform in its own file with shared validation logic
🧱 Tech Stack
Backend & Scraping
Python 3.10+ – core logic

Flask – REST API + JWT authentication

Undetected ChromeDriver – headless browser for Jumia/Noon fallbacks

Requests + BeautifulSoup – HTML parsing

SerpAPI – reliable scraping for Amazon, eBay, Walmart

Plotly, Matplotlib, NetworkX – visualisation generation

python‑dotenv – environment configuration

Frontend
React 18 – component‑based UI

Vite – fast builds & HMR

React Router DOM – client‑side routing

Framer Motion – smooth animations

Recharts – responsive charts

Lucide React – icon set

Database (lightweight)
JSON file storage – users.json, history.json, price_history.json

###🚀 Installation & Setup
1. Clone the repository
bash
git clone https://github.com/yourusername/SmartPrice-Tracker.git
cd SmartPrice-Tracker
2. Backend setup (Python)
Create a virtual environment and install dependencies:

bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
⚠️ requirements.txt should contain at least:
flask flask-cors flask-jwt-extended requests beautifulsoup4 undetected-chromedriver selenium plotly matplotlib networkx pandas python-dotenv

3. Frontend setup (React / Vite)
Open a second terminal:

bash
cd frontend   # or wherever your React app lives (usually the root of frontend folder)
npm install
4. Environment variables (.env)
Create a .env file in the backend root directory (same folder as app.py):

ini
# Required for Amazon/eBay/Walmart scraping
SERPAPI_KEY=your_serpapi_key_here

# JWT secret – change to a random string
JWT_SECRET_KEY=your_super_secret_key

# Optional: Telegram bot (see telegram_bot.py)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional: Email alerts (Gmail SMTP)
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
📌 Get a SerpAPI key from serpapi.com (free tier available).

5. Directory structure (ensure these exist)
The backend will automatically create data/ and data/charts/ folders.

####🖥️ Usage
Start the backend (Flask API)
From the backend directory (where app.py is located):

bash
python app.py
The API will run at http://localhost:5000

Start the frontend (React dev server)
From the frontend directory:

bash
npm run dev
The frontend will run at http://localhost:5173

Both servers must be running simultaneously.

Login to the web dashboard
Open http://localhost:5173

Register a new account or log in (any username/password – demo‑ready)

Enter a product name (e.g. iPhone 15 Pro, MacBook Air M4)

View results, charts, and save to history

Using the Telegram bot
Find your bot on Telegram (if you set TELEGRAM_BOT_TOKEN)

Send /start

Register or login – then use /search iPhone 15

Get results, email them, or check history

CLI dashboard (terminal only)
From the backend directory, run:

bash
python main.py
This will ask for authentication, then a product name, and output a formatted table + save CSV + generate charts in the current folder.

##### 📁 Project Structure (simplified)

```text
SmartPrice-Tracker/
├── app.py                  # Flask backend (API, auth, history)
├── main.py                 # CLI entry point (original standalone)
├── scrapers/               # Site-specific scrapers
│   ├── amazon_scraper.py
│   ├── jumia_scraper.py
│   ├── noon_scraper.py
│   ├── ebay_scraper.py
│   └── walmart_scraper.py
├── currency.py             # USD -> EGP conversion
├── alerts.py               # Telegram & email alerts
├── user_manager.py         # Register / login (JSON storage)
├── telegram_bot.py         # Telegram bot loop
├── visualizer.py           # Matplotlib summary chart
├── viz3d.py                # Plotly 3D scatter
├── network_viz.py          # NetworkX graph
├── cli_dashboard.py        # Terminal statistics
├── price_history.py        # Track price drops
├── data/                   # Auto-created JSON files
│   ├── users.json
│   ├── history.json
│   └── charts/             # Generated 3D HTML files
└── frontend/               # React + Vite frontend
    ├── src/
    │   ├── App.jsx
    │   ├── AuthPage.jsx
    │   ├── SearchPage.jsx
    │   ├── HistoryPage.jsx
    │   ├── VisualizerPage.jsx
    │   └── ...
    └── package.json
```

######👥 Contributors & Academic Credit
This project was developed as a 1st‑year academic project at:

Zewail City of Science, Technology and Innovation
School of Computational Sciences and Artificial Intelligence
Specialisation: Artificial Intelligence & Data Science

###Author Roles
**Matthew Alber William Hakeem : Full stack developer & Co-Author**
**Omar Mohmed Hassan : Full stack developer & Co-Author**
**Supervised by the faculty of the AI & Data Science program.**

-📌 The project demonstrates proficiency in full‑stack development, web scraping, data normalisation, and interactive analytics – all within a collaborative academic environment.

-📜 License
This project is licensed under the MIT License – feel free to use, modify, and distribute with attribution.

-🙌 Acknowledgments
SerpAPI for reliable search result APIs

Undetected ChromeDriver for stealth browsing

Plotly & Recharts for beautiful charts

Framer Motion for fluid animations

Built with ❤️ by Matthew & Omar – Zewail City Class of 2026
