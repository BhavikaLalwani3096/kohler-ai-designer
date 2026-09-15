import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from engine import run_intelligent_recommender, solve_spatial_layout

st.set_page_config(page_title="KOHLER AI Space & Fixture Planner", layout="wide")

st.title("KOHLER AI Bathroom Designer & Space Planner")
st.caption("AI Research Lab - Spatial Clearance, Circulation & Specification Engine")

# Sidebar Controls
st.sidebar.header("1. Room Geometry")
room_l = st.sidebar.slider("Room Length (ft)", min_value=7.0, max_value=20.0, value=12.0, step=0.5)
room_w = st.sidebar.slider("Room Width (ft)", min_value=6.0, max_value=16.0, value=10.0, step=0.5)
door_wall = st.sidebar.selectbox("Entrance Door Location", ["South (Bottom Wall)", "North (Top Wall)", "East (Right Wall)", "West (Left Wall)"])
clean_door_wall = door_wall.split()[0]

st.sidebar.header("2. Budget & Style")
budget = st.sidebar.number_input("Budget (INR)", min_value=150000, max_value=2500000, value=950000, step=50000)
theme = st.sidebar.selectbox("Aesthetic Collection", ["Minimalist Modern", "Classic Luxury", "Japanese Zen"])

# Solve recommendation and layout
engine_res = run_intelligent_recommender(room_l, room_w, budget, theme)
layout_res = solve_spatial_layout(room_l, room_w, engine_res["selected_skus"], door_wall=clean_door_wall)
fixtures = layout_res["fixtures"]
door = layout_res["door"]

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Interactive 2D Architectural Layout")
    
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.set_xlim(-0.5, room_l + 0.5)
    ax.set_ylim(-0.5, room_w + 0.5)
    ax.set_aspect('equal')
    ax.set_facecolor('#FDFDFD')

    # Room Perimeter
    ax.add_patch(patches.Rectangle((0, 0), room_l, room_w, fill=False, edgecolor='#1E1E24', linewidth=3.5))

    # Wet Zone Shading (Dedicated splash perimeter)
    ax.add_patch(patches.Rectangle((0, room_w - 5.0), 5.0, 5.0, facecolor='#E0F2FE', edgecolor='none', alpha=0.45))
    ax.text(0.5, room_w - 0.5, "WET ZONE", fontsize=8, color="#0284C7", fontweight='bold')

    # Draw Entrance Door Clearance Area
    ax.add_patch(patches.Rectangle((door["x"], door["y"]), door["dx"], door["dy"], facecolor='#EF4444', edgecolor='#B91C1C', linewidth=1.5, hatch='//', alpha=0.6))
    ax.text(door["x"] + (door["dx"] / 2), door["y"] + (door["dy"] / 2), "DOOR ACCESS (KEEP CLEAR)", fontsize=7, color="#FFFFFF", fontweight='bold', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', facecolor='#B91C1C', edgecolor='none'))

    # Render Fixtures
    for fix in fixtures:
        # Fixture Bounding Box
        rect = patches.Rectangle(
            (fix["x"], fix["y"]), 
            fix["width"], 
            fix["length"], 
            facecolor=fix["color"], 
            edgecolor='#2B2D42', 
            linewidth=1.8
        )
        ax.add_patch(rect)
        
        # Display clear label centered with background patch
        label_text = f"{fix['category'].upper()}\n{fix['width']}'×{fix['length']}'"
        ax.text(
            fix["x"] + fix["width"] / 2, 
            fix["y"] + fix["length"] / 2, 
            label_text, 
            ha='center', 
            va='center', 
            fontsize=7.5, 
            fontweight='bold',
            color='#1E1E24',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFFFFF', edgecolor='#A0AAB2', alpha=0.85)
        )

        # Render Faucet marker on Vanity without clashing
        if fix.get("has_faucet"):
            faucet_circle = patches.Circle(
                (fix["x"] + fix["width"] / 2, fix["y"] + fix["length"] / 2 + 0.35),
                0.18,
                facecolor='#D90429',
                edgecolor='#000000',
                linewidth=1.0
            )
            ax.add_patch(faucet_circle)

    ax.set_title(f"Plan View: {room_l} ft × {room_w} ft ({engine_res['room_area_sqft']} sq.ft) | Theme: {theme}", fontsize=11, pad=12, fontweight='bold')
    ax.set_xlabel("Width (Feet)", fontsize=9)
    ax.set_ylabel("Depth (Feet)", fontsize=9)
    ax.grid(color='#E5E7EB', linestyle=':', linewidth=0.7)

    st.pyplot(fig)

with col2:
    st.subheader("Curated Specification & BOM")
    st.info(f"**AI Space Rationale:** {engine_res['design_concept']}")
    
    for fix in fixtures:
        with st.expander(f"● {fix['name']} — ₹{fix['price_inr']:,}"):
            st.write(f"**Category:** {fix['category'].capitalize()}")
            st.write(f"**Footprint:** {fix['width']} ft × {fix['length']} ft")
            st.write(f"**Eco Credentials:** {fix['eco_feature']}")
            if fix.get("has_faucet"):
                st.write(f"**Fitted Faucet:** {fix['faucet_name']}")

    st.markdown("---")
    st.metric("Total Investment", f"₹{engine_res['total_cost']:,}", delta=f"Budget Reserve: ₹{engine_res['budget_surplus']:,}")

    if engine_res['budget_surplus'] >= 0:
        st.success("✅ Design complies with plumbing zoning, clearance corridors, and budget bounds.")
    else:
        st.error("⚠️ Budget exceeded! Expand budget or choose a compact configuration.")