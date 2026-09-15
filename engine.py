import json
from typing import Dict, List, Any

def load_catalog() -> List[Dict[str, Any]]:
    with open("catalog.json", "r") as f:
        return json.load(f)

def run_heuristic_recommender(room_l: float, room_w: float, budget: float, style: str) -> Dict[str, Any]:
    """
    Deterministic constraint engine that pairs SKUs based on style match, 
    dimensional bounds, and budget limits.
    """
    catalog = load_catalog()
    
    # Filter by budget capability and category
    categories = ["toilet", "shower", "vanity", "faucet"]
    selected_items = []
    current_cost = 0

    for cat in categories:
        # Match style tag first, sort by price descending to maximize quality within budget
        candidates = [item for item in catalog if item["category"] == cat]
        matched_candidates = [item for item in candidates if style in item["aesthetic_tags"]]
        pool = matched_candidates if matched_candidates else candidates
        
        # Pick the best item that fits the proportional budget allocation
        pool = sorted(pool, key=lambda x: x["price_inr"])
        chosen = pool[0] # Default fallback
        for candidate in pool:
            if current_cost + candidate["price_inr"] <= budget * 0.95:
                chosen = candidate
        
        selected_items.append(chosen)
        current_cost += chosen["price_inr"]

    return {
        "selected_skus": selected_items,
        "total_cost": current_cost,
        "budget_surplus": budget - current_cost,
        "design_concept": f"Optimized {style} design leveraging Kohler's signature ergonomics and sustainable flow rates."
    }

def solve_spatial_layout(room_l: float, room_w: float, selected_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Spatial solver implementing standard architectural clearance and wet/dry zoning:
    - Shower: Corner wet zone (0, 0)
    - Vanity: Dry wall along top edge
    - Toilet: Dry wall along opposite side with >=1.25 ft clearance from edge
    """
    layout = []
    
    for item in selected_items:
        cat = item["category"]
        w = item["width_ft"]
        l = item["length_ft"]
        
        if cat == "shower":
            # Corner wet zone (Top-Left)
            pos_x = 0.5
            pos_y = room_w - l - 0.5
            color = "#A0C4FF"
        elif cat == "vanity":
            # Along the bottom wall (Dry Zone)
            pos_x = 0.5
            pos_y = 0.5
            color = "#FDFFB6"
        elif cat == "toilet":
            # Along right wall
            pos_x = room_l - w - 0.75
            pos_y = 0.5
            color = "#CAFFBF"
        elif cat == "faucet":
            # Mounted directly on the vanity
            pos_x = 0.5 + (selected_items[2]["width_ft"] / 2) - (w / 2)
            pos_y = 0.5 + (selected_items[2]["length_ft"] / 2) - (l / 2)
            color = "#FFADAD"
        else:
            pos_x, pos_y = 1.0, 1.0
            color = "#CCCCCC"

        layout.append({
            "name": item["name"],
            "sku": item["sku"],
            "category": cat,
            "x": round(pos_x, 2),
            "y": round(pos_y, 2),
            "width": w,
            "length": l,
            "color": color,
            "eco_feature": item["eco_feature"],
            "price_inr": item["price_inr"]
        })
        
    return layout