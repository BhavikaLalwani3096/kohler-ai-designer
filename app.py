import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from engine import run_intelligent_recommender, solve_spatial_layout, generate_ai_design_critique

st.set_page_config(page_title="KOHLER AI Space & Fixture Planner", layout="wide")

st.title("KOHLER AI Bathroom Designer & Space Planner")
st.caption("AI Research Lab — Spatial Clearance, Dynamic Circulation & Specification Engine")

# --- Sidebar Controls ---
st.sidebar.header("1. Room Geometry")
room_l = st.sidebar.slider("Room Length (ft)", min_value=6.0, max_value=20.0, value=12.0, step=0.5)
room_w = st.sidebar.slider("Room Width (ft)", min_value=5.0, max_value=16.0, value=8.5, step=0.5)
door_wall_choice = st.sidebar.selectbox("Entrance Door Wall", [
    "South (Bottom Wall)", 
    "North (Top Wall)", 
    "East (Right Wall)", 
    "West (Left Wall)"
])
door_wall = door_wall_choice.split()[0]

st.sidebar.header("2. Budget & Theme")
budget = st.sidebar.number_input(
    "Target Budget (₹ INR)", 
    min_value=50000, 
    max_value=2500000, 
    value=400000, 
    step=25000
)
theme = st.sidebar.selectbox("Aesthetic Style", ["Minimalist Modern", "Japanese Zen", "Classic Luxury"])

# Run Instant Deterministic Solver
res = run_intelligent_recommender(room_l, room_w, budget, theme)
layout_data = solve_spatial_layout(room_l, room_w, res["selected_skus"], door_wall=door_wall)
fixtures = layout_data["fixtures"]
door = layout_data["door"]

col1, col2 = st.columns([3, 2])

# --- Column 1: 2D Interactive Plan ---
with col1:
    st.subheader("2D Architectural Floor Plan")
    
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    ax.set_xlim(-0.8, room_l + 0.8)
    ax.set_ylim(-0.8, room_w + 0.8)
    ax.set_aspect('equal')
    ax.set_facecolor('#FAFAFA')

    # Room Perimeter
    ax.add_patch(patches.Rectangle((0, 0), room_l, room_w, fill=False, edgecolor='#263238', linewidth=3))

    # Door Threshold
    door_rect = patches.Rectangle(
        (door["x"], door["y"]), 
        door["dx"], 
        door["dy"], 
        facecolor='#EF5350', 
        edgecolor='#C62828', 
        linewidth=1.0, 
        alpha=0.85
    )
    ax.add_patch(door_rect)
    if door["wall"] == "North":
        arc = patches.Arc((door["x"], room_w), 2 * door["dx"], 2 * door["dx"], angle=0, theta1=270, theta2=360, color="#C62828", linestyle="--", linewidth=1.2)
        ax.add_patch(arc)
        ax.plot([door["x"], door["x"]], [room_w, room_w - door["dx"]], color="#C62828", linewidth=2.0)
        ax.text(door["x"] + door["dx"] / 2, room_w - 0.35, "DOOR", fontsize=6, color="#C62828", fontweight='bold', ha='center')
    elif door["wall"] == "South":
        arc = patches.Arc((door["x"], 0), 2 * door["dx"], 2 * door["dx"], angle=0, theta1=0, theta2=90, color="#C62828", linestyle="--", linewidth=1.2)
        ax.add_patch(arc)
        ax.plot([door["x"], door["x"]], [0, door["dx"]], color="#C62828", linewidth=2.0)
        ax.text(door["x"] + door["dx"] / 2, 0.35, "DOOR", fontsize=6, color="#C62828", fontweight='bold', ha='center')
    elif door["wall"] == "East":
        arc = patches.Arc((room_l, door["y"]), 2 * door["dy"], 2 * door["dy"], angle=0, theta1=90, theta2=180, color="#C62828", linestyle="--", linewidth=1.2)
        ax.add_patch(arc)
        ax.plot([room_l, room_l - door["dy"]], [door["y"], door["y"]], color="#C62828", linewidth=2.0)
        ax.text(room_l - 0.35, door["y"] + door["dy"] / 2, "DOOR", fontsize=6, color="#C62828", fontweight='bold', va='center', rotation=90)
    else:  # West
        arc = patches.Arc((0, door["y"]), 2 * door["dy"], 2 * door["dy"], angle=0, theta1=0, theta2=90, color="#C62828", linestyle="--", linewidth=1.2)
        ax.add_patch(arc)
        ax.plot([0, door["dy"]], [door["y"], door["y"]], color="#C62828", linewidth=2.0)
        ax.text(0.35, door["y"] + door["dy"] / 2, "DOOR", fontsize=6, color="#C62828", fontweight='bold', va='center', rotation=90)

    # Render Fixtures
    for fix in fixtures:
        rect = patches.Rectangle(
            (fix["x"], fix["y"]), 
            fix["width"], 
            fix["length"], 
            facecolor=fix["color"], 
            edgecolor='#37474F', 
            linewidth=1.6
        )
        ax.add_patch(rect)
        cat_title = fix["item_data"]["category"].upper()
        dim_label = f"{fix['width']}'×{fix['length']}'"
        ax.text(
            fix["x"] + fix["width"] / 2, 
            fix["y"] + fix["length"] / 2, 
            f"{cat_title}\n{dim_label}", 
            ha='center', 
            va='center', 
            fontsize=7, 
            fontweight='bold',
            color='#212121',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFFFFF', edgecolor='#B0BEC5', alpha=0.9)
        )

        if fix.get("has_faucet"):
            faucet_dot = patches.Circle(
                (fix["x"] + fix["width"] / 2, fix["y"] + fix["length"] / 2 + 0.3), 
                0.14, 
                facecolor='#D32F2F', 
                edgecolor='#000000', 
                linewidth=0.8
            )
            ax.add_patch(faucet_dot)

    ax.set_title(f"Geometry: {room_l} ft × {room_w} ft ({res['room_area_sqft']} sq ft) | Entrance: {door_wall} Wall", fontsize=10, pad=10, fontweight='bold')
    ax.set_xlabel("Width (Feet)", fontsize=8)
    ax.set_ylabel("Depth (Feet)", fontsize=8)
    ax.grid(color='#E0E0E0', linestyle=':', linewidth=0.6)

    st.pyplot(fig)

# --- Column 2: Full Product Specification & BOM ---
with col2:
    st.subheader("Selected Kohler Bill of Materials")
    st.info(f"**AI Concept:** {res['design_concept']}")

    # Generative AI Architectural Consultant Layer
    st.markdown("### 🧠 AI Architectural Consultant")
    
    if st.button("Generate Expert Design & Material Rationale", type="primary"):
        with st.spinner("Consulting Kohler Architectural Knowledge Base..."):
            ai_eval = generate_ai_design_critique(
                room_l=room_l,
                room_w=room_w,
                area=res["room_area_sqft"],
                budget=budget,
                style=theme,
                door_wall=door_wall,
                selected_skus=res["selected_skus"],
                total_cost=res["total_cost"]
            )
            st.session_state["ai_critique"] = ai_eval

    if "ai_critique" in st.session_state:
        status = st.session_state["ai_critique"]["status"]
        if status == "live_ai":
            st.success("⚡ Live Gemini AI Architectural Rationale Generated")
        else:
            st.caption("ℹ️ Running in localized architectural knowledge mode")
            
        st.markdown(st.session_state["ai_critique"]["critique"])

    # Iterate through chosen items
    for idx, item in enumerate(res["selected_skus"], start=1):
        tier_label = item.get("tier", "standard").capitalize()
        with st.expander(f"{idx}. {item['name']} — ₹{item['price_inr']:,}", expanded=False):
            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.caption(f"**SKU:** `{item['sku']}`")
                st.caption(f"**Category:** {item['category'].capitalize()} ({tier_label} Tier)")
            with col_b:
                st.caption(f"**Footprint:** {item['width_ft']} ft × {item['length_ft']} ft")
            st.write(f"🌿 **Eco Feature:** {item['eco_feature']}")

    st.markdown("---")

    # Budget Summary Card
    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric("Total Bundle Cost", f"₹{res['total_cost']:,}")
    with metric_col2:
        if res['budget_surplus'] >= 0:
            st.metric("Budget Savings", f"₹{res['budget_surplus']:,}", delta_color="normal")
            st.success("✅ Fully complies with space constraints & budget.")
        else:
            st.metric("Budget Deficit", f"-₹{abs(res['budget_surplus']):,}", delta_color="inverse")
            st.warning("⚠️ Target budget too tight for selected tier. Increase budget slightly.")

    # --- Architectural Spec Sheet Downloader (.md) ---
    st.markdown("---")
    critique_text = st.session_state.get("ai_critique", {}).get("critique", "AI Rationale not generated yet.")

    spec_summary = f"""# KOHLER AI BATHROOM SPECIFICATION SHEET
Room Geometry: {room_l} ft x {room_w} ft ({res['room_area_sqft']} sq ft)
Room Typology: {res.get('room_type', 'Standard Bath')}
Entrance: {door_wall} Wall | Aesthetic Style: {theme}
Target Budget: INR {budget:,} | Total Cost: INR {res['total_cost']:,} | Reserve: INR {res['budget_surplus']:,}

## BILL OF MATERIALS (BOM)
"""
    for item in res["selected_skus"]:
        spec_summary += f"- {item['name']} | SKU: {item['sku']} | Price: INR {item['price_inr']:,} | Footprint: {item['width_ft']}' x {item['length_ft']}' | Eco Feature: {item['eco_feature']}\n"

    spec_summary += f"\n## AI ARCHITECTURAL CRITIQUE & SPECIFICATION\n{critique_text}\n"

    st.download_button(
        label="📄 Download Architectural Specification Sheet (.md)",
        data=spec_summary,
        file_name=f"Kohler_Spec_{theme.replace(' ', '_')}_{int(room_l)}x{int(room_w)}.md",
        mime="text/markdown",
        use_container_width=True
    )