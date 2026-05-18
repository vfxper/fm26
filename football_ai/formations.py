"""
Top 15 football formations with player positions.
Positions in meters on 105x68 pitch. Player 0 = GK always.
Attacking direction: left to right (x=0 own goal, x=105 opponent goal).
"""

import numpy as np

FIELD_W = 105.0
FIELD_H = 68.0

# All formations: 11 positions [x, y] in meters
FORMATIONS = {
    "4-4-2": np.array([
        [5, 34],      # GK
        [22, 10],     # LB
        [20, 27],     # CB
        [20, 41],     # CB
        [22, 58],     # RB
        [45, 10],     # LM
        [42, 27],     # CM
        [42, 41],     # CM
        [45, 58],     # RM
        [68, 27],     # ST
        [68, 41],     # ST
    ], dtype=np.float32),

    "4-3-3": np.array([
        [5, 34],      # GK
        [22, 10],     # LB
        [20, 27],     # CB
        [20, 41],     # CB
        [22, 58],     # RB
        [38, 34],     # DM
        [48, 22],     # CM
        [48, 46],     # CM
        [70, 8],      # LW
        [70, 60],     # RW
        [73, 34],     # ST
    ], dtype=np.float32),

    "4-2-3-1": np.array([
        [5, 34],      # GK
        [22, 10],     # LB
        [20, 27],     # CB
        [20, 41],     # CB
        [22, 58],     # RB
        [36, 27],     # DM
        [36, 41],     # DM
        [55, 10],     # LAM
        [55, 34],     # CAM
        [55, 58],     # RAM
        [73, 34],     # ST
    ], dtype=np.float32),

    "3-5-2": np.array([
        [5, 34],      # GK
        [20, 20],     # CB
        [18, 34],     # CB
        [20, 48],     # CB
        [42, 5],      # LWB
        [40, 24],     # CM
        [38, 34],     # DM
        [40, 44],     # CM
        [42, 63],     # RWB
        [68, 27],     # ST
        [68, 41],     # ST
    ], dtype=np.float32),

    "4-1-4-1": np.array([
        [5, 34],      # GK
        [22, 10],     # LB
        [20, 27],     # CB
        [20, 41],     # CB
        [22, 58],     # RB
        [34, 34],     # DM
        [50, 10],     # LM
        [48, 27],     # CM
        [48, 41],     # CM
        [50, 58],     # RM
        [73, 34],     # ST
    ], dtype=np.float32),

    "4-4-2-diamond": np.array([
        [5, 34],      # GK
        [22, 10],     # LB
        [20, 27],     # CB
        [20, 41],     # CB
        [22, 58],     # RB
        [35, 34],     # DM
        [45, 18],     # LCM
        [45, 50],     # RCM
        [55, 34],     # CAM
        [70, 24],     # ST
        [70, 44],     # ST
    ], dtype=np.float32),

    "3-4-3": np.array([
        [5, 34],      # GK
        [20, 17],     # CB
        [18, 34],     # CB
        [20, 51],     # CB
        [42, 8],      # LWB
        [40, 27],     # CM
        [40, 41],     # CM
        [42, 60],     # RWB
        [68, 12],     # LW
        [73, 34],     # ST
        [68, 56],     # RW
    ], dtype=np.float32),

    "5-3-2": np.array([
        [5, 34],      # GK
        [25, 5],      # LWB
        [20, 20],     # CB
        [18, 34],     # CB
        [20, 48],     # CB
        [25, 63],     # RWB
        [42, 20],     # CM
        [40, 34],     # CM
        [42, 48],     # CM
        [68, 27],     # ST
        [68, 41],     # ST
    ], dtype=np.float32),

    "4-3-2-1": np.array([
        [5, 34],      # GK
        [22, 10],     # LB
        [20, 27],     # CB
        [20, 41],     # CB
        [22, 58],     # RB
        [38, 20],     # CM
        [36, 34],     # DM
        [38, 48],     # CM
        [56, 24],     # AM
        [56, 44],     # AM
        [73, 34],     # ST
    ], dtype=np.float32),

    "4-5-1": np.array([
        [5, 34],      # GK
        [22, 10],     # LB
        [20, 27],     # CB
        [20, 41],     # CB
        [22, 58],     # RB
        [45, 8],      # LM
        [42, 24],     # CM
        [38, 34],     # DM
        [42, 44],     # CM
        [45, 60],     # RM
        [73, 34],     # ST
    ], dtype=np.float32),

    "4-1-2-1-2": np.array([
        [5, 34],      # GK
        [22, 10],     # LB
        [20, 27],     # CB
        [20, 41],     # CB
        [22, 58],     # RB
        [34, 34],     # DM
        [46, 22],     # CM
        [46, 46],     # CM
        [58, 34],     # CAM
        [70, 24],     # ST
        [70, 44],     # ST
    ], dtype=np.float32),

    "3-4-1-2": np.array([
        [5, 34],      # GK
        [20, 17],     # CB
        [18, 34],     # CB
        [20, 51],     # CB
        [40, 5],      # LWB
        [38, 27],     # CM
        [38, 41],     # CM
        [40, 63],     # RWB
        [55, 34],     # CAM
        [70, 24],     # ST
        [70, 44],     # ST
    ], dtype=np.float32),

    "5-4-1": np.array([
        [5, 34],      # GK
        [25, 5],      # LWB
        [20, 20],     # CB
        [18, 34],     # CB
        [20, 48],     # CB
        [25, 63],     # RWB
        [45, 12],     # LM
        [42, 28],     # CM
        [42, 40],     # CM
        [45, 56],     # RM
        [73, 34],     # ST
    ], dtype=np.float32),

    "4-3-1-2": np.array([
        [5, 34],      # GK
        [22, 10],     # LB
        [20, 27],     # CB
        [20, 41],     # CB
        [22, 58],     # RB
        [38, 20],     # CM
        [36, 34],     # DM
        [38, 48],     # CM
        [55, 34],     # CAM
        [70, 24],     # ST
        [70, 44],     # ST
    ], dtype=np.float32),

    "4-4-1-1": np.array([
        [5, 34],      # GK
        [22, 10],     # LB
        [20, 27],     # CB
        [20, 41],     # CB
        [22, 58],     # RB
        [44, 10],     # LM
        [42, 27],     # CM
        [42, 41],     # CM
        [44, 58],     # RM
        [60, 34],     # SS/CAM
        [73, 34],     # ST
    ], dtype=np.float32),
}


def get_formation(name):
    """Get formation by name. Returns (11, 2) numpy array."""
    return FORMATIONS.get(name, FORMATIONS["4-4-2"]).copy()


def get_formation_mirrored(name):
    """Get formation mirrored for away team (attacking left)."""
    f = get_formation(name)
    f[:, 0] = FIELD_W - f[:, 0]
    return f


def get_random_formation(rng=None):
    """Get a random formation name."""
    names = list(FORMATIONS.keys())
    if rng is not None:
        return names[rng.integers(len(names))]
    return names[np.random.randint(len(names))]


def get_all_formation_names():
    """Get list of all formation names."""
    return list(FORMATIONS.keys())


# Role names per formation position index
ROLE_NAMES_BY_FORMATION = {
    "4-4-2": ['GK', 'LB', 'CB', 'CB', 'RB', 'LM', 'CM', 'CM', 'RM', 'ST', 'ST'],
    "4-3-3": ['GK', 'LB', 'CB', 'CB', 'RB', 'DM', 'CM', 'CM', 'LW', 'RW', 'ST'],
    "4-2-3-1": ['GK', 'LB', 'CB', 'CB', 'RB', 'DM', 'DM', 'LAM', 'CAM', 'RAM', 'ST'],
    "3-5-2": ['GK', 'CB', 'CB', 'CB', 'LWB', 'CM', 'DM', 'CM', 'RWB', 'ST', 'ST'],
    "4-1-4-1": ['GK', 'LB', 'CB', 'CB', 'RB', 'DM', 'LM', 'CM', 'CM', 'RM', 'ST'],
    "4-4-2-diamond": ['GK', 'LB', 'CB', 'CB', 'RB', 'DM', 'LCM', 'RCM', 'CAM', 'ST', 'ST'],
    "3-4-3": ['GK', 'CB', 'CB', 'CB', 'LWB', 'CM', 'CM', 'RWB', 'LW', 'ST', 'RW'],
    "5-3-2": ['GK', 'LWB', 'CB', 'CB', 'CB', 'RWB', 'CM', 'CM', 'CM', 'ST', 'ST'],
    "4-3-2-1": ['GK', 'LB', 'CB', 'CB', 'RB', 'CM', 'DM', 'CM', 'AM', 'AM', 'ST'],
    "4-5-1": ['GK', 'LB', 'CB', 'CB', 'RB', 'LM', 'CM', 'DM', 'CM', 'RM', 'ST'],
    "4-1-2-1-2": ['GK', 'LB', 'CB', 'CB', 'RB', 'DM', 'CM', 'CM', 'CAM', 'ST', 'ST'],
    "3-4-1-2": ['GK', 'CB', 'CB', 'CB', 'LWB', 'CM', 'CM', 'RWB', 'CAM', 'ST', 'ST'],
    "5-4-1": ['GK', 'LWB', 'CB', 'CB', 'CB', 'RWB', 'LM', 'CM', 'CM', 'RM', 'ST'],
    "4-3-1-2": ['GK', 'LB', 'CB', 'CB', 'RB', 'CM', 'DM', 'CM', 'CAM', 'ST', 'ST'],
    "4-4-1-1": ['GK', 'LB', 'CB', 'CB', 'RB', 'LM', 'CM', 'CM', 'RM', 'SS', 'ST'],
}
