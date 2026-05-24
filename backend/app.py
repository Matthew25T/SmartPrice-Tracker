"""
PriceScout Backend API — Flask
Handles auth, search history, scraping, and email sending.
Telegram bot auto-starts when this file is run.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import undetected_chromedriver as uc
import time

from scrapers.jumia_scraper import JumiaScraper
from scrapers.noon_scraper import NoonScraper
from scrapers.amazon_scraper import AmazonScraper
from scrapers.ebay_scraper import EbayScraper
from scrapers.walmart_scraper import WalmartScraper

from currency import to_egp
from alerts import send_email, send_telegram

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
import hashlib, json, uuid, base64, io, logging
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["JWT_SECRET_KEY"]            = os.getenv("JWT_SECRET_KEY", "change-me-in-env")
app.config["JWT_ACCESS_TOKEN_EXPIRES"]  = timedelta(hours=24)

CORS(app, origins=["http://localhost:5173", "http://localhost:3000"])
jwt = JWTManager(app)

logger = logging.getLogger(__name__)

USERS_FILE   = "data/users.json"
HISTORY_FILE = "data/history.json"
CHARTS_DIR   = "data/charts"

os.makedirs("data", exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)


def _load(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Auth routes ───────────────────────────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
def register():
    body     = request.get_json()
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    if not username or not password:
        return jsonify(error="Username and password required"), 400
    users = _load(USERS_FILE)
    if username in users:
        return jsonify(error="Username already exists"), 409
    users[username] = {
        "password_hash": _hash(password),
        "created_at":    datetime.now().isoformat(),
        "avatar":        username[0].upper()
    }
    _save(USERS_FILE, users)
    token = create_access_token(identity=username)
    return jsonify(token=token, username=username, avatar=username[0].upper()), 201


@app.route("/api/login", methods=["POST"])
def login():
    body     = request.get_json()
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    users    = _load(USERS_FILE)
    if username not in users:
        return jsonify(error="Invalid credentials"), 401
    if users[username]["password_hash"] != _hash(password):
        return jsonify(error="Invalid credentials"), 401
    token = create_access_token(identity=username)
    return jsonify(token=token, username=username, avatar=username[0].upper()), 200


@app.route("/api/me", methods=["GET"])
@jwt_required()
def me():
    username = get_jwt_identity()
    users    = _load(USERS_FILE)
    u        = users.get(username, {})
    return jsonify(username=username, avatar=u.get("avatar", username[0].upper()))


# ── Search history routes ─────────────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
@jwt_required()
def get_history():
    username     = get_jwt_identity()
    history      = _load(HISTORY_FILE)
    user_history = history.get(username, [])
    return jsonify(user_history)


@app.route("/api/history", methods=["POST"])
@jwt_required()
def save_search():
    username = get_jwt_identity()
    body     = request.get_json()
    history  = _load(HISTORY_FILE)
    if username not in history:
        history[username] = []
    entry = {
        "id":         str(uuid.uuid4()),
        "query":      body.get("query"),
        "timestamp":  datetime.now().isoformat(),
        "results":    body.get("results", []),
        "chart_data": body.get("chart_data", {}),
        "summary":    body.get("summary", {}),
    }
    history[username].insert(0, entry)
    history[username] = history[username][:50]
    _save(HISTORY_FILE, history)
    return jsonify(entry), 201


@app.route("/api/history/<entry_id>", methods=["DELETE"])
@jwt_required()
def delete_history(entry_id):
    username = get_jwt_identity()
    history  = _load(HISTORY_FILE)
    if username in history:
        history[username] = [e for e in history[username] if e["id"] != entry_id]
        _save(HISTORY_FILE, history)
    return jsonify(ok=True)


# ── Scrape endpoint ───────────────────────────────────────────────────────────
@app.route("/api/scrape", methods=["POST"])
@jwt_required()
def scrape():
    body  = request.get_json()
    query = body.get("query", "Product")

    SITE_COLORS = {
        "Amazon": "#FF9900", "Jumia": "#E83030", "Noon": "#FECC00",
        "eBay": "#86B817", "Walmart": "#0071CE",
    }

    SCRAPERS = [
        (JumiaScraper,  3),
        (NoonScraper,   5),
        (AmazonScraper, 4),
        (EbayScraper,   4),
        (WalmartScraper,4),
    ]

    logger.info(f"Starting scrape for: {query}")

    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    try:
        driver = uc.Chrome(options=options, version_main=147)
        driver.set_page_load_timeout(30)
    except Exception as e:
        logger.error(f"Failed to initialize driver: {e}")
        return jsonify(error="Could not start scraping engine"), 500

    raw_results = []
    for ScraperClass, delay in SCRAPERS:
        try:
            scraper = ScraperClass(driver)
            res = scraper.scrape(query)
            if res:
                raw_results.extend(res)
        except Exception as e:
            logger.error(f"[{ScraperClass.SITE}] Scraping error: {e}", exc_info=True)
        finally:
            time.sleep(delay)

    try:
        driver.quit()
    except Exception:
        pass

    if not raw_results:
        return jsonify(results=[], summary={})

    results = []
    for r in raw_results:
        try:
            egp_price = to_egp(r["Price"], r["Currency"])
        except Exception:
            egp_price = r["Price"] * 49.0 if r["Currency"] == "USD" else r["Price"]

        results.append({
            "site":        r["Site"],
            "product":     r["Product"],
            "price":       r["Price"],
            "currency":    r["Currency"],
            "price_egp":   round(egp_price, 2),
            "rating":      r["Rating"],
            "reviews":     r["Reviews"],
            "color":       SITE_COLORS.get(r["Site"], "#6c63ff"),
            "product_url": r.get("Product_URL", ""),
        })

    results.sort(key=lambda x: x["price_egp"])
    best  = results[0]
    worst = results[-1]
    avg   = round(sum(r["price_egp"] for r in results) / len(results), 2)

    summary = {
        "best_price":  best["price_egp"],
        "best_site":   best["site"],
        "worst_price": worst["price_egp"],
        "worst_site":  worst["site"],
        "avg_price":   avg,
        "total_sites": len(results),
    }
    return jsonify(results=results, summary=summary)


# ── Send results via email ────────────────────────────────────────────────────
@app.route("/api/send_results", methods=["POST"])
@jwt_required()
def send_results_email():
    data    = request.get_json()
    email   = data.get("email", "").strip()
    results = data.get("results", [])
    query   = data.get("query", "")
    summary = data.get("summary", {})

    if not email or not results:
        return jsonify(error="Email and results are required"), 400

    body_html = f"""
    <html>
    <head><style>
        body {{ font-family: Arial, sans-serif; }}
        h2 {{ color: #6c63ff; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .best {{ background-color: #d4edda; }}
    </style></head>
    <body>
        <h2>PriceScout Results for "{query}"</h2>
        <p><strong>Best Price:</strong> {summary.get('best_price', 0):,.0f} EGP at {summary.get('best_site', '?')}</p>
        <p><strong>Average Price:</strong> {summary.get('avg_price', 0):,.0f} EGP</p>
        <p><strong>Worst Price:</strong> {summary.get('worst_price', 0):,.0f} EGP at {summary.get('worst_site', '?')}</p>
        <table>
            <tr><th>Site</th><th>Product</th><th>Price (EGP)</th><th>Original</th><th>Rating</th><th>Reviews</th><th>Link</th></tr>
    """
    for r in results:
        rating_stars = "★" * int(round(r.get("rating", 0))) if r.get("rating") else "?"
        orig = (f"{r.get('currency')} {r.get('price'):.2f}"
                if r.get("price") and r.get("currency") else "—")
        link = r.get("product_url", "")
        body_html += f"""
            <tr class="{'best' if r == results[0] else ''}">
                <td>{r.get('site')}</td>
                <td>{r.get('product')}</td>
                <td>{r.get('price_egp'):,.0f}</td>
                <td>{orig}</td>
                <td>{rating_stars} {r.get('rating', '?')}</td>
                <td>{r.get('reviews', 0):,}</td>
                <td><a href="{link}">View</a></td>
            </tr>
        """
    body_html += "</table><p>Sent from PriceScout bot</p></body></html>"

    success = send_email(f"PriceScout Results: {query}", body_html, recipient=email)
    if success:
        return jsonify(success=True, message=f"Results sent to {email}")
    return jsonify(error="Failed to send email. Check server logs."), 500


# ── Visualize endpoint ────────────────────────────────────────────────────────
@app.route("/api/visualize", methods=["POST"])
@jwt_required()
def visualize():
    body    = request.get_json()
    results = body.get("results", [])
    query   = body.get("query", "Product")
    errors  = []

    if not results:
        return jsonify(error="No results provided"), 400

    image_b64    = ""
    chart_3d_url = ""

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        sorted_results = sorted(results, key=lambda r: r["price_egp"])
        sites  = [r["site"]      for r in sorted_results]
        prices = [r["price_egp"] for r in sorted_results]
        colors = [r.get("color", "#6c63ff") for r in sorted_results]

        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#0f172a")

        bars = ax.bar(sites, prices, color=colors, edgecolor="none", width=0.55)
        ax.bar(sites[:1], prices[:1], color=colors[:1], edgecolor="#10b981",
               linewidth=2, width=0.55)

        for bar, price in zip(bars, prices):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(prices) * 0.01,
                f"{price:,.0f}",
                ha="center", va="bottom", color="white",
                fontsize=9, fontweight="bold"
            )

        ax.set_title(f"Price Comparison — {query}", color="white",
                     fontsize=14, fontweight="bold", pad=16)
        ax.set_xlabel("Platform", color="#8b9db5", fontsize=11)
        ax.set_ylabel("Price (EGP)", color="#8b9db5", fontsize=11)
        ax.tick_params(colors="white", labelsize=10)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:,.0f}")
        )
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.yaxis.grid(True, color="#1c2433", linewidth=0.8)
        ax.set_axisbelow(True)

        best   = sorted_results[0]
        legend = mpatches.Patch(
            color="#10b981",
            label=f"Best: {best['site']} @ {best['price_egp']:,.0f} EGP"
        )
        ax.legend(handles=[legend], facecolor="#141c2e", edgecolor="#1c2433",
                  labelcolor="white", fontsize=10)

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        image_b64 = base64.b64encode(buf.read()).decode("utf-8")

    except ImportError as e:
        errors.append(f"matplotlib not installed: {e}")
    except Exception as e:
        errors.append(f"2D chart error: {e}")

    try:
        import plotly.graph_objects as go
        import pandas as pd

        data_list = [
            {
                "Site":      r["site"],
                "Product":   r.get("product", r["site"]),
                "Price_EGP": r["price_egp"],
                "Rating":    r["rating"],
            }
            for r in results
        ]

        df        = pd.DataFrame(data_list)
        sites_uniq = df["Site"].unique()
        site_to_x  = {site: i for i, site in enumerate(sites_uniq)}

        SITE_COLORS = {
            "Amazon": "#FF9900", "Jumia": "#E83030", "Noon": "#FECC00",
            "eBay": "#86B817", "Walmart": "#0071CE",
        }

        fig3d = go.Figure()
        for site in sites_uniq:
            sdf = df[df["Site"] == site]
            fig3d.add_trace(go.Scatter3d(
                x=[site_to_x[site]] * len(sdf),
                y=sdf["Price_EGP"],
                z=sdf["Rating"],
                mode="markers+text",
                name=site,
                text=sdf["Product"].apply(lambda x: x[:40]),
                textposition="top center",
                marker=dict(
                    size=10,
                    color=SITE_COLORS.get(site, "#6c63ff"),
                    opacity=0.9,
                    line=dict(width=1, color="rgba(255,255,255,0.3)")
                ),
                hovertemplate=(
                    f"<b>{site}</b><br>"
                    "Price: %{y:,.0f} EGP<br>"
                    "Rating: %{z}<extra></extra>"
                )
            ))

        fig3d.update_layout(
            title=dict(text=f"3D Price & Rating — {query}",
                       font=dict(color="white", size=16)),
            scene=dict(
                xaxis=dict(title="Platform",
                           tickvals=list(range(len(sites_uniq))),
                           ticktext=list(sites_uniq),
                           color="white", gridcolor="#1c2433",
                           backgroundcolor="#0b0f1a"),
                yaxis=dict(title="Price (EGP)", type="log", color="white",
                           gridcolor="#1c2433", backgroundcolor="#0b0f1a"),
                zaxis=dict(title="Rating (/ 5)", range=[0, 5.5], color="white",
                           gridcolor="#1c2433", backgroundcolor="#0b0f1a"),
                bgcolor="#0f172a",
            ),
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            font=dict(color="white", family="DM Sans, sans-serif"),
            legend=dict(bgcolor="rgba(20,28,46,0.8)", bordercolor="#1c2433",
                        borderwidth=1, font=dict(color="white")),
            margin=dict(l=0, r=0, b=0, t=48),
            height=700,
        )

        filename  = f"3d_{uuid.uuid4().hex[:12]}.html"
        save_path = os.path.join(CHARTS_DIR, filename)
        fig3d.write_html(save_path, include_plotlyjs="cdn")
        chart_3d_url = f"http://localhost:5000/api/charts/{filename}"

    except ImportError as e:
        errors.append(f"plotly/pandas not installed: {e}")
    except Exception as e:
        errors.append(f"3D chart error: {e}")

    return jsonify(image_b64=image_b64, chart_3d_url=chart_3d_url, errors=errors)


@app.route("/api/charts/<filename>")
def serve_chart(filename):
    return send_from_directory(CHARTS_DIR, filename)


if __name__ == "__main__":
    try:
        from telegram_bot import start_bot
        start_bot()
        print("Telegram bot started — search via your bot on Telegram!")
    except Exception as e:
        print(f"Telegram bot failed to start: {e}")

    app.run(debug=True, port=5000, use_reloader=False)