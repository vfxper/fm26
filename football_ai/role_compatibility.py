"""
Role Compatibility System - Evaluates how well a player fits a position and role.
Applies bonuses/penalties to match simulation based on compatibility.

Usage:
    from football_ai.role_compatibility import evaluate_player_for_role, apply_role_effects

    result = evaluate_player_for_role(player_attrs, "Advanced Forward", "Attack", "ST", "natural")
    # result = {"level": "ideal", "color": "green", "bonus": 5, "compatibility_pct": 92}
"""

import numpy as np

# Position familiarity penalties (%)
FAMILIARITY_PENALTY = {
    "natural": 0,
    "accomplished": -5,
    "competent": -15,
    "unconvincing": -25,
    "awkward": -30,
}

# ============================================================
# KEY ATTRIBUTES PER ROLE: (attribute_name, minimum_threshold)
# ============================================================

ROLE_KEY_ATTRIBUTES = {
    # === GOALKEEPER ===
    "Goalkeeper_Defend": [
        ("reflexes", 15), ("handling", 15), ("positioning", 15),
        ("one_on_ones", 14), ("concentration", 14), ("composure", 13),
    ],
    "Sweeper Keeper_Defend": [
        ("rushing_out", 10), ("reflexes", 15), ("handling", 15),
        ("positioning", 15), ("one_on_ones", 14),
    ],
    "Sweeper Keeper_Support": [
        ("rushing_out", 13), ("acceleration", 12), ("first_touch", 11),
        ("passing", 11), ("decisions", 13), ("anticipation", 12),
    ],
    "Sweeper Keeper_Attack": [
        ("rushing_out", 15), ("acceleration", 14), ("first_touch", 13),
        ("passing", 13), ("decisions", 15), ("composure", 14),
        ("anticipation", 14), ("pace", 12),
    ],

    # === CENTRAL DEFENDER ===
    "Central Defender_Defend": [
        ("tackling", 15), ("marking", 14), ("strength", 14),
        ("positioning", 14), ("heading", 13),
    ],
    "Ball Playing Defender_Defend": [
        ("passing", 14), ("vision", 12), ("first_touch", 13),
        ("composure", 13), ("decisions", 13), ("technique", 11),
    ],
    "Ball Playing Defender_Stopper": [
        ("passing", 14), ("vision", 12), ("first_touch", 13),
        ("composure", 13), ("decisions", 13), ("technique", 11),
        ("aggression", 14), ("bravery", 15), ("acceleration", 12),
    ],
    "Ball Playing Defender_Cover": [
        ("passing", 14), ("vision", 12), ("first_touch", 13),
        ("composure", 13), ("decisions", 13), ("technique", 11),
        ("anticipation", 15), ("acceleration", 14), ("pace", 12),
    ],
    "No-Nonsense Centre-Back_Defend": [
        ("tackling", 14), ("strength", 15), ("heading", 14),
        ("bravery", 15), ("aggression", 13),
    ],
    "Libero_Support": [
        ("passing", 14), ("vision", 13), ("first_touch", 14),
        ("decisions", 14), ("composure", 14), ("technique", 12),
        ("acceleration", 11), ("dribbling", 11),
    ],
    "Libero_Attack": [
        ("passing", 14), ("vision", 13), ("first_touch", 14),
        ("decisions", 14), ("composure", 14), ("technique", 12),
        ("acceleration", 11), ("dribbling", 11),
        ("finishing", 10), ("long_shots", 11), ("off_the_ball", 11), ("stamina", 13),
    ],

    # === FULL-BACK ===
    "Full-Back_Defend": [
        ("tackling", 14), ("marking", 13), ("positioning", 14),
        ("anticipation", 13), ("strength", 12),
    ],
    "Full-Back_Support": [
        ("tackling", 13), ("crossing", 12), ("passing", 12),
        ("stamina", 14), ("work_rate", 13),
    ],
    "Full-Back_Attack": [
        ("crossing", 14), ("dribbling", 13), ("acceleration", 14),
        ("pace", 14), ("stamina", 15),
    ],
    "No-Nonsense Full-Back_Defend": [
        ("tackling", 15), ("strength", 14), ("positioning", 14), ("bravery", 14),
    ],

    # === WING-BACK ===
    "Wing-Back_Defend": [
        ("tackling", 13), ("positioning", 13), ("stamina", 15),
        ("work_rate", 14), ("acceleration", 13),
    ],
    "Wing-Back_Support": [
        ("crossing", 13), ("passing", 12), ("stamina", 16),
        ("acceleration", 14), ("work_rate", 14),
    ],
    "Wing-Back_Attack": [
        ("crossing", 15), ("dribbling", 14), ("acceleration", 15),
        ("pace", 15), ("stamina", 17), ("off_the_ball", 13),
    ],
    "Inverted Wing-Back_Defend": [
        ("passing", 14), ("vision", 12), ("decisions", 13),
        ("positioning", 13), ("first_touch", 12), ("tackling", 12),
    ],
    "Inverted Wing-Back_Support": [
        ("passing", 14), ("vision", 12), ("decisions", 13),
        ("positioning", 13), ("first_touch", 12), ("tackling", 12),
        ("dribbling", 12), ("acceleration", 12),
    ],
    "Inverted Wing-Back_Attack": [
        ("passing", 14), ("vision", 12), ("decisions", 13),
        ("positioning", 13), ("first_touch", 12), ("tackling", 12),
        ("dribbling", 12), ("acceleration", 12),
    ],
    "Complete Wing-Back_Support": [
        ("crossing", 14), ("dribbling", 14), ("passing", 13),
        ("tackling", 12), ("acceleration", 15), ("pace", 15),
        ("stamina", 16), ("work_rate", 15), ("decisions", 13),
    ],
    "Complete Wing-Back_Attack": [
        ("crossing", 14), ("dribbling", 14), ("passing", 13),
        ("tackling", 12), ("acceleration", 15), ("pace", 15),
        ("stamina", 16), ("work_rate", 15), ("decisions", 13),
        ("finishing", 11), ("off_the_ball", 13), ("flair", 13),
    ],

    # === DEFENSIVE MIDFIELDER ===
    "Defensive Midfielder_Defend": [
        ("tackling", 15), ("positioning", 15), ("anticipation", 14),
        ("work_rate", 14), ("strength", 13), ("bravery", 13),
    ],
    "Defensive Midfielder_Support": [
        ("tackling", 15), ("positioning", 15), ("anticipation", 14),
        ("work_rate", 14), ("strength", 13), ("bravery", 13),
        ("passing", 11), ("first_touch", 11),
    ],
    "Deep Lying Playmaker_Defend": [
        ("passing", 16), ("vision", 15), ("decisions", 14),
        ("first_touch", 14), ("technique", 13), ("composure", 15),
        ("anticipation", 13), ("positioning", 13),
    ],
    "Deep Lying Playmaker_Support": [
        ("passing", 16), ("vision", 15), ("decisions", 14),
        ("first_touch", 14), ("technique", 13), ("composure", 15),
        ("anticipation", 13), ("positioning", 13), ("off_the_ball", 11),
    ],
    "Anchor Man_Defend": [
        ("tackling", 14), ("strength", 15), ("positioning", 15),
        ("anticipation", 14), ("bravery", 15), ("concentration", 14),
    ],
    "Half-Back_Defend": [
        ("tackling", 14), ("positioning", 15), ("passing", 12),
        ("composure", 13), ("anticipation", 14), ("decisions", 13), ("strength", 13),
    ],
    "Regista_Support": [
        ("passing", 17), ("vision", 16), ("decisions", 15),
        ("flair", 15), ("first_touch", 15), ("technique", 15),
        ("composure", 16), ("anticipation", 14),
    ],
    "Roaming Playmaker_Support": [
        ("passing", 15), ("vision", 14), ("decisions", 14),
        ("stamina", 16), ("work_rate", 15), ("first_touch", 14),
        ("technique", 14), ("agility", 13),
    ],
    "Ball Winning Midfielder_Defend": [
        ("tackling", 16), ("aggression", 16), ("bravery", 16),
        ("work_rate", 15), ("strength", 14), ("stamina", 14),
    ],
    "Ball Winning Midfielder_Support": [
        ("tackling", 16), ("aggression", 16), ("bravery", 16),
        ("work_rate", 15), ("strength", 14), ("stamina", 14), ("passing", 10),
    ],
    "Segundo Volante_Support": [
        ("stamina", 17), ("work_rate", 15), ("long_shots", 13),
        ("passing", 12), ("tackling", 12), ("acceleration", 13),
        ("off_the_ball", 13), ("first_touch", 12),
    ],
    "Segundo Volante_Attack": [
        ("stamina", 17), ("work_rate", 15), ("long_shots", 13),
        ("passing", 12), ("tackling", 12), ("acceleration", 13),
        ("off_the_ball", 13), ("first_touch", 12),
        ("finishing", 12), ("composure", 13),
    ],

    # === CENTRAL MIDFIELDER ===
    "Central Midfielder_Defend": [
        ("passing", 13), ("positioning", 13), ("tackling", 12),
        ("decisions", 13), ("teamwork", 14), ("work_rate", 13),
    ],
    "Central Midfielder_Support": [
        ("passing", 14), ("decisions", 14), ("first_touch", 13),
        ("teamwork", 14), ("stamina", 14), ("work_rate", 13),
    ],
    "Central Midfielder_Attack": [
        ("passing", 14), ("long_shots", 14), ("finishing", 12),
        ("decisions", 13), ("first_touch", 13), ("off_the_ball", 13),
    ],
    "Box-to-Box Midfielder_Support": [
        ("stamina", 17), ("work_rate", 16), ("passing", 13),
        ("tackling", 12), ("long_shots", 13), ("first_touch", 13),
        ("acceleration", 13), ("decisions", 13),
    ],
    "Advanced Playmaker_Support": [
        ("passing", 16), ("vision", 16), ("decisions", 15),
        ("first_touch", 15), ("technique", 15), ("flair", 14), ("composure", 15),
    ],
    "Advanced Playmaker_Attack": [
        ("passing", 16), ("vision", 16), ("decisions", 15),
        ("first_touch", 15), ("technique", 15), ("flair", 14),
        ("composure", 15), ("dribbling", 13), ("finishing", 11),
    ],
    "Mezzala_Support": [
        ("passing", 14), ("vision", 13), ("dribbling", 14),
        ("first_touch", 14), ("decisions", 13), ("acceleration", 13), ("off_the_ball", 13),
    ],
    "Mezzala_Attack": [
        ("passing", 14), ("vision", 13), ("dribbling", 14),
        ("first_touch", 14), ("decisions", 13), ("acceleration", 13),
        ("off_the_ball", 13), ("finishing", 13), ("long_shots", 13), ("composure", 14),
    ],
    "Carrilero_Support": [
        ("work_rate", 15), ("stamina", 15), ("positioning", 14),
        ("tackling", 13), ("passing", 12), ("decisions", 12), ("teamwork", 15),
    ],

    # === ATTACKING MIDFIELDER ===
    "Attacking Midfielder_Support": [
        ("passing", 15), ("vision", 14), ("first_touch", 14),
        ("technique", 14), ("decisions", 14), ("long_shots", 13), ("flair", 13),
    ],
    "Attacking Midfielder_Attack": [
        ("finishing", 14), ("dribbling", 14), ("first_touch", 14),
        ("composure", 14), ("off_the_ball", 14), ("passing", 13), ("decisions", 13),
    ],
    "Trequartista_Attack": [
        ("flair", 17), ("dribbling", 16), ("technique", 16),
        ("first_touch", 16), ("passing", 15), ("vision", 15),
        ("composure", 15), ("finishing", 14), ("off_the_ball", 15),
    ],
    "Enganche_Attack": [
        ("passing", 17), ("vision", 17), ("first_touch", 16),
        ("technique", 15), ("composure", 16), ("decisions", 15), ("flair", 14),
    ],
    "Shadow Striker_Attack": [
        ("finishing", 15), ("off_the_ball", 16), ("composure", 14),
        ("acceleration", 14), ("dribbling", 13), ("first_touch", 13), ("anticipation", 15),
    ],

    # === WINGER ===
    "Winger_Support": [
        ("crossing", 14), ("dribbling", 14), ("pace", 14),
        ("acceleration", 14), ("agility", 13), ("technique", 13),
    ],
    "Winger_Attack": [
        ("crossing", 15), ("dribbling", 15), ("pace", 15),
        ("acceleration", 15), ("finishing", 12), ("off_the_ball", 13),
    ],
    "Inside Forward_Support": [
        ("dribbling", 15), ("finishing", 13), ("passing", 13),
        ("first_touch", 14), ("technique", 14), ("long_shots", 13), ("acceleration", 14),
    ],
    "Inside Forward_Attack": [
        ("finishing", 15), ("dribbling", 15), ("off_the_ball", 15),
        ("composure", 14), ("acceleration", 14), ("pace", 14), ("first_touch", 14),
    ],
    "Inverted Winger_Support": [
        ("dribbling", 15), ("passing", 14), ("technique", 14),
        ("first_touch", 14), ("acceleration", 14), ("agility", 14), ("vision", 13),
    ],
    "Inverted Winger_Attack": [
        ("dribbling", 15), ("passing", 14), ("technique", 14),
        ("first_touch", 14), ("acceleration", 14), ("agility", 14),
        ("vision", 13), ("finishing", 12), ("long_shots", 13),
    ],
    "Wide Playmaker_Support": [
        ("passing", 16), ("vision", 15), ("first_touch", 15),
        ("technique", 15), ("decisions", 14), ("flair", 13), ("composure", 14),
    ],
    "Wide Playmaker_Attack": [
        ("passing", 16), ("vision", 15), ("first_touch", 15),
        ("technique", 15), ("decisions", 14), ("flair", 13),
        ("composure", 14), ("dribbling", 13),
    ],
    "Wide Target Man_Support": [
        ("strength", 16), ("heading", 15), ("first_touch", 14),
        ("bravery", 15), ("jumping_reach", 14), ("teamwork", 14), ("balance", 14),
    ],
    "Wide Target Man_Attack": [
        ("strength", 16), ("heading", 15), ("first_touch", 14),
        ("bravery", 15), ("jumping_reach", 14), ("teamwork", 14),
        ("balance", 14), ("finishing", 12),
    ],
    "Raumdeuter_Attack": [
        ("off_the_ball", 18), ("finishing", 15), ("composure", 15),
        ("anticipation", 16), ("acceleration", 14), ("first_touch", 13), ("decisions", 14),
    ],
    "Defensive Winger_Defend": [
        ("work_rate", 16), ("tackling", 14), ("stamina", 15),
        ("positioning", 13), ("acceleration", 12), ("teamwork", 15),
    ],
    "Defensive Winger_Support": [
        ("work_rate", 16), ("tackling", 14), ("stamina", 15),
        ("positioning", 13), ("acceleration", 12), ("teamwork", 15),
        ("crossing", 11), ("passing", 11),
    ],

    # === STRIKER ===
    "Advanced Forward_Attack": [
        ("finishing", 16), ("off_the_ball", 16), ("composure", 15),
        ("acceleration", 16), ("pace", 15), ("anticipation", 14), ("dribbling", 13),
    ],
    "Poacher_Attack": [
        ("finishing", 17), ("off_the_ball", 17), ("composure", 16),
        ("anticipation", 15), ("acceleration", 14), ("first_touch", 14),
    ],
    "Target Man_Support": [
        ("strength", 17), ("heading", 16), ("first_touch", 15),
        ("bravery", 16), ("jumping_reach", 15), ("teamwork", 15), ("balance", 14),
    ],
    "Target Man_Attack": [
        ("strength", 17), ("heading", 16), ("first_touch", 15),
        ("bravery", 16), ("jumping_reach", 15), ("teamwork", 15),
        ("balance", 14), ("finishing", 14),
    ],
    "Pressing Forward_Defend": [
        ("work_rate", 17), ("stamina", 16), ("aggression", 15),
        ("bravery", 14), ("tackling", 12), ("teamwork", 15),
    ],
    "Pressing Forward_Support": [
        ("work_rate", 17), ("stamina", 16), ("aggression", 15),
        ("bravery", 14), ("tackling", 12), ("teamwork", 15),
        ("finishing", 12), ("first_touch", 12),
    ],
    "Pressing Forward_Attack": [
        ("work_rate", 17), ("stamina", 16), ("aggression", 15),
        ("bravery", 14), ("tackling", 12), ("teamwork", 15),
        ("finishing", 14), ("off_the_ball", 14), ("composure", 13),
    ],
    "Deep Lying Forward_Support": [
        ("passing", 15), ("vision", 14), ("first_touch", 15),
        ("technique", 14), ("composure", 15), ("decisions", 14),
        ("teamwork", 14), ("off_the_ball", 13),
    ],
    "Deep Lying Forward_Attack": [
        ("passing", 15), ("vision", 14), ("first_touch", 15),
        ("technique", 14), ("composure", 15), ("decisions", 14),
        ("teamwork", 14), ("off_the_ball", 13), ("finishing", 13),
    ],
    "Complete Forward_Support": [
        ("finishing", 15), ("passing", 14), ("first_touch", 15),
        ("technique", 15), ("composure", 15), ("decisions", 14),
        ("off_the_ball", 15), ("vision", 14), ("strength", 13), ("acceleration", 14),
    ],
    "Complete Forward_Attack": [
        ("finishing", 15), ("passing", 14), ("first_touch", 15),
        ("technique", 15), ("composure", 15), ("decisions", 14),
        ("off_the_ball", 15), ("vision", 14), ("strength", 13),
        ("acceleration", 14), ("heading", 13), ("dribbling", 14),
    ],
    "False Nine_Support": [
        ("passing", 16), ("vision", 16), ("first_touch", 16),
        ("technique", 16), ("composure", 16), ("decisions", 15),
        ("dribbling", 15), ("flair", 15), ("off_the_ball", 14),
    ],
}


def evaluate_player_for_role(player_attrs, role_name, duty, position, familiarity="natural"):
    """
    Evaluate how well a player fits a role.

    Args:
        player_attrs: dict of attribute_name -> value (1-20)
        role_name: e.g. "Advanced Forward"
        duty: e.g. "Attack", "Support", "Defend"
        position: e.g. "ST", "CB", "GK"
        familiarity: "natural", "accomplished", "competent", "unconvincing", "awkward"

    Returns:
        dict with level, color, bonus/penalty, compatibility_pct
    """
    # Check familiarity
    fam_penalty = FAMILIARITY_PENALTY.get(familiarity, -30)
    if familiarity == "awkward":
        return {
            "level": "unknown",
            "color": "gray",
            "penalty": -30,
            "compatibility_pct": 0,
            "details": [],
        }

    # Get key attributes for this role
    key = f"{role_name}_{duty}"
    if key not in ROLE_KEY_ATTRIBUTES:
        # Try without duty
        key = f"{role_name}_Defend"
    if key not in ROLE_KEY_ATTRIBUTES:
        return {"level": "unknown", "color": "gray", "penalty": 0, "compatibility_pct": 50, "details": []}

    key_attrs = ROLE_KEY_ATTRIBUTES[key]

    # Evaluate
    total = 0
    all_above_threshold = True
    any_below_10 = False
    details = []

    for attr_name, threshold in key_attrs:
        value = player_attrs.get(attr_name, 10)
        total += value
        meets = value >= threshold
        if not meets:
            all_above_threshold = False
        if value < 10:
            any_below_10 = True
        details.append({
            "attr": attr_name,
            "value": value,
            "threshold": threshold,
            "meets": meets,
        })

    avg = total / len(key_attrs) if key_attrs else 10

    # Determine level
    if all_above_threshold and avg >= 14:
        level = "ideal"
        color = "green"
        bonus = 5
    elif not any_below_10 and avg >= 10:
        level = "acceptable"
        color = "yellow"
        bonus = 0
    else:
        level = "poor"
        color = "red"
        bonus = -10

    # Compatibility percentage
    compatibility_pct = (avg / 20) * 100 + fam_penalty
    compatibility_pct = max(0, min(100, compatibility_pct))

    return {
        "level": level,
        "color": color,
        "bonus": bonus,
        "compatibility_pct": round(compatibility_pct, 1),
        "familiarity": familiarity,
        "familiarity_penalty": fam_penalty,
        "avg_key_attrs": round(avg, 1),
        "details": details,
    }


def apply_role_effects(player_attrs, compatibility_result):
    """
    Apply role compatibility bonuses/penalties to player attributes for match simulation.

    Args:
        player_attrs: dict of attribute values
        compatibility_result: output from evaluate_player_for_role

    Returns:
        Modified attributes dict
    """
    modified = dict(player_attrs)
    bonus = compatibility_result.get("bonus", 0)
    fam_penalty = compatibility_result.get("familiarity_penalty", 0)

    # Apply familiarity penalty to ALL attributes
    if fam_penalty != 0:
        factor = 1.0 + fam_penalty / 100.0
        for key in modified:
            modified[key] = max(1, round(modified[key] * factor))

    # Apply role bonus/penalty to Decisions and Positioning
    if bonus != 0:
        factor = 1.0 + bonus / 100.0
        if "decisions" in modified:
            modified["decisions"] = max(1, min(20, round(modified["decisions"] * factor)))
        if "positioning" in modified:
            modified["positioning"] = max(1, min(20, round(modified["positioning"] * factor)))

    return modified


def get_all_roles_for_position(position):
    """Get all available roles for a position."""
    position_roles = {
        "GK": ["Goalkeeper_Defend", "Sweeper Keeper_Defend", "Sweeper Keeper_Support", "Sweeper Keeper_Attack"],
        "CB": ["Central Defender_Defend", "Ball Playing Defender_Defend", "Ball Playing Defender_Stopper",
               "Ball Playing Defender_Cover", "No-Nonsense Centre-Back_Defend", "Libero_Support", "Libero_Attack"],
        "FB": ["Full-Back_Defend", "Full-Back_Support", "Full-Back_Attack", "No-Nonsense Full-Back_Defend",
               "Inverted Wing-Back_Defend", "Inverted Wing-Back_Support", "Inverted Wing-Back_Attack"],
        "WB": ["Wing-Back_Defend", "Wing-Back_Support", "Wing-Back_Attack",
               "Complete Wing-Back_Support", "Complete Wing-Back_Attack",
               "Inverted Wing-Back_Defend", "Inverted Wing-Back_Support", "Inverted Wing-Back_Attack"],
        "DM": ["Defensive Midfielder_Defend", "Defensive Midfielder_Support",
               "Deep Lying Playmaker_Defend", "Deep Lying Playmaker_Support",
               "Anchor Man_Defend", "Half-Back_Defend", "Regista_Support",
               "Roaming Playmaker_Support", "Ball Winning Midfielder_Defend",
               "Ball Winning Midfielder_Support", "Segundo Volante_Support", "Segundo Volante_Attack"],
        "CM": ["Central Midfielder_Defend", "Central Midfielder_Support", "Central Midfielder_Attack",
               "Box-to-Box Midfielder_Support", "Advanced Playmaker_Support", "Advanced Playmaker_Attack",
               "Mezzala_Support", "Mezzala_Attack", "Carrilero_Support",
               "Deep Lying Playmaker_Defend", "Deep Lying Playmaker_Support",
               "Roaming Playmaker_Support", "Ball Winning Midfielder_Defend", "Ball Winning Midfielder_Support"],
        "AM": ["Attacking Midfielder_Support", "Attacking Midfielder_Attack",
               "Advanced Playmaker_Support", "Advanced Playmaker_Attack",
               "Trequartista_Attack", "Enganche_Attack", "Shadow Striker_Attack"],
        "AML": ["Winger_Support", "Winger_Attack", "Inside Forward_Support", "Inside Forward_Attack",
                "Inverted Winger_Support", "Inverted Winger_Attack",
                "Wide Playmaker_Support", "Wide Playmaker_Attack",
                "Wide Target Man_Support", "Wide Target Man_Attack",
                "Raumdeuter_Attack", "Defensive Winger_Defend", "Defensive Winger_Support"],
        "AMR": ["Winger_Support", "Winger_Attack", "Inside Forward_Support", "Inside Forward_Attack",
                "Inverted Winger_Support", "Inverted Winger_Attack",
                "Wide Playmaker_Support", "Wide Playmaker_Attack",
                "Wide Target Man_Support", "Wide Target Man_Attack",
                "Raumdeuter_Attack", "Defensive Winger_Defend", "Defensive Winger_Support"],
        "ST": ["Advanced Forward_Attack", "Poacher_Attack",
               "Target Man_Support", "Target Man_Attack",
               "Pressing Forward_Defend", "Pressing Forward_Support", "Pressing Forward_Attack",
               "Deep Lying Forward_Support", "Deep Lying Forward_Attack",
               "Complete Forward_Support", "Complete Forward_Attack",
               "False Nine_Support", "Trequartista_Attack"],
    }
    return position_roles.get(position, [])
