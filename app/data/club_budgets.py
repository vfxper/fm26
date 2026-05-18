"""
All clubs from top 10 leagues with realistic budgets.
201 clubs total. Format: (english_name, scouting_budget, transfer_budget, league)
"""

CLUBS = [
    # === Premier League 2025/26 (20) ===
    # In: Sunderland, Leeds United, Burnley
    # Out: Leicester City, Ipswich Town, Southampton
    # Numbers per user table: scouting_budget €/week, transfer_budget transfer £
    ("Manchester City",   1_000_000, 120_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Liverpool",           980_000, 110_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Arsenal",             940_000, 100_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Manchester United",   910_000,  95_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Chelsea",             870_000,  95_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Newcastle United",    820_000,  80_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Tottenham Hotspur",   780_000,  70_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Aston Villa",         730_000,  60_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("West Ham United",     680_000,  50_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Brighton",            630_000,  55_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Crystal Palace",      580_000,  32_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Brentford",           540_000,  40_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Wolverhampton",       500_000,  35_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Fulham",              460_000,  35_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Nottingham Forest",   420_000,  40_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Everton",             380_000,  28_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Burnley",             350_000,  22_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Leeds United",        320_000,  20_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Sunderland",          290_000,  18_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    ("Sheffield United",    270_000,  16_000_000, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"),
    # === La Liga 2025/26 (20) ===
    # In: Levante, Elche, Real Oviedo
    # Out: Valladolid (kept Girona/Las Palmas as CSV has them)
    ("R. Madrid",         1_000_000, 90_000_000, "🇪🇸 La Liga"),
    ("Barcelona",           960_000, 80_000_000, "🇪🇸 La Liga"),
    ("A. Madrid",           900_000, 50_000_000, "🇪🇸 La Liga"),
    ("Sevilla",             780_000, 25_000_000, "🇪🇸 La Liga"),
    ("Real Sociedad",       730_000, 35_000_000, "🇪🇸 La Liga"),
    ("Real Betis",          670_000, 22_000_000, "🇪🇸 La Liga"),
    ("Villarreal",          620_000, 30_000_000, "🇪🇸 La Liga"),
    ("Athletic Bilbao",     590_000, 25_000_000, "🇪🇸 La Liga"),
    ("Valencia",            540_000, 18_000_000, "🇪🇸 La Liga"),
    ("Osasuna",             490_000, 14_000_000, "🇪🇸 La Liga"),
    ("Getafe",              450_000, 11_000_000, "🇪🇸 La Liga"),
    ("Celta Vigo",          420_000, 15_000_000, "🇪🇸 La Liga"),
    ("Rayo Vallecano",      390_000,  9_000_000, "🇪🇸 La Liga"),
    ("Mallorca",            360_000, 11_000_000, "🇪🇸 La Liga"),
    ("Alaves",              330_000,  8_500_000, "🇪🇸 La Liga"),
    ("Las Palmas",          300_000,  7_000_000, "🇪🇸 La Liga"),
    ("Girona",              280_000, 16_000_000, "🇪🇸 La Liga"),
    ("Espanyol",            260_000, 10_000_000, "🇪🇸 La Liga"),
    ("Levante",             240_000,  6_500_000, "🇪🇸 La Liga"),
    ("Elche",               220_000,  6_000_000, "🇪🇸 La Liga"),
    # === Bundesliga 2025/26 (18) ===
    # In: Köln, Hamburg
    # Out: Holstein Kiel, Bochum
    ("Bayern Munich",     1_000_000, 100_000_000, "🇩🇪 Bundesliga"),
    ("Borussia Dortmund",   920_000,  50_000_000, "🇩🇪 Bundesliga"),
    ("RB Leipzig",          860_000,  55_000_000, "🇩🇪 Bundesliga"),
    ("Bayer Leverkusen",    810_000,  50_000_000, "🇩🇪 Bundesliga"),
    ("Eintracht Frankfurt", 750_000,  35_000_000, "🇩🇪 Bundesliga"),
    ("Wolfsburg",           690_000,  40_000_000, "🇩🇪 Bundesliga"),
    ("Borussia Monchengladbach", 630_000, 28_000_000, "🇩🇪 Bundesliga"),
    ("Stuttgart",           570_000,  32_000_000, "🇩🇪 Bundesliga"),
    ("Hoffenheim",          520_000,  25_000_000, "🇩🇪 Bundesliga"),
    ("Freiburg",            480_000,  20_000_000, "🇩🇪 Bundesliga"),
    ("Werder Bremen",       450_000,  18_000_000, "🇩🇪 Bundesliga"),
    ("Augsburg",            420_000,  12_000_000, "🇩🇪 Bundesliga"),
    ("Union Berlin",        390_000,  22_000_000, "🇩🇪 Bundesliga"),
    ("Mainz 05",            360_000,  15_000_000, "🇩🇪 Bundesliga"),
    ("St. Pauli",           330_000,   9_000_000, "🇩🇪 Bundesliga"),
    ("Heidenheim",          300_000,   8_000_000, "🇩🇪 Bundesliga"),
    ("FC Koln",             270_000,  12_000_000, "🇩🇪 Bundesliga"),
    ("Hamburger SV",        240_000,  11_000_000, "🇩🇪 Bundesliga"),
    # === Serie A 2025/26 (20) ===
    # In: Sassuolo, Pisa, Cremonese
    # Out: Empoli, Venezia, Monza
    ("Inter Milan",       1_000_000, 60_000_000, "🇮🇹 Serie A"),
    ("Juventus",            950_000, 60_000_000, "🇮🇹 Serie A"),
    ("AC Milan",            910_000, 50_000_000, "🇮🇹 Serie A"),
    ("Napoli",              850_000, 45_000_000, "🇮🇹 Serie A"),
    ("Roma",                790_000, 30_000_000, "🇮🇹 Serie A"),
    ("Lazio",               730_000, 28_000_000, "🇮🇹 Serie A"),
    ("Atalanta",            680_000, 35_000_000, "🇮🇹 Serie A"),
    ("Fiorentina",          620_000, 25_000_000, "🇮🇹 Serie A"),
    ("Torino",              560_000, 18_000_000, "🇮🇹 Serie A"),
    ("Bologna",             520_000, 22_000_000, "🇮🇹 Serie A"),
    ("Udinese",             480_000, 16_000_000, "🇮🇹 Serie A"),
    ("Genoa",               440_000, 15_000_000, "🇮🇹 Serie A"),
    ("Lecce",               400_000,  8_000_000, "🇮🇹 Serie A"),
    ("Cagliari",            370_000, 10_000_000, "🇮🇹 Serie A"),
    ("Parma",               340_000, 12_000_000, "🇮🇹 Serie A"),
    ("Como",                310_000, 15_000_000, "🇮🇹 Serie A"),
    ("Verona",              280_000,  9_000_000, "🇮🇹 Serie A"),
    ("Sassuolo",            250_000, 11_000_000, "🇮🇹 Serie A"),
    ("Pisa",                220_000,  7_000_000, "🇮🇹 Serie A"),
    ("Cremonese",           190_000,  6_000_000, "🇮🇹 Serie A"),
    # === Ligue 1 2025/26 (18) ===
    ("Paris Saint-Germain", 1_000_000, 150_000_000, "🇫🇷 Ligue 1"),
    ("Marseille",             870_000,  35_000_000, "🇫🇷 Ligue 1"),
    ("Lyon",                  800_000,  30_000_000, "🇫🇷 Ligue 1"),
    ("Monaco",                760_000,  40_000_000, "🇫🇷 Ligue 1"),
    ("Lille",                 700_000,  28_000_000, "🇫🇷 Ligue 1"),
    ("Rennes",                640_000,  32_000_000, "🇫🇷 Ligue 1"),
    ("Nice",                  590_000,  25_000_000, "🇫🇷 Ligue 1"),
    ("Lens",                  540_000,  24_000_000, "🇫🇷 Ligue 1"),
    ("Strasbourg",            490_000,  18_000_000, "🇫🇷 Ligue 1"),
    ("Nantes",                450_000,  10_000_000, "🇫🇷 Ligue 1"),
    ("Reims",                 410_000,  15_000_000, "🇫🇷 Ligue 1"),
    ("Montpellier",           380_000,  12_000_000, "🇫🇷 Ligue 1"),
    ("Brest",                 350_000,   9_000_000, "🇫🇷 Ligue 1"),
    ("Le Havre",              320_000,   7_000_000, "🇫🇷 Ligue 1"),
    ("Toulouse",              290_000,  11_000_000, "🇫🇷 Ligue 1"),
    ("Auxerre",               270_000,   8_000_000, "🇫🇷 Ligue 1"),
    ("Angers",                250_000,   6_000_000, "🇫🇷 Ligue 1"),
    ("Saint-Etienne",         230_000,  10_000_000, "🇫🇷 Ligue 1"),
    # === Liga Portugal 2025/26 (18) ===
    ("Benfica",           1_000_000, 25_000_000, "🇵🇹 Liga Portugal"),
    ("Porto",               940_000, 22_000_000, "🇵🇹 Liga Portugal"),
    ("Sporting CP",         890_000, 20_000_000, "🇵🇹 Liga Portugal"),
    ("Braga",               710_000, 15_000_000, "🇵🇹 Liga Portugal"),
    ("Santa Clara",         580_000,  3_500_000, "🇵🇹 Liga Portugal"),
    ("Vitoria Guimaraes",   520_000,  6_000_000, "🇵🇹 Liga Portugal"),
    ("Famalicao",           460_000,  4_500_000, "🇵🇹 Liga Portugal"),
    ("Casa Pia",            400_000,  3_000_000, "🇵🇹 Liga Portugal"),
    ("Estoril",             350_000,  3_000_000, "🇵🇹 Liga Portugal"),
    ("Rio Ave",             320_000,  3_000_000, "🇵🇹 Liga Portugal"),
    ("Arouca",              290_000,  2_500_000, "🇵🇹 Liga Portugal"),
    ("Gil Vicente",         270_000,  3_000_000, "🇵🇹 Liga Portugal"),
    ("Nacional",            250_000,  1_800_000, "🇵🇹 Liga Portugal"),
    ("AVS",                 230_000,  2_000_000, "🇵🇹 Liga Portugal"),
    ("Estrela Amadora",     210_000,  1_800_000, "🇵🇹 Liga Portugal"),
    ("Moreirense",          190_000,  2_200_000, "🇵🇹 Liga Portugal"),
    ("Tondela",             170_000,  1_700_000, "🇵🇹 Liga Portugal"),
    ("Alverca",             150_000,  1_500_000, "🇵🇹 Liga Portugal"),
    # === Eredivisie 2025/26 (18) ===
    ("Ajax",              1_000_000, 20_000_000, "🇳🇱 Eredivisie"),
    ("PSV Eindhoven",       920_000, 18_000_000, "🇳🇱 Eredivisie"),
    ("Feyenoord",           880_000, 17_000_000, "🇳🇱 Eredivisie"),
    ("AZ Alkmaar",          700_000, 10_000_000, "🇳🇱 Eredivisie"),
    ("Twente",              580_000,  8_000_000, "🇳🇱 Eredivisie"),
    ("Utrecht",             500_000,  6_000_000, "🇳🇱 Eredivisie"),
    ("NEC Nijmegen",        430_000,  3_200_000, "🇳🇱 Eredivisie"),
    ("Go Ahead Eagles",     380_000,  2_800_000, "🇳🇱 Eredivisie"),
    ("Heerenveen",          350_000,  3_800_000, "🇳🇱 Eredivisie"),
    ("Sparta Rotterdam",    320_000,  3_500_000, "🇳🇱 Eredivisie"),
    ("Fortuna Sittard",     290_000,  2_000_000, "🇳🇱 Eredivisie"),
    ("Almere City",         260_000,  2_000_000, "🇳🇱 Eredivisie"),
    ("Zwolle",              240_000,  2_100_000, "🇳🇱 Eredivisie"),
    ("Heracles",            220_000,  2_200_000, "🇳🇱 Eredivisie"),
    ("RKC Waalwijk",        200_000,  2_200_000, "🇳🇱 Eredivisie"),
    ("NAC Breda",           180_000,  2_500_000, "🇳🇱 Eredivisie"),
    ("Volendam",            160_000,  1_800_000, "🇳🇱 Eredivisie"),
    ("Excelsior",           140_000,  1_600_000, "🇳🇱 Eredivisie"),
    # === Brazil Série A 2025 (20) ===
    ("Flamengo",          1_000_000, 20_000_000, "🇧🇷 Brasileirão"),
    ("Palmeiras",           930_000, 19_000_000, "🇧🇷 Brasileirão"),
    ("Sao Paulo",           860_000, 17_000_000, "🇧🇷 Brasileirão"),
    ("Corinthians",         800_000, 15_000_000, "🇧🇷 Brasileirão"),
    ("Internacional",       730_000, 12_000_000, "🇧🇷 Brasileirão"),
    ("Gremio",              670_000, 11_000_000, "🇧🇷 Brasileirão"),
    ("Atletico Mineiro",    610_000, 11_000_000, "🇧🇷 Brasileirão"),
    ("Fluminense",          560_000,  9_000_000, "🇧🇷 Brasileirão"),
    ("Botafogo",            520_000,  9_000_000, "🇧🇷 Brasileirão"),
    ("RB Bragantino",       480_000,  8_000_000, "🇧🇷 Brasileirão"),
    ("Athletico Paranaense",440_000,  7_500_000, "🇧🇷 Brasileirão"),
    ("Fortaleza",           400_000,  6_500_000, "🇧🇷 Brasileirão"),
    ("Cruzeiro",            370_000,  7_000_000, "🇧🇷 Brasileirão"),
    ("Bahia",               340_000,  6_000_000, "🇧🇷 Brasileirão"),
    ("Vasco da Gama",       310_000,  5_500_000, "🇧🇷 Brasileirão"),
    ("Santos",              280_000,  6_500_000, "🇧🇷 Brasileirão"),
    ("Ceara",               250_000,  4_000_000, "🇧🇷 Brasileirão"),
    ("Juventude",           230_000,  3_500_000, "🇧🇷 Brasileirão"),
    ("Vitoria",             210_000,  3_500_000, "🇧🇷 Brasileirão"),
    ("Sport Recife",        190_000,  3_200_000, "🇧🇷 Brasileirão"),
    # === MLS 2025 (30) ===
    ("Inter Miami",       1_000_000,  8_000_000, "🇺🇸 MLS"),
    ("LAFC",                950_000,  7_500_000, "🇺🇸 MLS"),
    ("Toronto FC",          900_000,  6_500_000, "🇺🇸 MLS"),
    ("Atlanta United",      890_000,  7_500_000, "🇺🇸 MLS"),
    ("LA Galaxy",           860_000,  7_000_000, "🇺🇸 MLS"),
    ("Nashville SC",        820_000,  4_500_000, "🇺🇸 MLS"),
    ("New York Red Bulls",  780_000,  4_500_000, "🇺🇸 MLS"),
    ("Vancouver Whitecaps", 750_000,  3_500_000, "🇺🇸 MLS"),
    ("New York City FC",    720_000,  6_000_000, "🇺🇸 MLS"),
    ("FC Cincinnati",       690_000,  4_500_000, "🇺🇸 MLS"),
    ("Columbus Crew",       660_000,  4_500_000, "🇺🇸 MLS"),
    ("Portland Timbers",    630_000,  3_500_000, "🇺🇸 MLS"),
    ("Real Salt Lake",      600_000,  3_000_000, "🇺🇸 MLS"),
    ("New England Revolution", 570_000, 3_200_000, "🇺🇸 MLS"),
    ("Colorado Rapids",     540_000,  2_800_000, "🇺🇸 MLS"),
    ("Charlotte FC",        510_000,  3_500_000, "🇺🇸 MLS"),
    ("Minnesota United",    480_000,  3_000_000, "🇺🇸 MLS"),
    ("Houston Dynamo",      450_000,  2_500_000, "🇺🇸 MLS"),
    ("DC United",           420_000,  2_000_000, "🇺🇸 MLS"),
    ("San Jose Earthquakes",390_000,  1_800_000, "🇺🇸 MLS"),
    ("Chicago Fire",        360_000,  2_200_000, "🇺🇸 MLS"),
    ("Orlando City",        340_000,  4_500_000, "🇺🇸 MLS"),
    ("Austin FC",           320_000,  2_500_000, "🇺🇸 MLS"),
    ("FC Dallas",           300_000,  2_800_000, "🇺🇸 MLS"),
    ("Sporting Kansas City",280_000,  2_000_000, "🇺🇸 MLS"),
    ("Seattle Sounders",    260_000,  4_500_000, "🇺🇸 MLS"),
    ("Philadelphia Union",  240_000,  2_500_000, "🇺🇸 MLS"),
    ("St. Louis City SC",   220_000,  3_000_000, "🇺🇸 MLS"),
    ("CF Montreal",         200_000,  2_000_000, "🇺🇸 MLS"),
    ("San Diego FC",        180_000,  3_500_000, "🇺🇸 MLS"),
    # === Saudi Pro League 2025/26 (18) ===
    ("Al-Hilal",          1_000_000, 80_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Nassr",            970_000, 70_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Ittihad",          930_000, 60_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Ahli",             890_000, 55_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Shabab",           830_000, 40_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Ettifaq",          770_000, 25_000_000, "🇸🇦 Saudi Pro League"),
    ("Abha",                710_000,  8_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Taawoun",          650_000, 20_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Fateh",            590_000,  9_000_000, "🇸🇦 Saudi Pro League"),
    ("Damac",               540_000, 18_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Raed",             490_000, 10_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Khaleej",          440_000,  8_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Wahda",            390_000, 12_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Okhdood",          340_000,  6_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Kholood",          290_000, 10_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Orubah",           250_000,  8_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Qadsiah",          210_000, 25_000_000, "🇸🇦 Saudi Pro League"),
    ("Al-Adalah",           180_000,  4_500_000, "🇸🇦 Saudi Pro League"),
]

# Build lookup dict
CLUB_BUDGETS = {name: (scout, transfer) for name, scout, transfer, _ in CLUBS}

# CSV name -> CLUBS name mapping (CSV uses different names for some clubs).
# This map is the source of truth — it's built from the actual CSV club
# strings we saw in 2600球员属性.csv.
CSV_NAME_MAP = {
    # Premier League — most exact match. Only those needing remap:
    "Brighton & Hove Albion": "Brighton",
    "Wolverhampton Wanderers": "Wolverhampton",
    "AFC Bournemouth": "Bournemouth",

    # La Liga
    "Real Madrid": "R. Madrid",
    "Atlético de Madrid": "A. Madrid",
    "Atlético Madrid": "A. Madrid",
    "Sevilla": "Sevilla",                       # 44 players — direct match
    "Real Hispalis": "Real Betis",              # CSV anonymises Real Betis (66 players)
    "Real San Sebastián": "Real Sociedad",      # CSV anonymises Sociedad
    "Atlético Pamplona": "Osasuna",             # CSV alias for Osasuna
    "Leganés": "Leganes",                       # accent variant (30 players)
    "A. Bilbao": "Athletic Bilbao",
    "Athletic Club": "Athletic Bilbao",
    "Vigo": "Celta Vigo",
    "Vallecano": "Rayo Vallecano",
    "Alavés": "Alaves",                         # accent variant
    "ALA": "Alaves",
    "Levante UD": "Levante",
    "Real Valladolid": "Valladolid",
    "CD Leganés": "Leganes",

    # Bundesliga
    "FC Bayern München": "Bayern Munich",
    "FC Bayern Munich": "Bayern Munich",
    "Bayer 04 Leverkusen": "Bayer Leverkusen",
    "VfL Wolfsburg": "Wolfsburg",
    "Eintracht Frankfurt": "Eintracht Frankfurt",
    "VfB Stuttgart": "Stuttgart",
    "Borussia Mönchengladbach": "Borussia Monchengladbach",
    "TSG 1899 Hoffenheim": "Hoffenheim",
    "1. FC Union Berlin": "Union Berlin",
    "Sport-Club Freiburg": "Freiburg",
    "SC Freiburg": "Freiburg",
    "SV Werder Bremen": "Werder Bremen",
    "1. FSV Mainz 05": "Mainz 05",
    "FC Augsburg": "Augsburg",
    "FC St. Pauli": "St. Pauli",
    "1. FC Heidenheim 1846": "Heidenheim",
    "VfL Bochum 1848": "Bochum",
    "Holstein Kiel": "Holstein Kiel",

    # Serie A
    "Inter": "Inter Milan",
    "Blu-neri Milano": "Inter Milan",          # CSV anonymises Inter
    "FC Internazionale Milano": "Inter Milan",
    "Internazionale": "Inter Milan",
    "Casciavit Milano": "AC Milan",            # CSV anonymises Milan
    "Milan": "AC Milan",
    "AC Milan": "AC Milan",
    "Parthenope": "Napoli",                    # CSV anonymises Napoli
    "SSC Napoli": "Napoli",
    "Bergamo": "Atalanta",                     # CSV anonymises Atalanta
    "Atalanta BC": "Atalanta",
    "Capitolini Celesti": "Lazio",             # CSV anonymises Lazio
    "AS Roma": "Roma",
    "Associazione Sportiva Roma": "Roma",
    "SS Lazio": "Lazio",
    "ACF Fiorentina": "Fiorentina",
    "Bologna FC 1909": "Bologna",
    "Torino FC": "Torino",
    "Associazione Calcio Monza": "Monza",
    "Genoa Cricket and Football Club": "Genoa",
    "Udinese Calcio": "Udinese",
    "Como 1907": "Como",
    "Parma Calcio 1913": "Parma",
    "Cagliari Calcio": "Cagliari",
    "Hellas Verona FC": "Verona",
    "Unione Sportiva Lecce": "Lecce",
    "Venezia Football Club": "Venezia",
    "Empoli Football Club": "Empoli",

    # Ligue 1
    "Paris Saint-Germain": "Paris Saint-Germain",
    "AS Monaco": "Monaco",
    "Olympique de Marseille": "Marseille",
    "Olympique Lyonnais": "Lyon",
    "Stade Rennais Football Club": "Rennes",
    "Stade Rennais FC": "Rennes",
    "LOSC Lille": "Lille",
    "OGC Nice": "Nice",
    "RC Lens": "Lens",
    "RC Strasbourg Alsace": "Strasbourg",
    "Stade de Reims": "Reims",
    "Montpellier Hérault SC": "Montpellier",
    "AS Saint-Étienne": "Saint-Etienne",
    "Saint-Étienne": "Saint-Etienne",
    "Toulouse FC": "Toulouse",
    "FC Nantes": "Nantes",
    "Stade Brestois 29": "Brest",
    "AJ Auxerre": "Auxerre",
    "Havre AC": "Le Havre",
    "Le Havre AC": "Le Havre",
    "Angers SCO": "Angers",

    # Liga Portugal
    "Sport Lisboa e Benfica": "Benfica",
    "Sporting Clube de Portugal": "Sporting CP",
    "Futebol Clube do Porto": "Porto",
    "Sporting Clube de Braga": "Braga",
    "Vitória Sport Clube": "Vitoria Guimaraes",
    "Futebol Clube de Famalicão": "Famalicao",
    "Boavista Futebol Clube - SAD": "Boavista",
    "Gil Vicente Futebol Clube": "Gil Vicente",
    "Rio Ave Futebol Clube": "Rio Ave",
    "Grupo Desportivo Estoril Praia - SAD": "Estoril",
    "Futebol Clube de Arouca": "Arouca",
    "Portimonense Sporting Clube SAD": "Portimonense",
    "Moreirense Futebol Clube": "Moreirense",
    "Casa Pia Atlético Clube": "Casa Pia",
    "Sporting Clube Farense": "Farense",
    "Clube Desportivo Nacional": "Nacional",
    "Santa Clara Açores Futebol": "Santa Clara",
    "AVS Futebol SAD": "AVS",

    # Eredivisie
    "AFC Ajax": "Ajax",
    "Feyenoord Rotterdam": "Feyenoord",
    "PSV": "PSV Eindhoven",
    "AZ": "AZ Alkmaar",
    "FC Twente": "Twente",
    "FC Utrecht": "Utrecht",
    "FC Groningen": "Groningen",
    "sc Heerenveen": "Heerenveen",
    "SC Heerenveen": "Heerenveen",
    "Sparta Rotterdam": "Sparta Rotterdam",
    "N.E.C. Nijmegen": "NEC Nijmegen",
    "Go Ahead Eagles": "Go Ahead Eagles",
    "Willem II": "Willem II",
    "NAC Breda": "NAC Breda",
    "Heracles Almelo": "Heracles",
    "RKC Waalwijk": "RKC Waalwijk",
    "PEC Zwolle": "Zwolle",
    "Almere City FC": "Almere City",
    "Fortuna Sittard": "Fortuna Sittard",

    # Süper Lig
    "Galatasaray A.Ş.": "Galatasaray",
    "Galatasaray SK": "Galatasaray",
    "Fenerbahçe SK": "Fenerbahce",
    "Fenerbahçe S.K.": "Fenerbahce",
    "Fenerbahçe A.Ş.": "Fenerbahce",
    "Beşiktaş JK": "Besiktas",
    "Beşiktaş J.K.": "Besiktas",
    "Beşiktaş A.Ş.": "Besiktas",
    "Trabzonspor A.Ş.": "Trabzonspor",
    "Trabzonspor": "Trabzonspor",
    "Başakşehir Futbol Kulübü": "Istanbul Basaksehir",
    "İstanbul Başakşehir FK": "Istanbul Basaksehir",
    "Adana Demirspor A.Ş.": "Adana Demirspor",
    "Antalyaspor": "Antalyaspor",
    "Konyaspor": "Konyaspor",
    "Gaziantep Futbol Kulübü A.Ş.": "Gaziantep",
    "Kasımpaşa A.Ş.": "Kasimpasa",
    "Kasımpaşa S.K.": "Kasimpasa",
    "Alanyaspor": "Alanyaspor",
    "Samsunspor A.Ş.": "Samsunspor",
    "Hatayspor": "Hatayspor",
    "Fatih Karagümrük A.Ş.": "Fatih Karagumruk",
    "İstanbulspor": "Istanbulspor",
    "İstanbulspor A.Ş.": "Istanbulspor",
    "MKE Ankaragücü": "Ankaragucu",
    "Kayserispor": "Kayserispor",
    "Sivasspor": "Sivasspor",
    "Rizespor A.Ş.": "Rizespor",
    "Bodrum Futbol Kulübü": "Bodrumspor",

    # Saudi Pro League
    "Al-Hilal Saudi Football Club": "Al-Hilal",
    "Al-Nassr Football Club": "Al-Nassr",
    "Al-Ittihad Club": "Al-Ittihad",
    "Al-Ahli Saudi Sport Club": "Al-Ahli",
    "Al-Shabab Football Club": "Al-Shabab",
    "Al-Taawoun Football Club": "Al-Taawoun",
    "Al-Fayha Club": "Al-Fayha",
    "Damac Football Club": "Damac",
    "Al-Raed Saudi Football Club": "Al-Raed",
    "Al-Qadsiah Football Club": "Al-Qadsiah",
    "Al-Kholood Club": "Al-Kholood",
    "Al-Fateh Sports Club": "Al-Fateh",
    "Al-Tai Football Club": "Al-Tai",
    "Al-Riyadh Saudi Club": "Al-Riyadh",

    # MLS
    "Inter Miami CF": "Inter Miami",
    "LA Galaxy": "LA Galaxy",
    "Atlanta United FC": "Atlanta United",
    "New York City FC": "New York City FC",
    "Los Angeles Football Club": "LAFC",
    "Seattle Sounders FC": "Seattle Sounders",
    "Toronto FC": "Toronto FC",
    "Orlando City SC": "Orlando City",
    "Columbus Crew": "Columbus Crew",
    "FC Cincinnati": "FC Cincinnati",
    "Nashville SC": "Nashville SC",
    "Portland Timbers": "Portland Timbers",
    "Charlotte FC": "Charlotte FC",
    "Minnesota United FC": "Minnesota United",
    "FC Dallas": "FC Dallas",
    "Houston Dynamo FC": "Houston Dynamo",
    "Vancouver Whitecaps FC": "Vancouver Whitecaps",
    "Real Salt Lake": "Real Salt Lake",
    "Sporting Kansas City": "Sporting Kansas City",
    "Colorado Rapids": "Colorado Rapids",
    "San Jose Earthquakes": "San Jose Earthquakes",
    "CF Montréal": "CF Montreal",
    "Chicago Fire FC": "Chicago Fire",
    "D.C. United": "DC United",
    "Philadelphia Union": "Philadelphia Union",
    "Austin FC": "Austin FC",
    "St. Louis CITY SC": "St. Louis City SC",
    "San Diego Football Club": "San Diego FC",
}

# Reverse map: CLUBS name -> list of CSV-name aliases (a single CLUBS
# entry can have multiple CSV-name spellings).
CLUBS_TO_CSV: dict[str, list[str]] = {}
for csv_name, clubs_name in CSV_NAME_MAP.items():
    CLUBS_TO_CSV.setdefault(clubs_name, []).append(csv_name)

# Weekly wage budget cap per club (€/week per club total).
# Realistic 2025/26 numbers — top EPL ~3.5M €/week, mid 1-1.5M, bottom 400-700k.
# These are SEPARATE from scouting / transfer budgets (CLUBS tuple).
WAGE_BUDGETS: dict[str, int] = {
    # === Premier League 2025/26 ===
    "Manchester City":     3_700_000, "Liverpool":           3_500_000,
    "Arsenal":             3_400_000, "Manchester United":   3_300_000,
    "Chelsea":             3_200_000, "Newcastle United":    2_500_000,
    "Tottenham Hotspur":   2_400_000, "Aston Villa":         2_200_000,
    "West Ham United":     2_000_000, "Brighton":            1_700_000,
    "Crystal Palace":      1_400_000, "Brentford":           1_300_000,
    "Wolverhampton":       1_200_000, "Fulham":              1_100_000,
    "Nottingham Forest":   1_100_000, "Everton":             1_000_000,
    "Burnley":               850_000, "Leeds United":          800_000,
    "Sunderland":            700_000, "Sheffield United":      650_000,
    # === La Liga 2025/26 ===
    "R. Madrid":           3_500_000, "Barcelona":           3_300_000,
    "A. Madrid":           3_000_000, "Sevilla":             1_700_000,
    "Real Sociedad":       1_600_000, "Real Betis":          1_400_000,
    "Villarreal":          1_300_000, "Athletic Bilbao":     1_300_000,
    "Valencia":            1_200_000, "Osasuna":             1_000_000,
    "Getafe":                900_000, "Celta Vigo":            900_000,
    "Rayo Vallecano":        850_000, "Mallorca":              800_000,
    "Alaves":                700_000, "Las Palmas":            650_000,
    "Girona":                650_000, "Espanyol":              600_000,
    "Levante":               550_000, "Elche":                 500_000,
    # === Bundesliga 2025/26 ===
    "Bayern Munich":       3_200_000, "Borussia Dortmund":   2_800_000,
    "RB Leipzig":          2_500_000, "Bayer Leverkusen":    2_500_000,
    "Eintracht Frankfurt": 2_000_000, "Wolfsburg":           1_800_000,
    "Borussia Monchengladbach": 1_500_000, "Stuttgart":      1_500_000,
    "Hoffenheim":          1_300_000, "Freiburg":            1_200_000,
    "Werder Bremen":       1_000_000, "Augsburg":              900_000,
    "Union Berlin":        1_000_000, "Mainz 05":              850_000,
    "St. Pauli":             700_000, "Heidenheim":            650_000,
    "FC Koln":               700_000, "Hamburger SV":          650_000,
    # === Serie A 2025/26 ===
    "Inter Milan":         3_000_000, "Juventus":            2_900_000,
    "AC Milan":            2_800_000, "Napoli":              2_500_000,
    "Roma":                2_200_000, "Lazio":               1_900_000,
    "Atalanta":            1_700_000, "Fiorentina":          1_400_000,
    "Torino":              1_100_000, "Bologna":             1_100_000,
    "Udinese":               900_000, "Genoa":                 800_000,
    "Lecce":                 700_000, "Cagliari":              700_000,
    "Parma":                 650_000, "Como":                  650_000,
    "Verona":                600_000, "Sassuolo":              600_000,
    "Pisa":                  500_000, "Cremonese":             450_000,
    # === Ligue 1 2025/26 ===
    "Paris Saint-Germain": 4_000_000, "Marseille":           1_900_000,
    "Lyon":                1_700_000, "Monaco":              1_700_000,
    "Lille":               1_500_000, "Rennes":              1_400_000,
    "Nice":                1_300_000, "Lens":                1_100_000,
    "Strasbourg":            900_000, "Nantes":                850_000,
    "Reims":                 800_000, "Montpellier":           750_000,
    "Brest":                 700_000, "Le Havre":              600_000,
    "Toulouse":              700_000, "Auxerre":               600_000,
    "Angers":                550_000, "Saint-Etienne":         700_000,
    # === Liga Portugal 2025/26 ===
    "Benfica":             1_500_000, "Porto":               1_400_000,
    "Sporting CP":         1_300_000, "Braga":                 900_000,
    "Santa Clara":           400_000, "Vitoria Guimaraes":     500_000,
    "Famalicao":             400_000, "Casa Pia":              350_000,
    "Estoril":               300_000, "Rio Ave":               300_000,
    "Arouca":                280_000, "Gil Vicente":           300_000,
    "Nacional":              250_000, "AVS":                   250_000,
    "Estrela Amadora":       230_000, "Moreirense":            260_000,
    "Tondela":               220_000, "Alverca":               200_000,
    # === Eredivisie 2025/26 ===
    "Ajax":                1_400_000, "PSV Eindhoven":       1_300_000,
    "Feyenoord":           1_200_000, "AZ Alkmaar":            900_000,
    "Twente":                700_000, "Utrecht":               600_000,
    "NEC Nijmegen":          500_000, "Go Ahead Eagles":       450_000,
    "Heerenveen":            450_000, "Sparta Rotterdam":      400_000,
    "Fortuna Sittard":       350_000, "Almere City":           300_000,
    "Zwolle":                350_000, "Heracles":              350_000,
    "RKC Waalwijk":          300_000, "NAC Breda":             300_000,
    "Volendam":              280_000, "Excelsior":             260_000,
    # === Brazil Série A 2025 ===
    "Flamengo":            1_500_000, "Palmeiras":           1_400_000,
    "Sao Paulo":           1_200_000, "Corinthians":         1_100_000,
    "Internacional":         950_000, "Gremio":                900_000,
    "Atletico Mineiro":      900_000, "Fluminense":            800_000,
    "Botafogo":              800_000, "RB Bragantino":         700_000,
    "Athletico Paranaense":  700_000, "Fortaleza":             600_000,
    "Cruzeiro":              650_000, "Bahia":                 600_000,
    "Vasco da Gama":         550_000, "Santos":                650_000,
    "Ceara":                 450_000, "Juventude":             400_000,
    "Vitoria":               400_000, "Sport Recife":          400_000,
    # === MLS 2025 ===
    "Inter Miami":         1_200_000, "LAFC":                  900_000,
    "Toronto FC":            850_000, "Atlanta United":        850_000,
    "LA Galaxy":             900_000, "Nashville SC":          700_000,
    "New York Red Bulls":    700_000, "Vancouver Whitecaps":   600_000,
    "New York City FC":      750_000, "FC Cincinnati":         700_000,
    "Columbus Crew":         700_000, "Portland Timbers":      650_000,
    "Real Salt Lake":        600_000, "New England Revolution":600_000,
    "Colorado Rapids":       550_000, "Charlotte FC":          600_000,
    "Minnesota United":      550_000, "Houston Dynamo":        500_000,
    "DC United":             500_000, "San Jose Earthquakes":  450_000,
    "Chicago Fire":          500_000, "Orlando City":          650_000,
    "Austin FC":             550_000, "FC Dallas":             500_000,
    "Sporting Kansas City":  500_000, "Seattle Sounders":      750_000,
    "Philadelphia Union":    600_000, "St. Louis City SC":     600_000,
    "CF Montreal":           400_000, "San Diego FC":          500_000,
    # === Saudi Pro League 2025/26 ===
    "Al-Hilal":            3_500_000, "Al-Nassr":            3_400_000,
    "Al-Ittihad":          3_200_000, "Al-Ahli":             3_000_000,
    "Al-Shabab":           2_500_000, "Al-Ettifaq":          2_000_000,
    "Abha":                  900_000, "Al-Taawoun":          1_200_000,
    "Al-Fateh":              900_000, "Damac":                 950_000,
    "Al-Raed":               800_000, "Al-Khaleej":            700_000,
    "Al-Wahda":              900_000, "Al-Okhdood":            600_000,
    "Al-Kholood":            700_000, "Al-Orubah":             600_000,
    "Al-Qadsiah":          1_300_000, "Al-Adalah":             500_000,
}


# Default values for clubs not explicitly listed.
DEFAULT_SCOUTING_BUDGET = 200_000
DEFAULT_TRANSFER_BUDGET = 10_000_000
DEFAULT_WAGE_BUDGET = 300_000


def get_wage_budget(club_name: str) -> int:
    """Return weekly wage budget cap (€/week) for a club. Default 300k for any
    club not explicitly listed."""
    if club_name in WAGE_BUDGETS:
        return WAGE_BUDGETS[club_name]
    # Try CSV name map
    if club_name in CSV_NAME_MAP:
        mapped = CSV_NAME_MAP[club_name]
        if mapped in WAGE_BUDGETS:
            return WAGE_BUDGETS[mapped]
    return DEFAULT_WAGE_BUDGET


def get_club_budget(club_name: str) -> tuple:
    """Get (scouting_budget, transfer_budget) for a club."""
    if club_name in CLUB_BUDGETS:
        return CLUB_BUDGETS[club_name]
    if club_name in CSV_NAME_MAP:
        mapped = CSV_NAME_MAP[club_name]
        if mapped in CLUB_BUDGETS:
            return CLUB_BUDGETS[mapped]
    for key, val in CLUB_BUDGETS.items():
        if key.lower() in club_name.lower() or club_name.lower() in key.lower():
            return val
    return (DEFAULT_SCOUTING_BUDGET, DEFAULT_TRANSFER_BUDGET)


def get_all_clubs():
    """Get all clubs with full info for selection screen."""
    return [{"name": name, "scouting_budget": scout, "transfer_budget": transfer, "league": league}
            for name, scout, transfer, league in CLUBS]
