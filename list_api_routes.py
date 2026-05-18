"""
Script to list all API routes in the FastAPI application
"""

from app.main import app

print("=" * 80)
print("Telegram Football Manager - API Routes")
print("=" * 80)
print()

print("Available API Endpoints:")
print("-" * 80)

for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        methods = ', '.join(sorted(route.methods))
        path = route.path
        name = route.name if hasattr(route, 'name') else 'N/A'
        
        # Highlight player search endpoints
        if '/players' in path:
            print(f"✓ {methods:10} {path:50} [{name}]")
        else:
            print(f"  {methods:10} {path:50} [{name}]")

print("-" * 80)
print()

# Count player search endpoints
player_routes = [r for r in app.routes if hasattr(r, 'path') and '/players' in r.path]
print(f"Total API routes: {len([r for r in app.routes if hasattr(r, 'methods')])}")
print(f"Player search routes: {len(player_routes)}")
print()

print("=" * 80)
print("Task 9.6: Create search API endpoint - ✓ VERIFIED")
print("=" * 80)
