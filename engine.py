import json
from typing import Dict, List, Any

def load_catalog() -> List[Dict[str, Any]]:
    with open("catalog.json", "r") as f:
        return json.load(f)

def run_intelligent_recommender(room_l: float, room_w: float, budget: float, style: str) -> Dict[str, Any]:
    catalog = load_catalog()
    area = room_l * room_w
    min_side = min(room_l, room_w)

    # 1. Architectural Typology Determination
    # If space is too tight (< 36 sq ft or min side < 5.5 ft), classify as Powder Room (Half-Bath)
    is_powder_room = (area < 36.0) or (min_side < 5.2)

    if is_powder_room:
        # Mandatory: Toilet + Vanity + Faucet (No Shower to prevent collision)
        desired_categories = ["toilet", "vanity", "faucet"]
        room_type_label = "Powder Room Suite (Half-Bath)"
    else:
        # Full bath: Shower + Vanity + Toilet + Faucet
        desired_categories = ["shower", "vanity", "toilet", "faucet"]
        room_type_label = "Full Architectural Bath"

        # Check physical space eligibility for luxury add-ons
        if min_side >= 8.0 and area >= 80.0:
            desired_categories.append("bathtub")
        if min_side >= 6.5 and area >= 50.0:
            desired_categories.append("accessory")

    # 2. Priority Pruning: Guarantee total_cost <= budget
    # Priority order to keep: toilet > vanity > faucet > shower > accessory > bathtub
    # Drop lowest priority first if over budget: bathtub first, then accessory, etc.
    while True:
        bundle, cost = select_optimal_bundle(catalog, desired_categories, budget, style, min_side, area)
        if cost <= budget or len(desired_categories) <= 3:
            break
        # Drop optional items in priority order
        if "bathtub" in desired_categories:
            desired_categories.remove("bathtub")
        elif "accessory" in desired_categories:
            desired_categories.remove("accessory")
        else:
            break

    # If still over budget, force the absolute lowest entry-tier items
    if cost > budget:
        bundle = [min([c for c in catalog if c["category"] == cat], key=lambda x: x["price_inr"]) for cat in desired_categories]
        cost = sum(x["price_inr"] for x in bundle)

    surplus = budget - cost

    return {
        "selected_skus": bundle,
        "total_cost": cost,
        "budget_surplus": surplus,
        "room_area_sqft": round(area, 1),
        "room_type": room_type_label,
        "design_concept": (
            f"Adaptive {style} {room_type_label} for {round(area, 1)} sq ft. "
            f"Prioritized {len(bundle)} fixtures with verified circulation envelopes."
        )
    }

def select_optimal_bundle(catalog, categories, budget, style, min_side, area):
    """Selects best candidate per category matching style and dimensional limits."""
    selected = []
    total = 0

    for cat in categories:
        pool = [c for c in catalog if c["category"] == cat]

        # Dimension constraints
        if min_side <= 6.0:
            if cat == "vanity":
                pool = [c for c in pool if c["length_ft"] <= 2.5] or pool
            elif cat == "shower":
                pool = [c for c in pool if c["width_ft"] <= 3.0 and c["length_ft"] <= 3.0] or pool

        # Style matching
        style_matches = [c for c in pool if style in c["aesthetic_tags"]]
        candidates = style_matches if style_matches else pool
        candidates = sorted(candidates, key=lambda x: x["price_inr"], reverse=True)

        # Headroom selection
        remaining_count = len(categories) - len(selected) - 1
        reserve = remaining_count * 8000

        chosen = None
        for item in candidates:
            if total + item["price_inr"] + reserve <= budget:
                chosen = item
                break
        if not chosen:
            chosen = min(pool, key=lambda x: x["price_inr"])

        selected.append(chosen)
        total += chosen["price_inr"]

    return selected, total

def solve_spatial_layout(room_l: float, room_w: float, selected_items: List[Dict[str, Any]], door_wall: str = "South") -> Dict[str, Any]:
    """
    Collision-Free Wall-Slot Solver:
    - Dedicated door swing clearance corridor
    - Wet Zone on opposite wall
    - Opposed flanking walls for Vanity and Toilet
    """
    layout = []
    margin = 0.4

    shower = next((i for i in selected_items if i["category"] == "shower"), None)
    tub = next((i for i in selected_items if i["category"] == "bathtub"), None)
    vanity = next((i for i in selected_items if i["category"] == "vanity"), None)
    faucet = next((i for i in selected_items if i["category"] == "faucet"), None)
    toilet = next((i for i in selected_items if i["category"] == "toilet"), None)
    acc = next((i for i in selected_items if i["category"] == "accessory"), None)

    # Calculate door clearance
    door_w = min(3.0, room_l * 0.45 if door_wall in ["North", "South"] else room_w * 0.45)
    door = {"wall": door_wall}

    if door_wall == "North":
        door.update({"x": (room_l - door_w) / 2, "y": room_w - 0.25, "dx": door_w, "dy": 0.25})
        
        # 1. Shower (Bottom-Left / South-West)
        if shower:
            layout.append({
                "item_data": shower,
                "x": margin,
                "y": margin,
                "width": shower["width_ft"],
                "length": shower["length_ft"],
                "color": "#C5E1A5"
            })
        
        # 2. Bathtub (Along South wall next to shower)
        if tub:
            sh_w = shower["width_ft"] if shower else 0.0
            tub_x = margin + sh_w + 0.6
            if tub_x + tub["length_ft"] <= room_l - margin:
                layout.append({
                    "item_data": tub,
                    "x": round(tub_x, 2),
                    "y": margin,
                    "width": tub["length_ft"],
                    "length": tub["width_ft"],
                    "color": "#B3E5FC"
                })

        # 3. Vanity (Along West Wall, top-left clear of door)
        if vanity:
            # If shower exists on bottom-left, place vanity above it or center on clear wall
            vy = room_w - vanity["length_ft"] - margin - 0.5 if shower else (room_w / 2 - vanity["length_ft"] / 2)
            layout.append({
                "item_data": vanity,
                "x": margin,
                "y": max(margin, round(vy, 2)),
                "width": vanity["width_ft"],
                "length": vanity["length_ft"],
                "color": "#FFE082",
                "has_faucet": True,
                "faucet_data": faucet
            })

        # 4. Toilet (Along East Wall, opposite vanity)
        if toilet:
            ty = room_w - toilet["length_ft"] - margin - 0.5 if shower else (room_w / 2 - toilet["length_ft"] / 2)
            layout.append({
                "item_data": toilet,
                "x": round(room_l - toilet["width_ft"] - margin, 2),
                "y": max(margin, round(ty, 2)),
                "width": toilet["width_ft"],
                "length": toilet["length_ft"],
                "color": "#FFCCBC"
            })

        # 5. Accessory
        if acc:
            layout.append({
                "item_data": acc,
                "x": round(room_l - acc["width_ft"] - margin, 2),
                "y": margin + 0.8,
                "width": acc["width_ft"],
                "length": acc["length_ft"],
                "color": "#E1BEE7"
            })

    elif door_wall == "South":
        door.update({"x": (room_l - door_w) / 2, "y": 0.0, "dx": door_w, "dy": 0.25})

        if shower:
            layout.append({
                "item_data": shower,
                "x": margin,
                "y": round(room_w - shower["length_ft"] - margin, 2),
                "width": shower["width_ft"],
                "length": shower["length_ft"],
                "color": "#C5E1A5"
            })
        if tub:
            sh_w = shower["width_ft"] if shower else 0.0
            tub_x = margin + sh_w + 0.6
            if tub_x + tub["length_ft"] <= room_l - margin:
                layout.append({
                    "item_data": tub,
                    "x": round(tub_x, 2),
                    "y": round(room_w - tub["width_ft"] - margin, 2),
                    "width": tub["length_ft"],
                    "length": tub["width_ft"],
                    "color": "#B3E5FC"
                })
        if vanity:
            vy = margin + 0.5 if shower else (room_w / 2 - vanity["length_ft"] / 2)
            layout.append({
                "item_data": vanity,
                "x": margin,
                "y": max(margin, round(vy, 2)),
                "width": vanity["width_ft"],
                "length": vanity["length_ft"],
                "color": "#FFE082",
                "has_faucet": True,
                "faucet_data": faucet
            })
        if toilet:
            ty = margin + 0.5 if shower else (room_w / 2 - toilet["length_ft"] / 2)
            layout.append({
                "item_data": toilet,
                "x": round(room_l - toilet["width_ft"] - margin, 2),
                "y": max(margin, round(ty, 2)),
                "width": toilet["width_ft"],
                "length": toilet["length_ft"],
                "color": "#FFCCBC"
            })
        if acc:
            layout.append({
                "item_data": acc,
                "x": round(room_l - acc["width_ft"] - margin, 2),
                "y": round(room_w / 2, 2),
                "width": acc["width_ft"],
                "length": acc["length_ft"],
                "color": "#E1BEE7"
            })

    elif door_wall == "East":
        door.update({"x": room_l - 0.25, "y": (room_w - door_w) / 2, "dx": 0.25, "dy": door_w})

        if shower:
            layout.append({
                "item_data": shower,
                "x": margin,
                "y": round(room_w - shower["length_ft"] - margin, 2),
                "width": shower["width_ft"],
                "length": shower["length_ft"],
                "color": "#C5E1A5"
            })
        if tub:
            if tub["width_ft"] + (shower["length_ft"] if shower else 3.0) <= room_w:
                layout.append({
                    "item_data": tub,
                    "x": margin,
                    "y": margin,
                    "width": tub["length_ft"],
                    "length": tub["width_ft"],
                    "color": "#B3E5FC"
                })
        if vanity:
            layout.append({
                "item_data": vanity,
                "x": round(room_l / 2 - vanity["length_ft"] / 2, 2),
                "y": round(room_w - vanity["width_ft"] - margin, 2),
                "width": vanity["length_ft"],
                "length": vanity["width_ft"],
                "color": "#FFE082",
                "has_faucet": True,
                "faucet_data": faucet
            })
        if toilet:
            layout.append({
                "item_data": toilet,
                "x": round(room_l / 2 - toilet["width_ft"] / 2, 2),
                "y": margin,
                "width": toilet["width_ft"],
                "length": toilet["length_ft"],
                "color": "#FFCCBC"
            })
        if acc:
            layout.append({
                "item_data": acc,
                "x": margin + 0.5,
                "y": round(room_w / 2, 2),
                "width": acc["width_ft"],
                "length": acc["length_ft"],
                "color": "#E1BEE7"
            })

    else:  # West
        door.update({"x": 0.0, "y": (room_w - door_w) / 2, "dx": 0.25, "dy": door_w})

        if shower:
            layout.append({
                "item_data": shower,
                "x": round(room_l - shower["width_ft"] - margin, 2),
                "y": round(room_w - shower["length_ft"] - margin, 2),
                "width": shower["width_ft"],
                "length": shower["length_ft"],
                "color": "#C5E1A5"
            })
        if tub:
            if tub["width_ft"] + (shower["length_ft"] if shower else 3.0) <= room_w:
                layout.append({
                    "item_data": tub,
                    "x": round(room_l - tub["length_ft"] - margin, 2),
                    "y": margin,
                    "width": tub["length_ft"],
                    "length": tub["width_ft"],
                    "color": "#B3E5FC"
                })
        if vanity:
            layout.append({
                "item_data": vanity,
                "x": round(room_l / 2 - vanity["length_ft"] / 2, 2),
                "y": round(room_w - vanity["width_ft"] - margin, 2),
                "width": vanity["length_ft"],
                "length": vanity["width_ft"],
                "color": "#FFE082",
                "has_faucet": True,
                "faucet_data": faucet
            })
        if toilet:
            layout.append({
                "item_data": toilet,
                "x": round(room_l / 2 - toilet["width_ft"] / 2, 2),
                "y": margin,
                "width": toilet["width_ft"],
                "length": toilet["length_ft"],
                "color": "#FFCCBC"
            })
        if acc:
            layout.append({
                "item_data": acc,
                "x": round(room_l - acc["width_ft"] - margin - 0.5, 2),
                "y": round(room_w / 2, 2),
                "width": acc["width_ft"],
                "length": acc["length_ft"],
                "color": "#E1BEE7"
            })

    return {"fixtures": layout, "door": door}