"""Quick verification that tests can be imported"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Try to import the service
    from app.services.transfer_service import TransferService, MAX_SQUAD_SIZE
    print("✓ Successfully imported TransferService")
    print(f"✓ MAX_SQUAD_SIZE = {MAX_SQUAD_SIZE}")
    
    # Create service instance
    service = TransferService()
    print("✓ Successfully created TransferService instance")
    
    # Test the method exists
    assert hasattr(service, 'validate_transfer_squad_size')
    print("✓ validate_transfer_squad_size method exists")
    
    # Quick functional test
    assert service.validate_transfer_squad_size(39) is True
    print("✓ validate_transfer_squad_size(39) returns True")
    
    assert service.validate_transfer_squad_size(40) is False
    print("✓ validate_transfer_squad_size(40) returns False")
    
    print("\n" + "="*60)
    print("All verifications passed! Tests are ready to run.")
    print("="*60)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
