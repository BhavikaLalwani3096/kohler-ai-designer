import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from engine import run_heuristic_recommender, solve_spatial_layout

st.set_page_config(page_title="KOHLER AI Bathroom Designer", layout="wide")

st.title("KOHLER AI Bathroom Designer & Planner")
st.caption("AI Research Lab - Automated Specification & Spatial Clearance Engine")

# Sidebar Configuration
st.sidebar.header("Design Parameters")
room_l = st.sidebar.slider("Room Length (ft)", min_value=6.0, max_value=18.0, value=10.0, step=0.5)
room_w = st.sidebar.slider("Room Width (ft)", min_value=5.0, max_value=14.0, value=8.0, step=0.5)
budget = st.sidebar.number_input("Budget (₹ INR)", min_value=150000, max_value=2500000, value=650000, step=25000)
theme = st.sidebar.selectbox("Aesthetic Collection", ["Minimalist Modern", "Classic Luxury", "Japanese Zen"])

# Execution
res = run_heuristic_recommender(room_l, room_w, budget, theme)
layout_fixtures = solve_spatial_layout(room_l, room_w, res["selected_skus"])

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("2D Architectural Floor Plan")
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlim(0, room_l)
    ax.set_ylim(0, room_w)
    ax.set_aspect('equal')
    ax.set_facecolor('#F8F9FA')

    # Draw Room Perimeter
    ax.add_patch(patches.Rectangle((0, 0), room_l, room_w, fill=False, edgecolor='#212529', linewidth=3))

    # Wet Zone Boundary Shading
    ax.add_patch(patches.Rectangle((0, room_w - 4.5), 4.5, 4.5, facecolor='#E3F2FD', edgecolor='none', alpha=0.5, label='Dedicated Wet Zone'))

    # Draw Fixtures
    for fix in layout_fixtures:
        # Fixture bounding box
        rect = patches.Rectangle(
            (fix["x"], fix["y"]), 
            fix["width"], 
            fix["length"], 
            facecolor=fix["color"], 
            edgecolor='#333333', 
            linewidth=1.5,
            label=fix["category"].capitalize()
        )
        ax.add_patch(rect)
        # Fixture Label
        ax.text(
            fix["x"] + fix["width"] / 2, 
            fix["y"] + fix["length"] / 2, 
            fix["name"].split()[0], 
            ha='center', 
            va='center', 
            fontsize=8, 
            fontweight='bold'
        )

    ax.set_title(f"Layout Geometry: {room_l} ft × {room_w} ft | {theme}", fontsize=11, pad=10)
    ax.set_xlabel("Length (ft)")
    ax.set_ylabel("Width (ft)")
    ax.grid(color='#E0E0E0', linestyle='--', linewidth=0.5)
    
    # Clean up legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper right', bbox_to_anchor=(1.35, 1.0))

    st.pyplot(fig)

with col2:
    st.subheader("Curated Bill of Materials (BOM)")
    st.markdown(f"**Design Rationale:** {res['design_concept']}")
    
    for fix in layout_fixtures:
        with st.expander(f"{fix['name']} — ₹{fix['price_inr']:,}"):
            st.write(f"**SKU:** `{fix['sku']}`")
            st.write(f"**Dimensions:** {fix['width']} ft × {fix['length']} ft")
            st.write(f"**Eco & Sustainability:** {fix['eco_feature']}")

    st.markdown("---")
    st.metric("Total Expenditure", f"₹{res['total_cost']:,}", delta=f"Surplus: ₹{res['budget_surplus']:,}")
    if res['budget_surplus'] >= 0:
        st.success("Project meets physical clearances and budgetary constraints.")
    else:
        st.error("Budget exceeded! Please adjust parameters.")