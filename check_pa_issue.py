"""Check PA issue"""
import sys
sys.path.insert(0, '.')

# Force module reload
for module_name in list(sys.modules.keys()):
    if 'app.services.player_loader' in module_name:
        del sys.modules[module_name]

from app.services.player_loader import PlayerCSVParser

parser = PlayerCSVParser('2600球员属性.csv')
df = parser.load()

print("Checking PA values...")
print(f"Total players: {len(df)}\n")

# Check PA range
import pandas as pd
df['pa_numeric'] = pd.to_numeric(df['pa'], errors='coerce')

print("PA value distribution:")
print(f"  Valid PA (1-200): {((df['pa_numeric'] >= 1) & (df['pa_numeric'] <= 200)).sum()}")
print(f"  Negative PA: {(df['pa_numeric'] < 0).sum()}")
print(f"  PA > 200: {(df['pa_numeric'] > 200).sum()}")
print(f"  Missing PA: {df['pa_numeric'].isna().sum()}")

print(f"\nNegative PA values (first 10):")
negative_pa = df[df['pa_numeric'] < 0].head(10)
for idx, row in negative_pa.iterrows():
    print(f"  {row['name']}: PA = {row['pa']}")

print(f"\nNote: Negative PA values in Football Manager indicate:")
print(f"  -10 = Random potential between 150-180")
print(f"  -9 = Random potential between 140-170")
print(f"  -8 = Random potential between 130-160")
print(f"  etc.")
print(f"\nThese are VALID values and should be accepted!")
