"""
Manual test script for transfer history logging functionality
"""

from app.services.transfer_service import TransferService, TransferRecord

def test_log_transfer():
    """Test logging a transfer"""
    service = TransferService()
    history = []
    
    # Test logging a permanent transfer
    record = service.log_transfer(
        player_id=1,
        player_name="John Doe",
        from_club="Club A",
        to_club="Club B",
        transfer_type="permanent",
        fee=5_000_000,
        wage=10_000,
        season=1,
        week=5,
        history=history,
    )
    
    print("✓ Test 1: Log permanent transfer")
    assert record.player_id == 1
    assert record.player_name == "John Doe"
    assert record.transfer_type == "permanent"
    assert record.fee == 5_000_000
    assert len(history) == 1
    print(f"  Record: {record.player_name} from {record.from_club} to {record.to_club} for ${record.fee:,}")
    
    # Test logging a loan transfer
    record2 = service.log_transfer(
        player_id=2,
        player_name="Jane Smith",
        from_club="Club C",
        to_club="Club B",
        transfer_type="loan",
        fee=0,
        wage=8_000,
        season=1,
        week=7,
        history=history,
    )
    
    print("\n✓ Test 2: Log loan transfer")
    assert record2.transfer_type == "loan"
    assert record2.fee == 0
    assert len(history) == 2
    print(f"  Record: {record2.player_name} from {record2.from_club} to {record2.to_club} (loan)")
    
    # Test logging a free agent
    record3 = service.log_transfer(
        player_id=3,
        player_name="Bob Johnson",
        from_club="Free Agent",
        to_club="Club B",
        transfer_type="free_agent",
        fee=0,
        wage=12_000,
        season=2,
        week=15,
        history=history,
    )
    
    print("\n✓ Test 3: Log free agent signing")
    assert record3.transfer_type == "free_agent"
    assert record3.from_club == "Free Agent"
    assert len(history) == 3
    print(f"  Record: {record3.player_name} signed as free agent")
    
    # Test getting all transfers
    all_transfers = service.get_transfer_history(history)
    print(f"\n✓ Test 4: Get all transfers")
    assert len(all_transfers) == 3
    print(f"  Total transfers: {len(all_transfers)}")
    
    # Test filtering by season
    season1_transfers = service.get_transfer_history(history, season=1)
    print(f"\n✓ Test 5: Filter by season 1")
    assert len(season1_transfers) == 2
    print(f"  Season 1 transfers: {len(season1_transfers)}")
    for r in season1_transfers:
        print(f"    - {r.player_name} ({r.transfer_type})")
    
    season2_transfers = service.get_transfer_history(history, season=2)
    print(f"\n✓ Test 6: Filter by season 2")
    assert len(season2_transfers) == 1
    print(f"  Season 2 transfers: {len(season2_transfers)}")
    for r in season2_transfers:
        print(f"    - {r.player_name} ({r.transfer_type})")
    
    # Test filtering by transfer type
    permanent_transfers = service.get_transfer_history(history, transfer_type="permanent")
    print(f"\n✓ Test 7: Filter by permanent transfers")
    assert len(permanent_transfers) == 1
    print(f"  Permanent transfers: {len(permanent_transfers)}")
    for r in permanent_transfers:
        print(f"    - {r.player_name} for ${r.fee:,}")
    
    loan_transfers = service.get_transfer_history(history, transfer_type="loan")
    print(f"\n✓ Test 8: Filter by loan transfers")
    assert len(loan_transfers) == 1
    print(f"  Loan transfers: {len(loan_transfers)}")
    
    # Test combined filters
    season1_permanent = service.get_transfer_history(history, season=1, transfer_type="permanent")
    print(f"\n✓ Test 9: Filter by season 1 AND permanent")
    assert len(season1_permanent) == 1
    assert season1_permanent[0].player_name == "John Doe"
    print(f"  Season 1 permanent transfers: {len(season1_permanent)}")
    
    print("\n" + "="*60)
    print("All tests passed! ✓")
    print("="*60)

if __name__ == "__main__":
    test_log_transfer()
