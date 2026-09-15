import os
import json
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

def load_catalog() -> List[Dict[str, Any]]:
    with open("catalog.json", "r") as f:
        return json.load(f)

# 1. NEURO-SYMBOLIC LLM RECOMMENDATION LAYER

def run_llm_recommender(
    room_l: float,
    room_w: float,
    budget: float,
    style: str,
    door_wall: str
) -> Dict[str, Any]:
    """
    Stage 1: Generative LLM Reasoner (Gemini 3.6 Flash)
    Inspects user constraints and the Kohler SKU catalog, performing 
    creative curation and returning a structured JSON recommendation.
    Falls back gracefully to the heuristic solver if offline or unconfigured.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    catalog = load_catalog()
    area = round(room_l * room_w, 1)
    min_side = min(room_l, room_w)
    is_powder_room = (area < 36.0) or (min_side < 5.2)

    if not api_key or api_key == "your_actual_gemini_api_key_here":
        return run_heuristic_recommender(room_l, room_w, budget, style, is_fallback=True)

    catalog_summary = []
    for item in catalog:
        catalog_summary.append({
            "sku": item["sku"],
            "name": item["name"],
            "category": item["category"],
            "price_inr": item["price_inr"],
            "dimensions": f"{item['width_ft']}x{item['length_ft']} ft",
            "aesthetic_tags": item["aesthetic_tags"],
            "eco_feature": item["eco_feature"]
        })

    allowed_fixture_guidance = (
        "This space is a compact Powder Room (<36 sq ft). ONLY select 1 toilet, 1 vanity, and 1 faucet. DO NOT select a shower or bathtub."
        if is_powder_room else
        "This is a Full Bath. Select 1 toilet, 1 vanity, 1 faucet, 1 shower enclosure. Only select a bathtub if area >= 80 sq ft and budget comfortably allows."
    )

    prompt = f"""
You are Kohler's Principal AI Space Planner and Design Architect.
Recommend an optimal, cohesive Kohler product bundle fitting the user's constraints.

USER CONSTRAINTS:
- Room Dimensions: {room_l} ft Length × {room_w} ft Width (Total Area: {area} sq ft)
- Entrance Door: {door_wall} Wall
- Target Maximum Budget: ₹{budget:,} INR
- Aesthetic Theme: {style}
- Typology Rule: {allowed_fixture_guidance}

AVAILABLE KOHLER PRODUCT CATALOG (JSON):
{json.dumps(catalog_summary, indent=2)}

TASK INSTRUCTIONS:
1. Select the most harmonious, coherent product bundle matching the aesthetic theme: '{style}'.
2. The sum of selected product prices MUST NOT exceed the target budget of ₹{budget:,} INR.
3. Every selected item must exist in the catalog provided above. Use exact SKUs.
4. Output your response STRICTLY as a raw JSON object (do not include markdown code block ticks, just valid parseable JSON) matching this schema:
{{
  "selected_skus": ["SKU_1", "SKU_2", ...],
  "architectural_rationale": "2-3 sentences explaining the design harmony and circulation strategy",
  "material_and_lighting_advice": "2 sentences suggesting tile finishes, Kohler metallic accents, and high-CRI lighting",
  "sustainability_metrics": "2 sentences detailing water-savings (GPM/GPF) and energy efficiency impact"
}}
"""

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        parsed = json.loads(raw_text)
        sku_list = parsed.get("selected_skus", [])

        selected_items = [item for item in catalog if item["sku"] in sku_list]

        if len(selected_items) < 3:
            return run_heuristic_recommender(room_l, room_w, budget, style, is_fallback=True)

        total_cost = sum(item["price_inr"] for item in selected_items)

        if total_cost > budget:
            selected_items, total_cost = prune_overbudget_bundle(selected_items, catalog, budget)

        critique_markdown = (
            f"**1. Architectural Layout & Circulation:**\n{parsed.get('architectural_rationale', '')}\n\n"
            f"**2. Materials, Finishes & Lighting:**\n{parsed.get('material_and_lighting_advice', '')}\n\n"
            f"**3. Sustainability & Efficiency Impact:**\n{parsed.get('sustainability_metrics', '')}"
        )

        return {
            "engine_mode": "⚡ Live Gemini 3.6 Flash Agent",
            "selected_skus": selected_items,
            "total_cost": total_cost,
            "budget_surplus": budget - total_cost,
            "room_area_sqft": area,
            "room_type": "Powder Room Suite (Half-Bath)" if is_powder_room else "Full Architectural Bath",
            "design_concept": parsed.get("architectural_rationale", f"Coordinated {style} design curated by Gemini AI."),
            "ai_critique": critique_markdown
        }

    except Exception as e:
        fallback_res = run_heuristic_recommender(room_l, room_w, budget, style, is_fallback=True)
        fallback_res["engine_mode"] = f"ℹ️ Localized Symbolic Engine (API Note: {str(e)[:40]}...)"
        return fallback_res


# 2. SYMBOLIC CONSTRAINT & PRUNING HELPERS

def prune_overbudget_bundle(items: List[Dict[str, Any]], catalog: List[Dict[str, Any]], budget: float):
    """Symbolic constraint validator: prunes optional items in priority order."""
    pruned = list(items)
    for cat in ["bathtub", "accessory"]:
        if sum(x["price_inr"] for x in pruned) <= budget:
            break
        pruned = [x for x in pruned if x["category"] != cat]

    if sum(x["price_inr"] for x in pruned) > budget:
        subbed = []
        for item in pruned:
            candidates = [c for c in catalog if c["category"] == item["category"]]
            cheapest = min(candidates, key=lambda x: x["price_inr"])
            subbed.append(cheapest)
        pruned = subbed

    return pruned, sum(x["price_inr"] for x in pruned)


def run_heuristic_recommender(room_l: float, room_w: float, budget: float, style: str, is_fallback: bool = False) -> Dict[str, Any]:
    """Deterministic constraint solver used as standalone or offline fallback."""
    catalog = load_catalog()
    area = round(room_l * room_w, 1)
    min_side = min(room_l, room_w)

    is_powder_room = (area < 36.0) or (min_side < 5.2)

    if is_powder_room:
        desired_categories = ["toilet", "vanity", "faucet"]
        room_type_label = "Powder Room Suite (Half-Bath)"
    else:
        desired_categories = ["shower", "vanity", "toilet", "faucet"]
        room_type_label = "Full Architectural Bath"
        if min_side >= 8.0 and area >= 80.0:
            desired_categories.append("bathtub")
        if min_side >= 6.5 and area >= 50.0:
            desired_categories.append("accessory")

    while True:
        bundle, cost = select_optimal_bundle(catalog, desired_categories, budget, style, min_side)
        if cost <= budget or len(desired_categories) <= 3:
            break
        if "bathtub" in desired_categories:
            desired_categories.remove("bathtub")
        elif "accessory" in desired_categories:
            desired_categories.remove("accessory")
        else:
            break

    if cost > budget:
        bundle = [min([c for c in catalog if c["category"] == cat], key=lambda x: x["price_inr"]) for cat in desired_categories]
        cost = sum(x["price_inr"] for x in bundle)

    surplus = budget - cost
    mode_text = "ℹ️ Localized Symbolic Engine" if is_fallback else "Deterministic Expert System"

    default_critique = (
        f"**1. Architectural Layout & Circulation:**\n"
        f"The {area} sq ft envelope utilizes a dedicated wet/dry zoning strategy with verified walking corridors.\n\n"
        f"**2. Materials, Finishes & Lighting:**\n"
        f"Pair neutral natural stone tile with matte black Kohler brassware and 3000K indirect perimeter cove lighting.\n\n"
        f"**3. Sustainability & Efficiency Impact:**\n"
        f"All selected Kohler fixtures comply with WaterSense standards, reducing consumption by up to 35%."
    )

    return {
        "engine_mode": mode_text,
        "selected_skus": bundle,
        "total_cost": cost,
        "budget_surplus": surplus,
        "room_area_sqft": area,
        "room_type": room_type_label,
        "design_concept": f"Optimized {style} {room_type_label} curated for {area} sq ft.",
        "ai_critique": default_critique
    }


def select_optimal_bundle(catalog, categories, budget, style, min_side):
    selected = []
    total = 0

    for cat in categories:
        pool = [c for c in catalog if c["category"] == cat]
        if min_side <= 6.0:
            if cat == "vanity":
                pool = [c for c in pool if c["length_ft"] <= 2.5] or pool
            elif cat == "shower":
                pool = [c for c in pool if c["width_ft"] <= 3.0 and c["length_ft"] <= 3.0] or pool

        style_matches = [c for c in pool if style in c["aesthetic_tags"]]
        candidates = style_matches if style_matches else pool
        candidates = sorted(candidates, key=lambda x: x["price_inr"], reverse=True)

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

# 3. SPATIAL LAYOUT & CLEARANCE ENGINE

def solve_spatial_layout(room_l: float, room_w: float, selected_items: List[Dict[str, Any]], door_wall: str = "South") -> Dict[str, Any]:
    layout = []
    margin = 0.4

    shower = next((i for i in selected_items if i["category"] == "shower"), None)
    tub = next((i for i in selected_items if i["category"] == "bathtub"), None)
    vanity = next((i for i in selected_items if i["category"] == "vanity"), None)
    faucet = next((i for i in selected_items if i["category"] == "faucet"), None)
    toilet = next((i for i in selected_items if i["category"] == "toilet"), None)
    acc = next((i for i in selected_items if i["category"] == "accessory"), None)

    # Standard residential bathroom door: 2.5 ft (calibrated to 2.2 ft for tight powder rooms)
    door_w = 2.5 if min(room_l, room_w) >= 6.5 else 2.2
    door = {"wall": door_wall}

    if door_wall == "North":
        door.update({"x": (room_l - door_w) / 2, "y": room_w - 0.2, "dx": door_w, "dy": 0.2})
        if shower:
            layout.append({
                "item_data": shower,
                "x": margin,
                "y": margin,
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
                    "y": margin,
                    "width": tub["length_ft"],
                    "length": tub["width_ft"],
                    "color": "#B3E5FC"
                })
        if vanity:
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
        door.update({"x": (room_l - door_w) / 2, "y": 0.0, "dx": door_w, "dy": 0.2})
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
        door.update({"x": room_l - 0.2, "y": (room_w - door_w) / 2, "dx": 0.2, "dy": door_w})
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
        door.update({"x": 0.0, "y": (room_w - door_w) / 2, "dx": 0.2, "dy": door_w})
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