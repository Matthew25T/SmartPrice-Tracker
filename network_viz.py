"""
NetworkX visualization: Each site is a node. For each product, we show a connected
edge from site to virtual product node, labeled with price.
"""
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import logging

logger = logging.getLogger(__name__)

SITE_COLORS = {
    "Amazon": "#FF9900", "Jumia": "#E83030", "Noon": "#FECC00",
    "eBay": "#86B817", "Newegg": "#FF6600", "BestBuy": "#0046BE",
    "Walmart": "#0071CE"
}

def draw_price_network(data_list: list, search_term: str, save_path: str = "price_network.png"):
    """Draw a bipartite graph: sites (left) → product nodes (right) with price labels."""
    if not data_list:
        logger.warning("No data for network graph.")
        return

    df = pd.DataFrame(data_list)
    # Ensure we have Price_EGP (normalized)
    if "Price_EGP" not in df.columns:
        logger.error("Price_EGP missing – run currency normalization first.")
        return

    G = nx.Graph()
    # Add center node (search term)
    G.add_node(search_term, layer=0, color="#1e40af", size=3000)

    # Add site nodes
    for site in df["Site"].unique():
        G.add_node(site, layer=1, color=SITE_COLORS.get(site, "#888888"), size=2000)

    # Add product nodes (one per result)
    for idx, row in df.iterrows():
        product_node = f"{row['Product'][:30]}…"
        G.add_node(product_node, layer=2, color="#e0e7ff", size=1000)
        G.add_edge(row["Site"], product_node, label=f"{row['Price_EGP']:.0f} EGP")
        G.add_edge(search_term, row["Site"], label="")

    # Positioning: hierarchical layers
    pos = {}
    # Search term at center
    pos[search_term] = (0, 0)
    # Sites in a circle around center
    sites = [n for n, d in G.nodes(data=True) if d.get("layer") == 1]
    for i, s in enumerate(sites):
        angle = 2 * 3.14159 * i / len(sites)
        pos[s] = (2.5 * cos(angle), 2.5 * sin(angle))
    # Product nodes around their respective sites
    products = [n for n, d in G.nodes(data=True) if d.get("layer") == 2]
    for p in products:
        neighbor = list(G.neighbors(p))[0]  # the site
        sx, sy = pos[neighbor]
        # random offset to avoid overlap
        offset = products.index(p) * 0.3
        pos[p] = (sx + 1.2, sy + offset - 1)

    # Draw
    plt.figure(figsize=(14, 10), facecolor="#0f172a")
    ax = plt.gca()
    ax.set_facecolor("#0f172a")

    node_colors = [G.nodes[n].get("color", "#94a3b8") for n in G.nodes()]
    node_sizes = [G.nodes[n].get("size", 800) for n in G.nodes()]

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax, alpha=0.9)
    nx.draw_networkx_edges(G, pos, edge_color="#334155", width=1.5, ax=ax, alpha=0.6)

    # Labels
    nx.draw_networkx_labels(G, pos, font_size=8, font_color="white", font_weight="bold", ax=ax)

    # Edge labels (prices)
    edge_labels = {(u, v): d["label"] for u, v, d in G.edges(data=True) if d.get("label")}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7, font_color="#94a3b8", ax=ax)

    ax.set_title(f"Price Network – {search_term}", color="white", fontsize=14, pad=20)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="#0f172a")
    plt.show()
    logger.info(f"Network graph saved to {save_path}")

from math import sin, cos