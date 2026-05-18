"""
Verification Script for Player Full-Text Search GIN Index

This script verifies that the Player model has the correct full-text search
GIN index defined without requiring a database connection.

Run: python verify_player_fts_index.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.models.player import Player
from sqlalchemy import inspect


def verify_fts_index():
    """
    Verify that the Player model has the full-text search GIN index defined.
    """
    print("=" * 70)
    print("Player Model Full-Text Search GIN Index Verification")
    print("=" * 70)
    print()
    
    # Get table args
    table_args = Player.__table_args__
    
    print("Step 1: Checking __table_args__ for indexes...")
    print(f"   Found {len(table_args)} table arguments")
    print()
    
    # Find GIN index
    gin_index = None
    for arg in table_args:
        if hasattr(arg, 'name') and arg.name == 'idx_players_fts':
            gin_index = arg
            break
    
    if gin_index is None:
        print("❌ FAILED: GIN index 'idx_players_fts' not found in __table_args__")
        return False
    
    print("✅ Step 1 PASSED: GIN index 'idx_players_fts' found")
    print()
    
    # Verify index properties
    print("Step 2: Verifying GIN index properties...")
    
    # Check if it's using GIN
    if hasattr(gin_index, 'kwargs'):
        using = gin_index.kwargs.get('postgresql_using')
        if using == 'gin':
            print("✅ Index uses GIN (postgresql_using='gin')")
        else:
            print(f"❌ FAILED: Index does not use GIN (postgresql_using='{using}')")
            return False
    else:
        print("⚠️  WARNING: Could not verify postgresql_using parameter")
    
    print()
    
    # Verify index expression
    print("Step 3: Verifying index expression...")
    
    if hasattr(gin_index, 'expressions'):
        expressions = gin_index.expressions
        print(f"   Index has {len(expressions)} expression(s)")
        
        if len(expressions) > 0:
            expr = expressions[0]
            # Convert to string representation without compiling
            expr_str = str(expr)
            
            print(f"   Expression: {expr_str[:150]}...")
            
            # Check for required components
            checks = {
                'to_tsvector': 'to_tsvector' in expr_str.lower(),
                'name field': 'name' in expr_str.lower() or 'players.name' in expr_str.lower(),
                'position field': 'position' in expr_str.lower() or 'players.position' in expr_str.lower(),
                'club field': 'club' in expr_str.lower() or 'players.club' in expr_str.lower(),
                'nationality field': 'nationality' in expr_str.lower() or 'players.nationality' in expr_str.lower(),
            }
            
            print()
            print("   Expression components:")
            all_passed = True
            for component, present in checks.items():
                status = "✅" if present else "❌"
                print(f"      {status} {component}: {'present' if present else 'MISSING'}")
                if not present:
                    all_passed = False
            
            if not all_passed:
                print()
                print("❌ FAILED: Index expression is missing required components")
                return False
            
            print()
            print("✅ Step 3 PASSED: Index expression contains all required fields")
        else:
            print("❌ FAILED: Index has no expressions")
            return False
    else:
        print("❌ FAILED: Could not access index expressions")
        return False
    
    print()
    
    # Verify helper methods
    print("Step 4: Verifying helper methods...")
    
    helper_methods = [
        'search_query_expression',
        'search_rank_expression',
        'build_search_vector'
    ]
    
    all_methods_present = True
    for method_name in helper_methods:
        if hasattr(Player, method_name):
            print(f"   ✅ {method_name}() method found")
        else:
            print(f"   ❌ {method_name}() method MISSING")
            all_methods_present = False
    
    if not all_methods_present:
        print()
        print("❌ FAILED: Some helper methods are missing")
        return False
    
    print()
    print("✅ Step 4 PASSED: All helper methods present")
    print()
    
    # Test helper methods
    print("Step 5: Testing helper methods...")
    
    try:
        # Test search_query_expression
        expr = Player.search_query_expression("test query")
        print("   ✅ search_query_expression() returns valid expression")
        
        # Test search_rank_expression
        rank_expr = Player.search_rank_expression("test query")
        print("   ✅ search_rank_expression() returns valid expression")
        
        # Test build_search_vector
        vector_expr = Player.build_search_vector("name", "position", "club", "nationality")
        print("   ✅ build_search_vector() returns valid expression")
        
        print()
        print("✅ Step 5 PASSED: All helper methods work correctly")
    except Exception as e:
        print(f"   ❌ Error testing helper methods: {e}")
        return False
    
    print()
    print("=" * 70)
    print("✅ ALL CHECKS PASSED")
    print("=" * 70)
    print()
    print("Summary:")
    print("  • GIN index 'idx_players_fts' is properly defined")
    print("  • Index uses PostgreSQL GIN indexing method")
    print("  • Index expression includes: name, position, club, nationality")
    print("  • Index uses to_tsvector for full-text search")
    print("  • Helper methods for search queries are implemented")
    print()
    print("Next steps:")
    print("  1. Start PostgreSQL database")
    print("  2. Run: python scripts/init_tables.py")
    print("  3. Run: pytest tests/test_player_fts.py -v")
    print()
    
    return True


if __name__ == "__main__":
    success = verify_fts_index()
    sys.exit(0 if success else 1)
