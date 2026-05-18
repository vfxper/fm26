"""
Transfer History Logging Example

This script demonstrates the usage of the transfer history logging system.
It shows how to log transfers and query the history with various filters.
"""

from app.services.transfer_service import TransferService, TransferRecord
from typing import List


def print_separator(title: str = ""):
    """Print a formatted separator"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"{'='*60}\n")


def print_transfer_record(record: TransferRecord, index: int = None):
    """Print a formatted transfer record"""
    prefix = f"{index}. " if index is not None else "  "
    print(f"{prefix}{record.player_name}")
    print(f"   From: {record.from_club} → To: {record.to_club}")
    print(f"   Type: {record.transfer_type}")
    print(f"   Fee: ${record.fee:,}, Wage: ${record.wage:,}/week")
    print(f"   Season {record.season}, Week {record.week}")


def example_basic_logging():
    """Example 1: Basic transfer logging"""
    print_separator("Example 1: Basic Transfer Logging")
    
    service = TransferService()
    history = []
    
    # Log a permanent transfer
    print("Logging permanent transfer...")
    record1 = service.log_transfer(
        player_id=1,
        player_name="Cristiano Ronaldo",
        from_club="Manchester United",
        to_club="Real Madrid",
        transfer_type="permanent",
        fee=80_000_000,
        wage=300_000,
        season=1,
        week=5,
        history=history,
    )
    print_transfer_record(record1)
    
    # Log a loan transfer
    print("\nLogging loan transfer...")
    record2 = service.log_transfer(
        player_id=2,
        player_name="Gareth Bale",
        from_club="Tottenham Hotspur",
        to_club="Real Madrid",
        transfer_type="loan",
        fee=0,
        wage=150_000,
        season=1,
        week=7,
        history=history,
    )
    print_transfer_record(record2)
    
    # Log a free agent signing
    print("\nLogging free agent signing...")
    record3 = service.log_transfer(
        player_id=3,
        player_name="Zlatan Ibrahimović",
        from_club="Free Agent",
        to_club="Manchester United",
        transfer_type="free_agent",
        fee=0,
        wage=250_000,
        season=1,
        week=15,
        history=history,
    )
    print_transfer_record(record3)
    
    print(f"\nTotal transfers logged: {len(history)}")


def example_season_filtering():
    """Example 2: Filtering by season"""
    print_separator("Example 2: Filtering by Season")
    
    service = TransferService()
    history = []
    
    # Create transfers across multiple seasons
    transfers_data = [
        # Season 1
        (1, "Lionel Messi", "Barcelona", "Paris Saint-Germain", "permanent", 50_000_000, 500_000, 1, 5),
        (2, "Neymar Jr", "Barcelona", "Paris Saint-Germain", "permanent", 222_000_000, 600_000, 1, 6),
        (3, "Kylian Mbappé", "Monaco", "Paris Saint-Germain", "loan", 0, 200_000, 1, 7),
        # Season 2
        (4, "Eden Hazard", "Chelsea", "Real Madrid", "permanent", 100_000_000, 400_000, 2, 3),
        (5, "Harry Kane", "Tottenham", "Bayern Munich", "permanent", 120_000_000, 450_000, 2, 4),
        # Season 3
        (6, "Erling Haaland", "Dortmund", "Manchester City", "permanent", 60_000_000, 375_000, 3, 2),
    ]
    
    for data in transfers_data:
        service.log_transfer(
            player_id=data[0],
            player_name=data[1],
            from_club=data[2],
            to_club=data[3],
            transfer_type=data[4],
            fee=data[5],
            wage=data[6],
            season=data[7],
            week=data[8],
            history=history,
        )
    
    print(f"Total transfers: {len(history)}\n")
    
    # Filter by season 1
    season1 = service.get_transfer_history(history, season=1)
    print(f"Season 1 Transfers ({len(season1)}):")
    for i, record in enumerate(season1, 1):
        print_transfer_record(record, i)
    
    # Filter by season 2
    season2 = service.get_transfer_history(history, season=2)
    print(f"\nSeason 2 Transfers ({len(season2)}):")
    for i, record in enumerate(season2, 1):
        print_transfer_record(record, i)
    
    # Filter by season 3
    season3 = service.get_transfer_history(history, season=3)
    print(f"\nSeason 3 Transfers ({len(season3)}):")
    for i, record in enumerate(season3, 1):
        print_transfer_record(record, i)


def example_type_filtering():
    """Example 3: Filtering by transfer type"""
    print_separator("Example 3: Filtering by Transfer Type")
    
    service = TransferService()
    history = []
    
    # Create transfers of different types
    transfers_data = [
        (1, "Player A", "Club 1", "Club 2", "permanent", 10_000_000, 50_000, 1, 5),
        (2, "Player B", "Club 3", "Club 2", "loan", 0, 30_000, 1, 6),
        (3, "Player C", "Free Agent", "Club 2", "free_agent", 0, 40_000, 1, 15),
        (4, "Player D", "Club 4", "Club 2", "emergency_loan", 0, 25_000, 1, 35),
        (5, "Player E", "Club 5", "Club 2", "permanent", 15_000_000, 60_000, 1, 7),
        (6, "Player F", "Club 6", "Club 2", "loan", 0, 35_000, 1, 8),
    ]
    
    for data in transfers_data:
        service.log_transfer(
            player_id=data[0],
            player_name=data[1],
            from_club=data[2],
            to_club=data[3],
            transfer_type=data[4],
            fee=data[5],
            wage=data[6],
            season=data[7],
            week=data[8],
            history=history,
        )
    
    print(f"Total transfers: {len(history)}\n")
    
    # Filter by permanent transfers
    permanent = service.get_transfer_history(history, transfer_type="permanent")
    print(f"Permanent Transfers ({len(permanent)}):")
    for i, record in enumerate(permanent, 1):
        print_transfer_record(record, i)
    
    # Filter by loan transfers
    loans = service.get_transfer_history(history, transfer_type="loan")
    print(f"\nLoan Transfers ({len(loans)}):")
    for i, record in enumerate(loans, 1):
        print_transfer_record(record, i)
    
    # Filter by free agent signings
    free_agents = service.get_transfer_history(history, transfer_type="free_agent")
    print(f"\nFree Agent Signings ({len(free_agents)}):")
    for i, record in enumerate(free_agents, 1):
        print_transfer_record(record, i)
    
    # Filter by emergency loans
    emergency = service.get_transfer_history(history, transfer_type="emergency_loan")
    print(f"\nEmergency Loans ({len(emergency)}):")
    for i, record in enumerate(emergency, 1):
        print_transfer_record(record, i)


def example_combined_filtering():
    """Example 4: Combined filtering (season + type)"""
    print_separator("Example 4: Combined Filtering")
    
    service = TransferService()
    history = []
    
    # Create diverse transfer history
    transfers_data = [
        # Season 1 - permanent
        (1, "Player A", "Club 1", "My Club", "permanent", 20_000_000, 80_000, 1, 5),
        (2, "Player B", "Club 2", "My Club", "permanent", 15_000_000, 70_000, 1, 6),
        # Season 1 - loan
        (3, "Player C", "Club 3", "My Club", "loan", 0, 40_000, 1, 7),
        # Season 2 - permanent
        (4, "Player D", "Club 4", "My Club", "permanent", 25_000_000, 90_000, 2, 3),
        # Season 2 - free agent
        (5, "Player E", "Free Agent", "My Club", "free_agent", 0, 50_000, 2, 15),
        (6, "Player F", "Free Agent", "My Club", "free_agent", 0, 45_000, 2, 20),
        # Season 3 - permanent
        (7, "Player G", "Club 5", "My Club", "permanent", 30_000_000, 100_000, 3, 2),
        # Season 3 - loan
        (8, "Player H", "Club 6", "My Club", "loan", 0, 35_000, 3, 4),
    ]
    
    for data in transfers_data:
        service.log_transfer(
            player_id=data[0],
            player_name=data[1],
            from_club=data[2],
            to_club=data[3],
            transfer_type=data[4],
            fee=data[5],
            wage=data[6],
            season=data[7],
            week=data[8],
            history=history,
        )
    
    print(f"Total transfers: {len(history)}\n")
    
    # Season 1 permanent transfers
    s1_permanent = service.get_transfer_history(history, season=1, transfer_type="permanent")
    print(f"Season 1 Permanent Transfers ({len(s1_permanent)}):")
    for i, record in enumerate(s1_permanent, 1):
        print_transfer_record(record, i)
    
    # Season 2 free agents
    s2_free = service.get_transfer_history(history, season=2, transfer_type="free_agent")
    print(f"\nSeason 2 Free Agent Signings ({len(s2_free)}):")
    for i, record in enumerate(s2_free, 1):
        print_transfer_record(record, i)
    
    # Season 3 loans
    s3_loans = service.get_transfer_history(history, season=3, transfer_type="loan")
    print(f"\nSeason 3 Loan Transfers ({len(s3_loans)}):")
    for i, record in enumerate(s3_loans, 1):
        print_transfer_record(record, i)


def example_transfer_statistics():
    """Example 5: Calculating transfer statistics"""
    print_separator("Example 5: Transfer Statistics")
    
    service = TransferService()
    history = []
    
    # Create a realistic transfer history
    transfers_data = [
        (1, "Star Player", "Big Club", "My Club", "permanent", 50_000_000, 200_000, 1, 5),
        (2, "Young Talent", "Small Club", "My Club", "permanent", 5_000_000, 50_000, 1, 6),
        (3, "Loan Player", "Top Club", "My Club", "loan", 0, 80_000, 1, 7),
        (4, "Free Agent", "Free Agent", "My Club", "free_agent", 0, 60_000, 1, 15),
        (5, "Backup GK", "Mid Club", "My Club", "permanent", 2_000_000, 30_000, 2, 3),
        (6, "Emergency Loan", "Another Club", "My Club", "emergency_loan", 0, 40_000, 2, 35),
    ]
    
    for data in transfers_data:
        service.log_transfer(
            player_id=data[0],
            player_name=data[1],
            from_club=data[2],
            to_club=data[3],
            transfer_type=data[4],
            fee=data[5],
            wage=data[6],
            season=data[7],
            week=data[8],
            history=history,
        )
    
    # Calculate statistics
    all_transfers = service.get_transfer_history(history)
    permanent_transfers = service.get_transfer_history(history, transfer_type="permanent")
    loan_transfers = service.get_transfer_history(history, transfer_type="loan")
    free_agents = service.get_transfer_history(history, transfer_type="free_agent")
    emergency_loans = service.get_transfer_history(history, transfer_type="emergency_loan")
    
    total_fees = sum(r.fee for r in all_transfers)
    total_wages = sum(r.wage for r in all_transfers)
    
    print("Transfer Summary:")
    print(f"  Total Transfers: {len(all_transfers)}")
    print(f"  Permanent: {len(permanent_transfers)}")
    print(f"  Loans: {len(loan_transfers)}")
    print(f"  Free Agents: {len(free_agents)}")
    print(f"  Emergency Loans: {len(emergency_loans)}")
    
    print(f"\nFinancial Summary:")
    print(f"  Total Transfer Fees: ${total_fees:,}")
    print(f"  Total Weekly Wages: ${total_wages:,}")
    print(f"  Average Transfer Fee: ${total_fees // len(permanent_transfers) if permanent_transfers else 0:,}")
    print(f"  Average Weekly Wage: ${total_wages // len(all_transfers):,}")
    
    if permanent_transfers:
        most_expensive = max(permanent_transfers, key=lambda r: r.fee)
        print(f"\nMost Expensive Signing:")
        print_transfer_record(most_expensive)
    
    if all_transfers:
        highest_wage = max(all_transfers, key=lambda r: r.wage)
        print(f"\nHighest Wage:")
        print_transfer_record(highest_wage)


def example_multi_season_analysis():
    """Example 6: Multi-season transfer analysis"""
    print_separator("Example 6: Multi-Season Analysis")
    
    service = TransferService()
    history = []
    
    # Simulate 3 seasons of transfers
    for season in range(1, 4):
        # Each season has different transfer activity
        num_transfers = 3 + season  # More transfers each season
        
        for i in range(num_transfers):
            player_id = (season - 1) * 10 + i
            fee = (season * 5_000_000) + (i * 1_000_000)
            wage = 50_000 + (season * 10_000) + (i * 5_000)
            
            service.log_transfer(
                player_id=player_id,
                player_name=f"Player S{season}-{i+1}",
                from_club=f"Club {player_id}",
                to_club="My Club",
                transfer_type="permanent" if i % 2 == 0 else "loan",
                fee=fee if i % 2 == 0 else 0,
                wage=wage,
                season=season,
                week=5 + i,
                history=history,
            )
    
    print("Multi-Season Transfer Analysis:\n")
    
    # Analyze each season
    for season in range(1, 4):
        season_transfers = service.get_transfer_history(history, season=season)
        season_permanent = service.get_transfer_history(history, season=season, transfer_type="permanent")
        season_loans = service.get_transfer_history(history, season=season, transfer_type="loan")
        
        total_fees = sum(r.fee for r in season_transfers)
        total_wages = sum(r.wage for r in season_transfers)
        
        print(f"Season {season}:")
        print(f"  Total Transfers: {len(season_transfers)}")
        print(f"  Permanent: {len(season_permanent)}")
        print(f"  Loans: {len(season_loans)}")
        print(f"  Total Fees: ${total_fees:,}")
        print(f"  Total Wages: ${total_wages:,}/week")
        print()
    
    # Overall statistics
    print("Overall Statistics:")
    print(f"  Total Transfers: {len(history)}")
    print(f"  Total Fees: ${sum(r.fee for r in history):,}")
    print(f"  Total Wages: ${sum(r.wage for r in history):,}/week")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("  TRANSFER HISTORY LOGGING EXAMPLES")
    print("="*60)
    
    example_basic_logging()
    example_season_filtering()
    example_type_filtering()
    example_combined_filtering()
    example_transfer_statistics()
    example_multi_season_analysis()
    
    print_separator()
    print("All examples completed successfully!")
    print()


if __name__ == "__main__":
    main()
