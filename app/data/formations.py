"""
Formation slot coordinates for the pitch UI.

Each formation defines 11 slots. Each slot has:
- code: short identifier (GK, DR, DC1, DC2, DL, DM, MC1, MC2, AML, AMR, ST)
- pos_csv: which CSV position string fits this slot (used to validate
  drag-drop and to grey-out wrong-position drops)
- x, y: 0..100 grid (x=horizontal across pitch, y=vertical, 0=own goal,
  100=opponent goal)
- label: short Russian label

The frontend renders a 100×100 SVG-style grid scaled to the screen, so
these coordinates translate directly to pixel positions.
"""

FORMATIONS = {
    "4-3-3": [
        {"code": "GK",  "pos_csv": "GK",     "x": 50, "y": 6,  "label": "ВРТ"},
        {"code": "DL",  "pos_csv": "D L",    "x": 18, "y": 22, "label": "ЛЗ"},
        {"code": "DC1", "pos_csv": "D C",    "x": 38, "y": 18, "label": "ЦЗ"},
        {"code": "DC2", "pos_csv": "D C",    "x": 62, "y": 18, "label": "ЦЗ"},
        {"code": "DR",  "pos_csv": "D R",    "x": 82, "y": 22, "label": "ПЗ"},
        {"code": "DM",  "pos_csv": "DM",     "x": 50, "y": 38, "label": "ОПЗ"},
        {"code": "MC1", "pos_csv": "M C",    "x": 30, "y": 50, "label": "ЦПЗ"},
        {"code": "MC2", "pos_csv": "M C",    "x": 70, "y": 50, "label": "ЦПЗ"},
        {"code": "AML", "pos_csv": "AM L",   "x": 18, "y": 75, "label": "ЛВ"},
        {"code": "ST",  "pos_csv": "ST",     "x": 50, "y": 88, "label": "ФРВ"},
        {"code": "AMR", "pos_csv": "AM R",   "x": 82, "y": 75, "label": "ПВ"},
    ],
    "4-4-2": [
        {"code": "GK",  "pos_csv": "GK",   "x": 50, "y": 6,  "label": "ВРТ"},
        {"code": "DL",  "pos_csv": "D L",  "x": 18, "y": 22, "label": "ЛЗ"},
        {"code": "DC1", "pos_csv": "D C",  "x": 38, "y": 18, "label": "ЦЗ"},
        {"code": "DC2", "pos_csv": "D C",  "x": 62, "y": 18, "label": "ЦЗ"},
        {"code": "DR",  "pos_csv": "D R",  "x": 82, "y": 22, "label": "ПЗ"},
        {"code": "ML",  "pos_csv": "M L",  "x": 18, "y": 50, "label": "ЛП"},
        {"code": "MC1", "pos_csv": "M C",  "x": 38, "y": 48, "label": "ЦПЗ"},
        {"code": "MC2", "pos_csv": "M C",  "x": 62, "y": 48, "label": "ЦПЗ"},
        {"code": "MR",  "pos_csv": "M R",  "x": 82, "y": 50, "label": "ПП"},
        {"code": "ST1", "pos_csv": "ST",   "x": 38, "y": 84, "label": "ФРВ"},
        {"code": "ST2", "pos_csv": "ST",   "x": 62, "y": 84, "label": "ФРВ"},
    ],
    "4-2-3-1": [
        {"code": "GK",  "pos_csv": "GK",    "x": 50, "y": 6,  "label": "ВРТ"},
        {"code": "DL",  "pos_csv": "D L",   "x": 18, "y": 22, "label": "ЛЗ"},
        {"code": "DC1", "pos_csv": "D C",   "x": 38, "y": 18, "label": "ЦЗ"},
        {"code": "DC2", "pos_csv": "D C",   "x": 62, "y": 18, "label": "ЦЗ"},
        {"code": "DR",  "pos_csv": "D R",   "x": 82, "y": 22, "label": "ПЗ"},
        {"code": "DM1", "pos_csv": "DM",    "x": 38, "y": 40, "label": "ОПЗ"},
        {"code": "DM2", "pos_csv": "DM",    "x": 62, "y": 40, "label": "ОПЗ"},
        {"code": "AML", "pos_csv": "AM L",  "x": 18, "y": 65, "label": "ЛАП"},
        {"code": "AMC", "pos_csv": "AM C",  "x": 50, "y": 65, "label": "ЦАП"},
        {"code": "AMR", "pos_csv": "AM R",  "x": 82, "y": 65, "label": "ПАП"},
        {"code": "ST",  "pos_csv": "ST",    "x": 50, "y": 88, "label": "ФРВ"},
    ],
    "3-5-2": [
        {"code": "GK",  "pos_csv": "GK",    "x": 50, "y": 6,  "label": "ВРТ"},
        {"code": "DC1", "pos_csv": "D C",   "x": 28, "y": 20, "label": "ЦЗ"},
        {"code": "DC2", "pos_csv": "D C",   "x": 50, "y": 17, "label": "ЦЗ"},
        {"code": "DC3", "pos_csv": "D C",   "x": 72, "y": 20, "label": "ЦЗ"},
        {"code": "WBL", "pos_csv": "WB L",  "x": 12, "y": 45, "label": "ЛЛ"},
        {"code": "MC1", "pos_csv": "M C",   "x": 32, "y": 45, "label": "ЦПЗ"},
        {"code": "MC2", "pos_csv": "M C",   "x": 50, "y": 50, "label": "ЦПЗ"},
        {"code": "MC3", "pos_csv": "M C",   "x": 68, "y": 45, "label": "ЦПЗ"},
        {"code": "WBR", "pos_csv": "WB R",  "x": 88, "y": 45, "label": "ПЛ"},
        {"code": "ST1", "pos_csv": "ST",    "x": 38, "y": 84, "label": "ФРВ"},
        {"code": "ST2", "pos_csv": "ST",    "x": 62, "y": 84, "label": "ФРВ"},
    ],
    "3-4-3": [
        {"code": "GK",  "pos_csv": "GK",    "x": 50, "y": 6,  "label": "ВРТ"},
        {"code": "DC1", "pos_csv": "D C",   "x": 28, "y": 20, "label": "ЦЗ"},
        {"code": "DC2", "pos_csv": "D C",   "x": 50, "y": 17, "label": "ЦЗ"},
        {"code": "DC3", "pos_csv": "D C",   "x": 72, "y": 20, "label": "ЦЗ"},
        {"code": "WBL", "pos_csv": "WB L",  "x": 12, "y": 45, "label": "ЛЛ"},
        {"code": "MC1", "pos_csv": "M C",   "x": 38, "y": 48, "label": "ЦПЗ"},
        {"code": "MC2", "pos_csv": "M C",   "x": 62, "y": 48, "label": "ЦПЗ"},
        {"code": "WBR", "pos_csv": "WB R",  "x": 88, "y": 45, "label": "ПЛ"},
        {"code": "AML", "pos_csv": "AM L",  "x": 18, "y": 78, "label": "ЛВ"},
        {"code": "ST",  "pos_csv": "ST",    "x": 50, "y": 86, "label": "ФРВ"},
        {"code": "AMR", "pos_csv": "AM R",  "x": 82, "y": 78, "label": "ПВ"},
    ],
    "5-3-2": [
        {"code": "GK",  "pos_csv": "GK",   "x": 50, "y": 6,  "label": "ВРТ"},
        {"code": "WBL", "pos_csv": "WB L", "x": 10, "y": 24, "label": "ЛЛ"},
        {"code": "DC1", "pos_csv": "D C",  "x": 30, "y": 18, "label": "ЦЗ"},
        {"code": "DC2", "pos_csv": "D C",  "x": 50, "y": 16, "label": "ЦЗ"},
        {"code": "DC3", "pos_csv": "D C",  "x": 70, "y": 18, "label": "ЦЗ"},
        {"code": "WBR", "pos_csv": "WB R", "x": 90, "y": 24, "label": "ПЛ"},
        {"code": "MC1", "pos_csv": "M C",  "x": 30, "y": 50, "label": "ЦПЗ"},
        {"code": "MC2", "pos_csv": "M C",  "x": 50, "y": 50, "label": "ЦПЗ"},
        {"code": "MC3", "pos_csv": "M C",  "x": 70, "y": 50, "label": "ЦПЗ"},
        {"code": "ST1", "pos_csv": "ST",   "x": 38, "y": 84, "label": "ФРВ"},
        {"code": "ST2", "pos_csv": "ST",   "x": 62, "y": 84, "label": "ФРВ"},
    ],
    "4-1-4-1": [
        {"code": "GK",  "pos_csv": "GK",   "x": 50, "y": 6,  "label": "ВРТ"},
        {"code": "DL",  "pos_csv": "D L",  "x": 18, "y": 22, "label": "ЛЗ"},
        {"code": "DC1", "pos_csv": "D C",  "x": 38, "y": 18, "label": "ЦЗ"},
        {"code": "DC2", "pos_csv": "D C",  "x": 62, "y": 18, "label": "ЦЗ"},
        {"code": "DR",  "pos_csv": "D R",  "x": 82, "y": 22, "label": "ПЗ"},
        {"code": "DM",  "pos_csv": "DM",   "x": 50, "y": 35, "label": "ОПЗ"},
        {"code": "ML",  "pos_csv": "M L",  "x": 18, "y": 56, "label": "ЛП"},
        {"code": "MC1", "pos_csv": "M C",  "x": 38, "y": 54, "label": "ЦПЗ"},
        {"code": "MC2", "pos_csv": "M C",  "x": 62, "y": 54, "label": "ЦПЗ"},
        {"code": "MR",  "pos_csv": "M R",  "x": 82, "y": 56, "label": "ПП"},
        {"code": "ST",  "pos_csv": "ST",   "x": 50, "y": 88, "label": "ФРВ"},
    ],
}


def slots(formation: str):
    return FORMATIONS.get(formation, FORMATIONS["4-3-3"])
