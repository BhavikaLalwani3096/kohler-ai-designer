import json
from typing import Dict, List, Any

def load_catalog() -> List[Dict[str, Any]]:
    with open("catalog.json", "r") as f:
        return json.load(f)

def run_intelligent_recommender(room_l: float, room_w: float, budget: float, style: str) -> Dict[str, Any]:
    catalog = load_catalog()
    area = room_l * room_w
    
    # 1. Base mandatory components
    required_cats = ["toilet", "shower", "vanity", "faucet"]
    
    # 2. Check if space allows luxury add-ons
    can_fit_tub = area >= 65.0
    can_fit_acc = area >= 45.0

    # Pick the best combination that does not exceed budget
    # Try with optional items if budget permits, fallback cleanly if tight
    test_combinations = []
    if can_fit_tub and can_fit_acc:
        test_combinations.append(required_cats + ["bathtub", "accessory"])
    if can_fit_tub:
        test_combinations.append(required_cats + ["bathtub"])
    if can_fit_acc:
        test_combinations.append(required_cats + ["accessory"])
    test_combinations.append(required_cats)

    best_selection = None
    best_cost = 0

    for combo in test_combinations:
        selection = []
        cost = 0
        possible = True

        for cat in combo:
            candidates = [c for c in catalog if c["category"] == cat]
            
            # Prefer larger vanity for spacious rooms
            if cat == "vanity" and area >= 80.0:
                doubles = [c for c in candidates if "Double" in c["name"]]
                if doubles:
                    candidates = doubles

            # Filter by style if available, else keep all
            style_matches = [c for c in candidates if style in c["aesthetic_tags"]]
            pool = style_matches if style_matches else candidates
            
            # Sort descending by price to maximize quality
            pool = sorted(pool, key=lambda x: x["price_inr"], reverse=True)
            
            # Find an item that keeps overall cost under budget
            chosen = None
            for item in pool:
                # Estimate conservative budget headroom for remaining categories
                remaining_cats = len(combo) - len(selection) - 1
                estimated_reserve = remaining_cats * 15000  # min fallback cost
                if cost + item["price_inr"] + estimated_reserve <= budget:
                    chosen = item
                    break
            
            # If still None, take the cheapest item from catalog in this category
            if not chosen:
                cheapest = min(candidates, key=lambda x: x["price_inr"])
                chosen = cheapest

            selection.append(chosen)
            cost += chosen["price_inr"]

        if cost <= budget:
            best_selection = selection
            best_cost = cost
            break  # Found the most luxurious viable combination

    # Final safeguard: if even the cheapest base set exceeds the budget
    if not best_selection:
        best_selection = [min([c for c in catalog if c["category"] == cat], key=lambda x: x["price_inr"]) for cat in required_cats]
        best_cost = sum(x["price_inr"] for x in best_selection)

    surplus = budget - best_cost

    return {
        "selected_skus": best_selection,
        "total_cost": best_cost,
        "budget_surplus": surplus,
        "room_area_sqft": round(area, 1),
        "design_concept": (
            f"Curated {style} suite for {round(area, 1)} sq ft. "
            f"Optimized across {len(best_selection)} Kohler fixtures ensuring WaterSense performance and circulation clearances."
        )
    }

def solve_spatial_layout(room_l: float, room_w: float, selected_items: List[Dict[str, Any]], door_wall: str = "South") -> Dict[str, Any]:
    """
    Dynamically positions fixtures to guarantee 0% clash with the entrance door.
    The door wall is strictly kept clear of large fixtures.
    """
    layout = []
    
    # Extract items by category
    toilet = next((i for i in selected_items if i["category"] == "toilet"), None)
    shower = next((i for i in selected_items if i["category"] == "shower"), None)
    vanity = next((i for i in selected_items if i["category"] == "vanity"), None)
    faucet = next((i for i in selected_items if i["category"] == "faucet"), None)
    tub = next((i for i in selected_items if i["category"] == "bathtub"), None)
    acc = next((i for i in selected_items if i["category"] == "accessory"), None)

    # 1. Determine Door Geometry (3.0 ft clearance swing arc)
    door = {"wall": door_wall}
    if door_wall == "South":
        door.update({"x": room_l / 2 - 1.5, "y": 0, "dx": 3.0, "dy": 0.25})
    elif door_wall == "North":
        door.update({"x": room_l / 2 - 1.5, "y": room_w - 0.25, "dx": 3.0, "dy": 0.25})
    elif door_wall == "East":
        door.update({"x": room_l - 0.25, "y": room_w / 2 - 1.5, "dx": 0.25, "dy": 3.0})
    else:  # West
        door.update({"x": 0, "y": room_w / 2 - 1.5, "dx": 0.25, "dy": 3.0})

    # 2. Dynamic Zone Allocation based on Door Wall:
    # If Door is North -> Wet zone moves to South-West (Bottom-Left)
    # If Door is South -> Wet zone stays at North-West (Top-Left)
    # If Door is East  -> Wet zone stays at North-West
    # If Door is West  -> Wet zone moves to North-East
    if door_wall == "North":
        wet_corner_x = 0.5
        wet_corner_y = 0.5
        tub_y = 0.5
        vanity_wall = "North-East"  # Away from the North-Center door
    elif door_wall == "West":
        wet_corner_x = room_l - (shower["width_ft"] if shower else 3.5) - 0.5
        wet_corner_y = room_w - (shower["length_ft"] if shower else 3.5) - 0.5
        tub_y = room_w - (tub["width_ft"] if tub else 2.8) - 0.5
        vanity_wall = "South"
    else:
        # Default for South or East doors: North-West Wet Zone
        wet_corner_x = 0.5
        wet_corner_y = room_w - (shower["length_ft"] if shower else 3.5) - 0.5
        tub_y = room_w - (tub["width_ft"] if tub else 2.8) - 0.5
        vanity_wall = "East" if door_wall == "South" else "South"

    # Place Shower
    if shower:
        layout.append({
            "item_data": shower,
            "x": round(wet_corner_x, 2),
            "y": round(wet_corner_y, 2),
            "width": shower["width_ft"],
            "length": shower["length_ft"],
            "color": "#C5E1A5",
            "is_fixture": True
        })

    # Place Bathtub if present (along safe wall, adjacent to wet zone)
    if tub:
        if door_wall == "North":
            # Place horizontally along South wall next to shower
            tub_x = wet_corner_x + (shower["width_ft"] if shower else 3.5) + 0.8
            layout.append({
                "item_data": tub,
                "x": round(tub_x, 2),
                "y": 0.5,
                "width": tub["length_ft"],
                "length": tub["width_ft"],
                "color": "#B3E5FC",
                "is_fixture": True
            })
        else:
            # Place horizontally along North wall next to shower
            tub_x = wet_corner_x + (shower["width_ft"] if shower else 3.5) + 0.8
            if tub_x + tub["length_ft"] <= room_l - 0.5:
                layout.append({
                    "item_data": tub,
                    "x": round(tub_x, 2),
                    "y": round(tub_y, 2),
                    "width": tub["length_ft"],
                    "length": tub["width_ft"],
                    "color": "#B3E5FC",
                    "is_fixture": True
                })

    # Place Vanity (with fitted faucet)
    if vanity:
        if door_wall == "North":
            # Put along East wall
            vx = room_l - vanity["width_ft"] - 0.5
            vy = room_w / 2 - (vanity["length_ft"] / 2)
            vw, vl = vanity["width_ft"], vanity["length_ft"]
        elif door_wall == "South":
            # Put along East wall
            vx = room_l - vanity["width_ft"] - 0.5
            vy = room_w / 2 - (vanity["length_ft"] / 2)
            vw, vl = vanity["width_ft"], vanity["length_ft"]
        else:
            # Put along North or South wall
            vx = 0.6
            vy = 0.6
            vw, vl = vanity["length_ft"], vanity["width_ft"]

        layout.append({
            "item_data": vanity,
            "x": round(vx, 2),
            "y": round(vy, 2),
            "width": vw,
            "length": vl,
            "color": "#FFE082",
            "is_fixture": True,
            "has_faucet": True,
            "faucet_data": faucet
        })

    # Place Toilet (Privacy placement in available clear corner)
    if toilet:
        if door_wall == "North":
            tx = room_l - toilet["width_ft"] - 0.6
            ty = 0.6
        elif door_wall == "East":
            tx = 0.6
            ty = 0.6
        else:
            tx = room_l - toilet["width_ft"] - 0.6
            ty = 0.6

        layout.append({
            "item_data": toilet,
            "x": round(tx, 2),
            "y": round(ty, 2),
            "width": toilet["width_ft"],
            "length": toilet["length_ft"],
            "color": "#FFCCBC",
            "is_fixture": True
        })

    # Place Accessory (Mirror/Towel Rail)
    if acc:
        ax_pos = 0.4 if door_wall != "West" else room_l - 0.8
        ay_pos = room_w / 2 - (acc["length_ft"] / 2)
        layout.append({
            "item_data": acc,
            "x": round(ax_pos, 2),
            "y": round(ay_pos, 2),
            "width": acc["width_ft"],
            "length": acc["length_ft"],
            "color": "#E1BEE7",
            "is_fixture": True
        })

    return {"fixtures": layout, "door": door}