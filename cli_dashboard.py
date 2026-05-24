"""
CLI dashboard: best price, worst price, average price, best value recommendation.
"""
import pandas as pd
import numpy as np

def show_dashboard(data_list: list, search_term: str):
    """Print a formatted table with statistics."""
    if not data_list:
        print("No data to display.")
        return

    df = pd.DataFrame(data_list)
    if "Price_EGP" not in df.columns:
        print("Price_EGP missing – run currency normalization first.")
        return

    print("\n" + "=" * 60)
    print(f"  📊 DASHBOARD: {search_term}")
    print("=" * 60)

    best_idx = df["Price_EGP"].idxmin()
    worst_idx = df["Price_EGP"].idxmax()
    avg_price = df["Price_EGP"].mean()
    median_price = df["Price_EGP"].median()

    print(f"\n  🏆 BEST PRICE: {df.loc[best_idx, 'Price_EGP']:.2f} EGP at {df.loc[best_idx, 'Site']}")
    print(f"  💀 WORST PRICE: {df.loc[worst_idx, 'Price_EGP']:.2f} EGP at {df.loc[worst_idx, 'Site']}")
    print(f"  📈 AVERAGE PRICE: {avg_price:.2f} EGP")
    print(f"  📊 MEDIAN PRICE: {median_price:.2f} EGP")

    # Best value (price per rating, if rating > 0)
    rated = df[df["Rating"] > 0].copy()
    if not rated.empty:
        rated["Value_Score"] = rated["Price_EGP"] / rated["Rating"]
        best_value_idx = rated["Value_Score"].idxmin()
        print(f"  💎 BEST VALUE (lowest price per rating star): {rated.loc[best_value_idx, 'Site']} "
              f"({rated.loc[best_value_idx, 'Price_EGP']:.2f} EGP for {rated.loc[best_value_idx, 'Rating']}★)")

    print("\n  SITE BREAKDOWN:")
    for site in df["Site"].unique():
        site_df = df[df["Site"] == site]
        print(f"    • {site}: {len(site_df)} product(s) | "
              f"Price range: {site_df['Price_EGP'].min():.2f} – {site_df['Price_EGP'].max():.2f} EGP")

    print("=" * 60 + "\n")

    # Also save to CSV/Excel if user wants
    df.to_csv(f"results_{search_term.replace(' ', '_')}.csv", index=False)
    print(f"✅ Results exported to CSV: results_{search_term.replace(' ', '_')}.csv")