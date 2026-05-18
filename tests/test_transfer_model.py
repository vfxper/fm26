"""
Unit tests for Transfer model
"""

import pytest
from datetime import datetime
from app.models.transfer import Transfer, TransferType, TransferStatus


def test_transfer_creation():
    """Test basic Transfer model instantiation"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        from_club_id=10,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=5000000,
        wage_offer=50000,
        contract_length=4,
        season=1,
        week=5
    )
    
    assert transfer.career_id == 1
    assert transfer.player_id == 100
    assert transfer.from_club_id == 10
    assert transfer.to_club_id == 20
    assert transfer.transfer_type == TransferType.PERMANENT
    assert transfer.transfer_status == TransferStatus.PENDING
    assert transfer.transfer_fee == 5000000
    assert transfer.wage_offer == 50000
    assert transfer.contract_length == 4
    assert transfer.season == 1
    assert transfer.week == 5


def test_transfer_type_enum():
    """Test TransferType enum values"""
    assert TransferType.PERMANENT.value == "permanent"
    assert TransferType.LOAN.value == "loan"
    assert TransferType.FREE_AGENT.value == "free_agent"
    assert TransferType.EMERGENCY_LOAN.value == "emergency_loan"


def test_transfer_status_enum():
    """Test TransferStatus enum values"""
    assert TransferStatus.PENDING.value == "pending"
    assert TransferStatus.ACCEPTED.value == "accepted"
    assert TransferStatus.REJECTED.value == "rejected"
    assert TransferStatus.COMPLETED.value == "completed"


def test_is_pending():
    """Test is_pending method"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=5000000,
        wage_offer=50000,
        season=1,
        week=5
    )
    
    assert transfer.is_pending() is True
    
    transfer.transfer_status = TransferStatus.COMPLETED
    assert transfer.is_pending() is False


def test_is_completed():
    """Test is_completed method"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.COMPLETED,
        transfer_fee=5000000,
        wage_offer=50000,
        season=1,
        week=5
    )
    
    assert transfer.is_completed() is True
    
    transfer.transfer_status = TransferStatus.PENDING
    assert transfer.is_completed() is False


def test_is_loan():
    """Test is_loan method"""
    loan_transfer = Transfer(
        career_id=1,
        player_id=100,
        from_club_id=10,
        to_club_id=20,
        transfer_type=TransferType.LOAN,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=0,
        wage_offer=30000,
        loan_duration=38,
        wage_contribution=0.5,
        season=1,
        week=5
    )
    
    assert loan_transfer.is_loan() is True
    
    emergency_loan = Transfer(
        career_id=1,
        player_id=100,
        from_club_id=10,
        to_club_id=20,
        transfer_type=TransferType.EMERGENCY_LOAN,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=0,
        wage_offer=30000,
        loan_duration=10,
        wage_contribution=0.3,
        season=1,
        week=35
    )
    
    assert emergency_loan.is_loan() is True
    
    permanent_transfer = Transfer(
        career_id=1,
        player_id=100,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=5000000,
        wage_offer=50000,
        season=1,
        week=5
    )
    
    assert permanent_transfer.is_loan() is False


def test_is_permanent():
    """Test is_permanent method"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=5000000,
        wage_offer=50000,
        season=1,
        week=5
    )
    
    assert transfer.is_permanent() is True
    
    transfer.transfer_type = TransferType.LOAN
    assert transfer.is_permanent() is False


def test_is_free_agent():
    """Test is_free_agent method"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        from_club_id=None,
        to_club_id=20,
        transfer_type=TransferType.FREE_AGENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=0,
        wage_offer=40000,
        contract_length=3,
        season=1,
        week=5
    )
    
    assert transfer.is_free_agent() is True
    
    transfer.transfer_type = TransferType.PERMANENT
    assert transfer.is_free_agent() is False


def test_get_total_cost_permanent():
    """Test get_total_cost for permanent transfer"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=5000000,
        wage_offer=50000,
        contract_length=4,
        season=1,
        week=5
    )
    
    # Total cost = transfer_fee + (wage_offer * 52 weeks * contract_length years)
    # = 5000000 + (50000 * 52 * 4)
    # = 5000000 + 10400000
    # = 15400000
    assert transfer.get_total_cost() == 15400000


def test_get_total_cost_loan():
    """Test get_total_cost for loan transfer"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        from_club_id=10,
        to_club_id=20,
        transfer_type=TransferType.LOAN,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=0,
        wage_offer=30000,
        loan_duration=38,
        wage_contribution=0.5,
        season=1,
        week=5
    )
    
    # Total cost = wage_contribution * wage_offer * loan_duration
    # = 0.5 * 30000 * 38
    # = 570000
    assert transfer.get_total_cost() == 570000


def test_get_total_cost_free_agent():
    """Test get_total_cost for free agent signing"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        from_club_id=None,
        to_club_id=20,
        transfer_type=TransferType.FREE_AGENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=0,
        wage_offer=40000,
        contract_length=3,
        season=1,
        week=5
    )
    
    # Total cost = wage_offer * 52 weeks * contract_length years
    # = 40000 * 52 * 3
    # = 6240000
    assert transfer.get_total_cost() == 6240000


def test_get_wage_cost_per_week_permanent():
    """Test get_wage_cost_per_week for permanent transfer"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=5000000,
        wage_offer=50000,
        contract_length=4,
        season=1,
        week=5
    )
    
    assert transfer.get_wage_cost_per_week() == 50000


def test_get_wage_cost_per_week_loan():
    """Test get_wage_cost_per_week for loan transfer"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        from_club_id=10,
        to_club_id=20,
        transfer_type=TransferType.LOAN,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=0,
        wage_offer=30000,
        loan_duration=38,
        wage_contribution=0.5,
        season=1,
        week=5
    )
    
    # Weekly cost = wage_contribution * wage_offer
    # = 0.5 * 30000
    # = 15000
    assert transfer.get_wage_cost_per_week() == 15000


def test_accept_method():
    """Test accept method"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=5000000,
        wage_offer=50000,
        season=1,
        week=5
    )
    
    transfer.accept()
    assert transfer.transfer_status == TransferStatus.ACCEPTED


def test_reject_method():
    """Test reject method"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=5000000,
        wage_offer=50000,
        season=1,
        week=5
    )
    
    transfer.reject()
    assert transfer.transfer_status == TransferStatus.REJECTED


def test_to_dict():
    """Test to_dict method"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        from_club_id=10,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=5000000,
        wage_offer=50000,
        contract_length=4,
        season=1,
        week=5
    )
    
    transfer_dict = transfer.to_dict()
    
    assert transfer_dict["career_id"] == 1
    assert transfer_dict["player_id"] == 100
    assert transfer_dict["from_club_id"] == 10
    assert transfer_dict["to_club_id"] == 20
    assert transfer_dict["transfer_type"] == "permanent"
    assert transfer_dict["transfer_status"] == "pending"
    assert transfer_dict["transfer_fee"] == 5000000
    assert transfer_dict["wage_offer"] == 50000
    assert transfer_dict["contract_length"] == 4
    assert transfer_dict["season"] == 1
    assert transfer_dict["week"] == 5


def test_repr():
    """Test __repr__ method"""
    transfer = Transfer(
        career_id=1,
        player_id=100,
        from_club_id=10,
        to_club_id=20,
        transfer_type=TransferType.PERMANENT,
        transfer_status=TransferStatus.PENDING,
        transfer_fee=5000000,
        wage_offer=50000,
        season=1,
        week=5
    )
    
    repr_str = repr(transfer)
    assert "Transfer" in repr_str
    assert "player_id=100" in repr_str
    assert "from_club_id=10" in repr_str
    assert "to_club_id=20" in repr_str
    assert "type=permanent" in repr_str
    assert "status=pending" in repr_str
    assert "fee=5000000" in repr_str
