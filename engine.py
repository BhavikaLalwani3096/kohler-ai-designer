import json
from typing import Dict, List, Any

def load_catalog() -> List[Dict[str, Any]]:
    with open("catalog.json", "r") as f:
        return json.load(f)

def run_intelligent_recommender(room_l: float, room_w: float, budget: float, style: str) -> Dict[str, Any]:
    catalog = load_catalog()
    area = room_l * room_w
    
    # Base requirements
    categories_to_pick = ["toilet", "shower", "vanity", "faucet"]
    
    # Automatically add luxury fixtures if room size and budget allow
    if area >= 75.0 and budget >= 500000:
        categories_to_pick.append("bathtub")
    if area >= 60.0:
        categories_to_pick.append("accessory")
        
    selected_items = []
    current_cost = 0

    for cat in categories_to_pick:
        # Large rooms get double vanities if affordable
        candidates = [item for item in catalog if item["category"] == cat]
        if cat == "vanity" and area >= 80.0:
            double_vans = [c for c in candidates if "Double" in c["name"]]
            if double_vans:
                candidates = double_vans
                
        # Filter by aesthetic preference
        matched = [item for item in candidates if style in item["aesthetic_tags"]]
        pool = matched if matched else candidates
        
        # Pick highest quality candidate that fits under remaining budget
        pool = sorted(pool, key=lambda x: x["price_inr"], reverse=True)
        chosen = pool[-1]  # Default to least expensive fallback
        for candidate in pool:
            if current_cost + candidate["price_inr"] <= budget * 0.98:
                chosen = candidate
                break
                
        selected_items.append(chosen)
        current_cost += chosen["price_inr"]

    return {
        "selected_skus": selected_items,
        "total_cost": current_cost,
        "budget_surplus": budget - current_cost,
        "room_area_sqft": round(area, 1),
        "design_concept": f"Curated {style} concept scaled for {round(area, 1)} sq ft. Balances wet/dry circulation corridors, signature Kohler fixtures, and water conservation."
    }

def solve_spatial_layout(room_l: float, room_w: float, selected_items: List[Dict[str, Any]], door_wall: str = "South") -> Dict[str, Any]:
    """
    Arranges bathroom zones to avoid door clearance:
    - Door clearance reserve: 3.0 ft swing arc at selected door wall
    - Wet Zone: Dedicated corner for shower and tub
    - Dry Zone: Perimeter distribution for vanity and toilet
    """
    layout = []
    faucet_item = next((i for i in selected_items if i["category"] == "faucet"), None)
    
    # 1. Place Shower (Always in Top-Left / North-West corner if door is South/East)
    shower = next((i for i in selected_items if i["category"] == "shower"), None)
    if shower:
        layout.append({
            "name": shower["name"],
            "sku": shower["sku"],
            "category": "shower",
            "x": 0.4,
            "y": room_w - shower["length_ft"] - 0.4,
            "width": shower["width_ft"],
            "length": shower["length_ft"],
            "color": "#BEE1E6",
            "eco_feature": shower["eco_feature"],
            "price_inr": shower["price_inr"]
        })
        
    # 2. Place Bathtub (if present, placed adjacent to wet zone along North wall)
    tub = next((i for i in selected_items if i["category"] == "bathtub"), None)
    if tub:
        sh_w = shower["width_ft"] if shower else 3.5
        layout.append({
            "name": tub["name"],
            "sku": tub["sku"],
            "category": "bathtub",
            "x": sh_w + 1.0,
            "y": room_w - tub["width_ft"] - 0.4,
            "width": tub["length_ft"],  # Length horizontal along top wall
            "length": tub["width_ft"],
            "color": "#CDDAFD",
            "eco_feature": tub["eco_feature"],
            "price_inr": tub["price_inr"]
        })

    # 3. Place Vanity (Placed along East wall or South wall away from door)
    vanity = next((i for i in selected_items if i["category"] == "vanity"), None)
    if vanity:
        # Default along South-West wall if door is not South
        if door_wall == "South":
            # Mount along the East (Right) wall
            vx = room_l - vanity["width_ft"] - 0.4
            vy = room_w / 2 - (vanity["length_ft"] / 2)
            vw, vl = vanity["width_ft"], vanity["length_ft"]
        else:
            # Mount along South (Bottom) wall
            vx = 0.8
            vy = 0.4
            vw, vl = vanity["length_ft"], vanity["width_ft"]
            
        layout.append({
            "name": vanity["name"],
            "sku": vanity["sku"],
            "category": "vanity",
            "x": vx,
            "y": vy,
            "width": vw,
            "length": vl,
            "color": "#E2E2DF",
            "eco_feature": vanity["eco_feature"],
            "price_inr": vanity["price_inr"],
            "has_faucet": True,
            "faucet_name": faucet_item["name"] if faucet_item else "Standard Faucet"
        })

    # 4. Place Toilet (Placed with >=1.5 ft privacy clearance)
    toilet = next((i for i in selected_items if i["category"] == "toilet"), None)
    if toilet:
        if door_wall == "East":
            tx = 0.5
            ty = 0.5
        else:
            tx = room_l - toilet["width_ft"] - 0.6
            ty = 0.6
            
        layout.append({
            "name": toilet["name"],
            "sku": toilet["sku"],
            "category": "toilet",
            "x": tx,
            "y": ty,
            "width": toilet["width_ft"],
            "length": toilet["length_ft"],
            "color": "#D4A373",
            "eco_feature": toilet["eco_feature"],
            "price_inr": toilet["price_inr"]
        })

    # 5. Place Towel Rail / Accessory if present
    acc = next((i for i in selected_items if i["category"] == "accessory"), None)
    if acc:
        layout.append({
            "name": acc["name"],
            "sku": acc["sku"],
            "category": "accessory",
            "x": 0.4,
            "y": room_w / 2 - 1.0,
            "width": acc["width_ft"],
            "length": acc["length_ft"],
            "color": "#F0EFEB",
            "eco_feature": acc["eco_feature"],
            "price_inr": acc["price_inr"]
        })

    # 6. Calculate Door Swing position based on door_wall
    door_clearance = {"wall": door_wall}
    if door_wall == "South":
        door_clearance.update({"x": room_l / 2 - 1.5, "y": 0, "dx": 3.0, "dy": 0.2})
    elif door_wall == "North":
        door_clearance.update({"x": room_l / 2 - 1.5, "y": room_w - 0.2, "dx": 3.0, "dy": 0.2})
    elif door_wall == "East":
        door_clearance.update({"x": room_l - 0.2, "y": room_w / 2 - 1.5, "dx": 0.2, "dy": 3.0})
    else:  # West
        door_clearance.update({"x": 0, "y": room_w / 2 - 1.5, "dx": 0.2, "dy": 3.0})

    return {"fixtures": layout, "door": door_clearance}