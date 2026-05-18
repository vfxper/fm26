"""
Static catalogue of training roles per position (FM-style).

Each role maps to:
- key_attributes: list of attribute names this role develops
- phase: "with_ball" / "without_ball" / "universal"
- positions: list of position codes (matches CSV) it applies to
- label_ru: Russian display name

Used by:
- the per-player Development tab
- the auto-pick on training tab ("автоматически выбиралась лучшая")
- the match engine, to weight player's effective rating per role
"""

TRAINING_ROLES = {
    # Goalkeepers
    "GK_DEFEND": {
        "label_ru": "Вратарь (защита)",
        "phase": "without_ball",
        "positions": ["GK"],
        "key_attributes": ["concentration", "anticipation", "jumping_reach", "agility", "natural_fitness"],
    },
    "SK_ATTACK": {
        "label_ru": "Свипер-кипер (атака)",
        "phase": "with_ball",
        "positions": ["GK"],
        "key_attributes": ["acceleration", "passing", "first_touch", "stamina", "anticipation"],
    },
    # Centre-backs
    "CD_DEFEND": {
        "label_ru": "Центральный защитник (защита)",
        "phase": "without_ball",
        "positions": ["D C", "DC"],
        "key_attributes": ["tackling", "marking", "positioning", "jumping_reach", "strength"],
    },
    "CD_STOPPER": {
        "label_ru": "Стоппер",
        "phase": "without_ball",
        "positions": ["D C", "DC"],
        "key_attributes": ["aggression", "tackling", "marking", "jumping_reach", "strength", "bravery"],
    },
    "BPD_SUPPORT": {
        "label_ru": "Защитник-либеро (поддержка)",
        "phase": "with_ball",
        "positions": ["D C", "DC"],
        "key_attributes": ["passing", "technique", "vision", "first_touch", "positioning"],
    },
    # Full-backs
    "FB_DEFEND": {
        "label_ru": "Фланговый защитник (защита)",
        "phase": "without_ball",
        "positions": ["D R", "D L", "DR", "DL"],
        "key_attributes": ["tackling", "marking", "positioning", "stamina", "acceleration"],
    },
    "FB_SUPPORT": {
        "label_ru": "Фланговый защитник (поддержка)",
        "phase": "universal",
        "positions": ["D R", "D L", "DR", "DL"],
        "key_attributes": ["passing", "crossing", "stamina", "acceleration", "technique"],
    },
    "FB_ATTACK": {
        "label_ru": "Фланговый защитник (атака)",
        "phase": "with_ball",
        "positions": ["D R", "D L", "DR", "DL", "WB"],
        "key_attributes": ["crossing", "dribbling", "pace", "stamina", "off_the_ball"],
    },
    "WB_SUPPORT": {
        "label_ru": "Латераль (поддержка)",
        "phase": "with_ball",
        "positions": ["WB", "D R", "D L", "DR", "DL"],
        "key_attributes": ["stamina", "pace", "crossing", "passing", "dribbling"],
    },
    "IWB_SUPPORT": {
        "label_ru": "Инвертированный защитник (поддержка)",
        "phase": "with_ball",
        "positions": ["WB", "D R", "D L"],
        "key_attributes": ["passing", "technique", "vision", "first_touch", "stamina"],
    },
    # Defensive midfielders
    "DM_DEFEND": {
        "label_ru": "Опорник (защита)",
        "phase": "without_ball",
        "positions": ["DM", "DM C"],
        "key_attributes": ["tackling", "marking", "positioning", "strength", "aggression"],
    },
    "DLP_SUPPORT": {
        "label_ru": "Глубинный плеймейкер",
        "phase": "with_ball",
        "positions": ["DM", "DM C", "M C"],
        "key_attributes": ["passing", "technique", "vision", "first_touch", "decisions"],
    },
    "REGISTA": {
        "label_ru": "Реджиста",
        "phase": "with_ball",
        "positions": ["DM", "DM C"],
        "key_attributes": ["passing", "vision", "technique", "long_shots", "anticipation"],
    },
    "B2B": {
        "label_ru": "Бокс-ту-бокс",
        "phase": "universal",
        "positions": ["M C", "MC"],
        "key_attributes": ["stamina", "acceleration", "passing", "technique", "teamwork"],
    },
    "AP_SUPPORT": {
        "label_ru": "Атакующий плеймейкер",
        "phase": "with_ball",
        "positions": ["AM C", "M C", "AMC"],
        "key_attributes": ["passing", "vision", "technique", "first_touch", "off_the_ball"],
    },
    "CM_ATTACK": {
        "label_ru": "ЦПЗ (атака)",
        "phase": "with_ball",
        "positions": ["M C", "AM C"],
        "key_attributes": ["passing", "technique", "long_shots", "first_touch", "vision"],
    },
    # Wingers / inside fwds
    "WINGER_SUPPORT": {
        "label_ru": "Вингер (поддержка)",
        "phase": "with_ball",
        "positions": ["AM R", "AM L", "M R", "M L", "AMR", "AML"],
        "key_attributes": ["crossing", "dribbling", "pace", "stamina", "passing"],
    },
    "WINGER_ATTACK": {
        "label_ru": "Вингер (атака)",
        "phase": "with_ball",
        "positions": ["AM R", "AM L", "AMR", "AML"],
        "key_attributes": ["dribbling", "pace", "crossing", "finishing", "off_the_ball"],
    },
    "INSIDE_FWD_SUPPORT": {
        "label_ru": "Инсайд (поддержка)",
        "phase": "with_ball",
        "positions": ["AM R", "AM L", "AMR", "AML"],
        "key_attributes": ["dribbling", "finishing", "long_shots", "technique", "off_the_ball"],
    },
    "INSIDE_FWD_ATTACK": {
        "label_ru": "Инсайд (атака)",
        "phase": "with_ball",
        "positions": ["AM R", "AM L", "AMR", "AML"],
        "key_attributes": ["finishing", "dribbling", "acceleration", "technique", "off_the_ball"],
    },
    "TREQ": {
        "label_ru": "Треквартиста",
        "phase": "with_ball",
        "positions": ["AM C", "AMC"],
        "key_attributes": ["technique", "vision", "passing", "first_touch", "finishing"],
    },
    # Strikers
    "POACHER": {
        "label_ru": "Завершитель",
        "phase": "with_ball",
        "positions": ["ST", "ST C"],
        "key_attributes": ["finishing", "off_the_ball", "acceleration", "composure", "anticipation"],
    },
    "TARGET_ATTACK": {
        "label_ru": "Целевой форвард (атака)",
        "phase": "with_ball",
        "positions": ["ST", "ST C"],
        "key_attributes": ["strength", "jumping_reach", "finishing", "heading", "bravery"],
    },
    "DLF_SUPPORT": {
        "label_ru": "Оттянутый нападающий",
        "phase": "with_ball",
        "positions": ["ST", "ST C"],
        "key_attributes": ["passing", "technique", "off_the_ball", "vision", "first_touch"],
    },
    "ADV_FWD": {
        "label_ru": "Мобильный форвард",
        "phase": "with_ball",
        "positions": ["ST", "ST C"],
        "key_attributes": ["finishing", "acceleration", "dribbling", "off_the_ball", "composure"],
    },
    "FALSE_NINE": {
        "label_ru": "Ложная девятка",
        "phase": "with_ball",
        "positions": ["ST", "ST C", "AM C"],
        "key_attributes": ["passing", "technique", "vision", "first_touch", "off_the_ball"],
    },
    "PRESSING_FWD_ATTACK": {
        "label_ru": "Форвард-прессингёр (атака)",
        "phase": "universal",
        "positions": ["ST", "ST C"],
        "key_attributes": ["tackling", "stamina", "acceleration", "finishing", "aggression"],
    },
}


def roles_for_position(position: str) -> list:
    """Return list of role codes valid for this position string.

    Position strings come in FM-style: "GK", "D C", "AM/ST RL",
    "M/AM LC". We split on slashes / spaces and accept any role whose
    `positions` list contains any of the resulting tokens.
    """
    if not position:
        return []
    raw = position.strip().upper()
    # Build a set of tokens to test against role.positions entries.
    tokens: set[str] = {raw}
    # Split on slashes for multi-position players
    for chunk in raw.replace("  ", " ").split():
        tokens.add(chunk)
    for slash_part in raw.split("/"):
        tokens.add(slash_part.strip())
    # Also produce zone+side combinations: "AM/ST RL" -> {AM R, AM L, ST R, ST L}
    parts = raw.split()
    if len(parts) >= 2:
        zones = parts[0].split("/")
        sides = parts[1] if len(parts[1]) <= 3 and all(c in "RLC" for c in parts[1]) else ""
        if sides:
            for z in zones:
                for s in sides:
                    tokens.add(f"{z} {s}")
    out = []
    seen = set()
    for code, role in TRAINING_ROLES.items():
        if code in seen:
            continue
        for p in role["positions"]:
            pu = p.upper()
            for t in tokens:
                if not t:
                    continue
                if pu == t or pu in t or t in pu:
                    out.append({"code": code, **role})
                    seen.add(code)
                    break
            if code in seen:
                break
    return out


def auto_pick_role(position: str) -> str:
    """Pick a sensible default training role for a CSV position string."""
    candidates = roles_for_position(position)
    if not candidates:
        return "B2B"
    # Prefer support-duty universal roles if available.
    for c in candidates:
        if c["code"].endswith("_SUPPORT"):
            return c["code"]
    return candidates[0]["code"]
