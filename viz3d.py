"""
3D Visualization using Plotly: X = Site, Y = Price (EGP), Z = Rating.
"""
import plotly.graph_objects as go
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def draw_3d_scatter(data_list: list, search_term: str, save_path: str = "price_3d.html"):
    """Plotly 3D: sites on x-axis (categorical → numeric), price on y, rating on z."""
    if not data_list:
        logger.warning("No data for 3D plot.")
        return

    df = pd.DataFrame(data_list)
    if "Price_EGP" not in df.columns:
        logger.error("Price_EGP missing – run currency normalization first.")
        return

    # Map sites to numeric x positions
    sites = df["Site"].unique()
    site_to_x = {site: i for i, site in enumerate(sites)}

    fig = go.Figure()

    for site in sites:
        site_df = df[df["Site"] == site]
        fig.add_trace(go.Scatter3d(
            x=[site_to_x[site]] * len(site_df),
            y=site_df["Price_EGP"],
            z=site_df["Rating"],
            mode="markers+text",
            name=site,
            text=site_df["Product"].apply(lambda x: x[:40]),
            textposition="top center",
            marker=dict(size=8, opacity=0.8),
            hovertemplate=f"<b>{site}</b><br>Price: %{{y:.2f}} EGP<br>Rating: %{{z}}<extra></extra>"
        ))

    fig.update_layout(
        title=f"3D Price & Rating Comparison – {search_term}",
        scene=dict(
            xaxis=dict(title="Website", tickvals=list(range(len(sites))), ticktext=list(sites)),
            yaxis=dict(title="Price (EGP)", type="log"),
            zaxis=dict(title="Rating (out of 5)", range=[0, 5.5]),
            bgcolor="#0f172a"
        ),
        paper_bgcolor="#0f172a",
        font=dict(color="white"),
        margin=dict(l=0, r=0, b=0, t=40),
        height=700
    )
    fig.write_html(save_path)
    logger.info(f"3D plot saved to {save_path}")
    fig.show()