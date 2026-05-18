"""
Verify that all player data is correctly imported into the database.

This script checks:
1. Total player count
2. Data integrity (all required fields present)
3. Attribute ranges
4. Traits data
5. Sample queries
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, select, func, and_, or_
from sqlalchemy.orm import sessionmaker

from app.models.player import Player

# Connect to SQLite database
DATABASE_URL = "sqlite:///./tfm_players.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def verify_total_count(session):
    """Verify total player count"""
    print("\n" + "="*60)
    print("1. TOTAL PLAYER COUNT")
    print("="*60)
    
    count = session.execute(select(func.count(Player.id))).scalar_one()
    print(f"Total players in database: {count}")
    
    expected = 34643
    if count == expected:
        print(f"✓ Correct! Expected {expected} players")
    else:
        print(f"✗ Warning! Expected {expected} but got {count}")
    
    return count == expected


def verify_data_integrity(session):
    """Verify data integrity"""
    print("\n" + "="*60)
    print("2. DATA INTEGRITY")
    print("="*60)
    
    # Check for NULL values in required fields
    required_fields = [
        ('name', Player.name),
        ('position', Player.position),
        ('age', Player.age),
        ('ca', Player.ca),
        ('pa', Player.pa),
        ('club', Player.club),
        ('uid', Player.uid),
    ]
    
    all_good = True
    for field_name, field in required_fields:
        null_count = session.execute(
            select(func.count(Player.id)).where(field.is_(None))
        ).scalar_one()
        
        if null_count > 0:
            print(f"✗ {field_name}: {null_count} NULL values found")
            all_good = False
        else:
            print(f"✓ {field_name}: No NULL values")
    
    return all_good


def verify_attribute_ranges(session):
    """Verify attribute ranges"""
    print("\n" + "="*60)
    print("3. ATTRIBUTE RANGES")
    print("="*60)
    
    all_good = True
    
    # Check CA range (1-200)
    ca_out_of_range = session.execute(
        select(func.count(Player.id)).where(
            or_(Player.ca < 1, Player.ca > 200)
        )
    ).scalar_one()
    
    if ca_out_of_range > 0:
        print(f"✗ CA: {ca_out_of_range} players out of range (1-200)")
        all_good = False
    else:
        print(f"✓ CA: All players in valid range (1-200)")
    
    # Check PA range (-200 to 200, excluding 0)
    pa_out_of_range = session.execute(
        select(func.count(Player.id)).where(
            or_(Player.pa < -200, Player.pa > 200, Player.pa == 0)
        )
    ).scalar_one()
    
    if pa_out_of_range > 0:
        print(f"✗ PA: {pa_out_of_range} players out of range (-200 to 200)")
        all_good = False
    else:
        print(f"✓ PA: All players in valid range (-200 to 200)")
    
    # Check technical attributes (1-20)
    tech_attrs = ['dribbling', 'passing', 'finishing', 'technique']
    for attr_name in tech_attrs:
        attr = getattr(Player, attr_name)
        out_of_range = session.execute(
            select(func.count(Player.id)).where(
                or_(attr < 1, attr > 20)
            )
        ).scalar_one()
        
        if out_of_range > 0:
            print(f"✗ {attr_name}: {out_of_range} players out of range (1-20)")
            all_good = False
    
    if all_good:
        print(f"✓ All technical attributes in valid range (1-20)")
    
    return all_good


def verify_traits_data(session):
    """Verify traits data"""
    print("\n" + "="*60)
    print("4. TRAITS DATA")
    print("="*60)
    
    # Count players with non-empty traits
    with_traits = session.execute(
        select(func.count(Player.id)).where(
            and_(Player.traits.isnot(None), Player.traits != '')
        )
    ).scalar_one()
    
    total = session.execute(select(func.count(Player.id))).scalar_one()
    
    print(f"Players with traits: {with_traits} / {total} ({with_traits/total*100:.1f}%)")
    
    # Show sample traits
    result = session.execute(
        select(Player).where(
            and_(Player.traits.isnot(None), Player.traits != '')
        ).limit(3)
    )
    players = result.scalars().all()
    
    print(f"\nSample players with traits:")
    for player in players:
        traits_preview = player.traits[:50] + "..." if len(player.traits) > 50 else player.traits
        print(f"  - {player.name}: {traits_preview}")
    
    return with_traits > 0


def verify_sample_queries(session):
    """Verify sample queries work correctly"""
    print("\n" + "="*60)
    print("5. SAMPLE QUERIES")
    print("="*60)
    
    all_good = True
    
    # Query 1: Top 10 players by CA
    print("\nTop 10 players by CA:")
    result = session.execute(
        select(Player).order_by(Player.ca.desc()).limit(10)
    )
    top_players = result.scalars().all()
    
    if len(top_players) == 10:
        for i, player in enumerate(top_players, 1):
            print(f"  {i}. {player.name} ({player.club}) - CA: {player.ca}")
        print("✓ Query successful")
    else:
        print(f"✗ Expected 10 players, got {len(top_players)}")
        all_good = False
    
    # Query 2: Search by name
    print("\nSearch for 'Ronaldo':")
    result = session.execute(
        select(Player).where(Player.name.like('%Ronaldo%')).limit(5)
    )
    ronaldo_players = result.scalars().all()
    
    if len(ronaldo_players) > 0:
        for player in ronaldo_players:
            print(f"  - {player.name} ({player.club}) - CA: {player.ca}")
        print(f"✓ Found {len(ronaldo_players)} players")
    else:
        print("✗ No players found")
        all_good = False
    
    # Query 3: Filter by position and CA
    print("\nTop strikers (ST) with CA > 170:")
    result = session.execute(
        select(Player).where(
            and_(
                Player.position.like('%ST%'),
                Player.ca > 170
            )
        ).order_by(Player.ca.desc()).limit(5)
    )
    strikers = result.scalars().all()
    
    if len(strikers) > 0:
        for player in strikers:
            print(f"  - {player.name} ({player.position}) - CA: {player.ca}")
        print(f"✓ Found {len(strikers)} strikers")
    else:
        print("✗ No strikers found")
        all_good = False
    
    # Query 4: Young talents (age < 22, PA > 150)
    print("\nYoung talents (age < 22, PA > 150):")
    result = session.execute(
        select(Player).where(
            and_(
                Player.age < 22,
                Player.pa > 150
            )
        ).order_by(Player.pa.desc()).limit(5)
    )
    talents = result.scalars().all()
    
    if len(talents) > 0:
        for player in talents:
            print(f"  - {player.name} (age {player.age}) - PA: {player.pa}")
        print(f"✓ Found {len(talents)} young talents")
    else:
        print("✗ No young talents found")
        all_good = False
    
    return all_good


def verify_specific_players(session):
    """Verify specific known players"""
    print("\n" + "="*60)
    print("6. SPECIFIC PLAYER VERIFICATION")
    print("="*60)
    
    test_players = [
        'Kylian Mbappé',
        'Lamine Yamal',
        'Lionel Messi',
        'Erling Haaland',
    ]
    
    all_found = True
    for player_name in test_players:
        result = session.execute(
            select(Player).where(Player.name == player_name)
        )
        player = result.scalar_one_or_none()
        
        if player:
            print(f"✓ {player_name}:")
            print(f"    Club: {player.club}")
            print(f"    CA: {player.ca}, PA: {player.pa}")
            print(f"    Age: {player.age}, Position: {player.position}")
            if player.traits:
                traits_preview = player.traits[:50] + "..." if len(player.traits) > 50 else player.traits
                print(f"    Traits: {traits_preview}")
        else:
            print(f"✗ {player_name} NOT FOUND")
            all_found = False
    
    return all_found


def main():
    """Main verification function"""
    print("="*60)
    print("DATABASE VERIFICATION")
    print("="*60)
    
    with SessionLocal() as session:
        results = {
            'total_count': verify_total_count(session),
            'data_integrity': verify_data_integrity(session),
            'attribute_ranges': verify_attribute_ranges(session),
            'traits_data': verify_traits_data(session),
            'sample_queries': verify_sample_queries(session),
            'specific_players': verify_specific_players(session),
        }
    
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name.replace('_', ' ').title()}")
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL VERIFICATIONS PASSED!")
        print("✓ Database is ready for production use!")
    else:
        print("✗ SOME VERIFICATIONS FAILED")
        print("✗ Please review the errors above")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
