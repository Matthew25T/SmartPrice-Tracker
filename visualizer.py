"""
Visualizer
==========
Creates professional charts from scraped product data.
Handles mixed currencies by normalizing to USD where possible.
"""

import matplotlib
matplotlib.use("TkAgg")   # use TkAgg for desktop; change to "Agg" for headless/CI

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np
import logging
import datetime
import os

logger = logging.getLogger(__name__)

# Approximate exchange rates relative to USD (update periodically)
EXCHANGE_TO_USD = {
    "USD": 1.0,
    "EGP": 1 / 49.0,   # 1 EGP ≈ 0.020 USD  (as of mid-2025)
}

SITE_COLORS = {
    "Amazon":  "#FF9900",
    "Jumia":   "#E83030",
    "Noon":    "#FECC00",
    "eBay":    "#86B817",
    "Newegg":  "#FF6600",
    "BestBuy": "#0046BE",
    "Walmart": "#0071CE",
}

def normalize_price(row: dict) -> float:
    """Convert any currency price to USD equivalent."""
    currency = row.get("Currency", "USD")
    price    = row.get("Price", 0.0) or 0.0
    rate     = EXCHANGE_TO_USD.get(currency, 1.0)
    return round(price * rate, 2)


def create_visualizations(data_list: list[dict], search_term: str) -> None:
    if not data_list:
        logger.warning("No data to visualize.")
        return

    df = pd.DataFrame(data_list)

    # Add normalized price column
    df["Price_USD"] = df.apply(normalize_price, axis=1)
    df["Has_Rating"] = df["Rating"].notna()
    df["Rating"] = df["Rating"].fillna(0)

    # ── Figure setup ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(18, 12), facecolor="#1a1a2e")
    fig.suptitle(
        f'Price Comparison: "{search_term}"',
        fontsize=20, fontweight="bold", color="white",
        y=0.98
    )

    gs = gridspec.GridSpec(
        2, 3,
        figure=fig,
        hspace=0.45,
        wspace=0.38,
        left=0.06, right=0.97,
        top=0.91, bottom=0.08,
    )

    ax_bar    = fig.add_subplot(gs[0, :2])   # top-left wide: bar chart
    ax_rating = fig.add_subplot(gs[0, 2])    # top-right: rating chart
    ax_table  = fig.add_subplot(gs[1, :])    # bottom: summary table

    _style_axes([ax_bar, ax_rating, ax_table])

    # ── 1. Bar Chart: Price per Site ──────────────────────────────────────────
    sites  = df["Site"].tolist()
    prices = df["Price_USD"].tolist()
    colors = [SITE_COLORS.get(s, "#888888") for s in sites]
    bars   = ax_bar.bar(sites, prices, color=colors, edgecolor="white", linewidth=0.5, width=0.55)

    for bar, price, row in zip(bars, prices, data_list):
        currency = row.get("Currency", "USD")
        orig     = row.get("Price", 0)
        label    = f"${price:,.2f}"
        if currency != "USD":
            label += f"\n({currency} {orig:,.0f})"
        ax_bar.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(prices) * 0.01,
            label,
            ha="center", va="bottom",
            fontsize=8.5, color="white", fontweight="bold"
        )

    min_idx = prices.index(min(prices))
    ax_bar.patches[min_idx].set_edgecolor("#00FF88")
    ax_bar.patches[min_idx].set_linewidth(3)

    ax_bar.set_title("Price by Site (USD equivalent)", color="white", fontsize=13, pad=10)
    ax_bar.set_ylabel("Price (USD)", color="#aaaaaa", fontsize=10)
    ax_bar.tick_params(colors="white", labelsize=9)
    ax_bar.set_ylim(0, max(prices) * 1.22)

    best_site = df.loc[df["Price_USD"].idxmin(), "Site"]
    ax_bar.annotate(
        f"✓ Best price: {best_site}",
        xy=(min_idx, min(prices)),
        xytext=(min_idx, min(prices) + max(prices) * 0.08),
        ha="center", color="#00FF88", fontsize=9, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#00FF88", lw=1.5),
    )

    # ── 2. Rating Chart ───────────────────────────────────────────────────────
    rated_df = df[df["Has_Rating"]].copy()

    if rated_df.empty:
        ax_rating.text(
            0.5, 0.5, "No ratings\navailable",
            ha="center", va="center", color="#888888",
            fontsize=11, transform=ax_rating.transAxes
        )
    else:
        r_sites  = rated_df["Site"].tolist()
        r_values = rated_df["Rating"].tolist()
        r_colors = [SITE_COLORS.get(s, "#888888") for s in r_sites]
        r_bars   = ax_rating.barh(r_sites, r_values, color=r_colors, edgecolor="white", linewidth=0.5)

        for bar, val in zip(r_bars, r_values):
            ax_rating.text(
                val + 0.05, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}★", va="center", ha="left",
                color="white", fontsize=9, fontweight="bold"
            )

        ax_rating.set_xlim(0, 5.5)
        ax_rating.axvline(x=5, color="#555555", linestyle="--", linewidth=0.8)
        ax_rating.set_xlabel("Rating / 5", color="#aaaaaa", fontsize=9)
        ax_rating.tick_params(colors="white", labelsize=9)

    ax_rating.set_title("Customer Rating", color="white", fontsize=13, pad=10)

    # ── 3. Summary Table ──────────────────────────────────────────────────────
    ax_table.axis("off")

    table_data = []
    for _, row in df.iterrows():
        reviews_str = f"{int(row['Reviews']):,}" if row.get("Reviews") else "N/A"
        rating_str  = f"{row['Rating']:.1f} ★" if row["Has_Rating"] else "N/A"
        orig_price  = f"{row['Currency']} {row['Price']:,.2f}"
        usd_price   = f"$ {row['Price_USD']:,.2f}"
        table_data.append([
            row["Site"],
            orig_price,
            usd_price,
            rating_str,
            reviews_str,
            row["Product"][:55] + ("…" if len(row["Product"]) > 55 else ""),
        ])

    columns = ["Site", "Original Price", "≈ USD", "Rating", "Reviews", "Product"]
    table = ax_table.table(
        cellText=table_data,
        colLabels=columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 1.7)

    # Style header
    for col_idx in range(len(columns)):
        cell = table[0, col_idx]
        cell.set_facecolor("#3a3a5c")
        cell.set_text_props(color="white", fontweight="bold")

    # Style data rows
    for row_idx, (_, row) in enumerate(df.iterrows(), start=1):
        site_color = SITE_COLORS.get(row["Site"], "#888888")
        for col_idx in range(len(columns)):
            cell = table[row_idx, col_idx]
            cell.set_facecolor("#12122a" if row_idx % 2 == 0 else "#1e1e3a")
            cell.set_text_props(color="white")
            if col_idx == 0:
                cell.set_facecolor(site_color + "55")  # tinted site color
                cell.set_text_props(color="white", fontweight="bold")

    ax_table.set_title("Full Results Summary", color="white", fontsize=13, pad=8)

    # ── Footer ────────────────────────────────────────────────────────────────
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    fig.text(
        0.99, 0.01,
        f"Generated {ts} | Exchange rates approximate",
        ha="right", va="bottom", color="#555555", fontsize=7
    )

    # ── Save & Show ───────────────────────────────────────────────────────────
    out_path = f"results_{search_term.replace(' ', '_')}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    logger.info(f"Chart saved to: {os.path.abspath(out_path)}")
    print(f"\n📊 Chart saved → {out_path}")
    plt.show()


# ── Helper ────────────────────────────────────────────────────────────────────
def _style_axes(axes: list):
    for ax in axes:
        ax.set_facecolor("#12122a")
        ax.spines["bottom"].set_color("#444466")
        ax.spines["left"].set_color("#444466")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(colors="white")
        ax.yaxis.label.set_color("#aaaaaa")
        ax.xaxis.label.set_color("#aaaaaa")