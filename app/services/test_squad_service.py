"""
Tests for Squad Service

Comprehensive tests covering all squad management functionality:
- Squad size validation (7.1)
- Matchday squad selection (7.2)
- Player contract tracking (7.3)
- Contract expiry notifications (7.4)
- Squad status system (7.5)
- Player morale calculation (7.6)
- Morale impact on CA (7.7)
- Player interaction system (7.8)
- Transfer request logic (7.9)
- Player aging system (7.10)
- Non-EU player restrictions (7.11)
- Player attribute display (7.12)
"""

import pytest
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.services.squad_service import (
    SquadService,
    ValidationResult,
    ContractInfo,
    ContractNotification,
    InteractionResult,
    AgingResult,
    SquadStatus,
    MIN_SQUAD_SIZE,
    MAX_SQUAD_SIZE,
    MATCHDAY_STARTERS,
    MATCHDAY_SUBS,
    MATCHDAY_TOTAL,
    LOW_MORALE_THRESHOLD,
    VERY_LOW_MORALE_THRESHOLD,
    TRANSFER_REQUEST_WEEKS,
    MAX_NON_EU_STARTERS,
    EU_NATIONALITIES,
    LEAGUE_FOREIGN_PLAYER_RULES,
)


# --- Mock/Stub classes for testing ---


@dataclass
class MockSquadPlayer:
    """Mock SquadPlayer for testing without database."""
    player_id: int = 1
    career_id: int = 1
    contract_start_date: date = field(default_factory=lambda: date(2024, 1, 1))
    contract_end_date: date = field(default_factory=lambda: date(2026, 6, 30))
    wage: int = 50000
    release_clause: Optional[int] = None
    contract_months_remaining: Optional[int] = 30
    squad_status: str = "FIRST_TEAM"
    squad_number: int = 7
    morale: int = 70
    appearances: int = 20
    goals: int = 5
    assists: int = 8
    minutes_played: int = 1500
    yellow_cards: int = 3
    red_cards: int = 0
    joined_date: date = field(default_factory=lambda: date(2024, 1, 1))

    def get_goals_per_appearance(self) -> float:
        if self.appearances == 0:
            return 0.0
        return self.goals / self.appearances

    def get_assists_per_appearance(self) -> float:
        if self.appearances == 0:
            return 0.0
        return self.assists / self.appearances


@dataclass
class MockPlayer:
    """Mock Player for testing without database."""
    id: int = 1
    name: str = "Test Player"
    position: str = "AM/ST"
    age: int = 25
    nationality: str = "Spain"
    club: str = "Test FC"
    ca: int = 150
    pa: int = 170
    height: int = 180
    weight: int = 75
    left_foot: int = 15
    right_foot: int = 10
    # Technical
    corners: int = 12
    crossing: int = 14
    dribbling: int = 16
    finishing: int = 17
    first_touch: int = 15
    free_kicks: int = 13
    heading: int = 12
    long_shots: int = 14
    long_throws: int = 5
    marking: int = 6
    passing: int = 15
    penalty: int = 14
    tackling: int = 7
    technique: int = 16
    # Mental
    aggression: int = 10
    anticipation: int = 15
    bravery: int = 12
    composure: int = 16
    concentration: int = 14
    decisions: int = 15
    determination: int = 14
    flair: int = 17
    leadership: int = 10
    off_the_ball: int = 16
    positioning: int = 8
    teamwork: int = 13
    vision: int = 16
    work_rate: int = 13
    # Physical
    acceleration: int = 15
    agility: int = 16
    balance: int = 14
    jumping: int = 12
    stamina: int = 14
    pace: int = 15
    endurance: int = 13
    strength: int = 12
    # Financial
    price: str = "€50M"
    wage: int = 100000
    # Traits
    traits: str = "tries tricks, cuts inside"


# --- Fixtures ---


@pytest.fixture
def service():
    """Create a SquadService instance."""
    return SquadService()


@pytest.fixture
def mock_squad_player():
    """Create a default mock squad player."""
    return MockSquadPlayer()


@pytest.fixture
def mock_player():
    """Create a default mock player."""
    return MockPlayer()


# ===================================================================
# 7.1 Squad size validation tests
# ===================================================================


class TestSquadSizeValidation:
    """Tests for squad size validation (18-40 players)."""

    def test_validate_squad_size_minimum(self, service):
        assert service.validate_squad_size(18) is True

    def test_validate_squad_size_maximum(self, service):
        assert service.validate_squad_size(40) is True

    def test_validate_squad_size_middle(self, service):
        assert service.validate_squad_size(25) is True

    def test_validate_squad_size_below_minimum(self, service):
        assert service.validate_squad_size(17) is False

    def test_validate_squad_size_above_maximum(self, service):
        assert service.validate_squad_size(41) is False

    def test_validate_squad_size_zero(self, service):
        assert service.validate_squad_size(0) is False

    def test_can_add_player_below_max(self, service):
        assert service.can_add_player(39) is True

    def test_can_add_player_at_max(self, service):
        assert service.can_add_player(40) is False

    def test_can_add_player_at_minimum(self, service):
        assert service.can_add_player(18) is True

    def test_can_remove_player_above_min(self, service):
        assert service.can_remove_player(19) is True

    def test_can_remove_player_at_min(self, service):
        assert service.can_remove_player(18) is False

    def test_can_remove_player_at_max(self, service):
        assert service.can_remove_player(40) is True


# ===================================================================
# 7.2 Matchday squad selection tests
# ===================================================================


class TestMatchdaySquad:
    """Tests for matchday squad validation (11 starters + 7 subs)."""

    def test_valid_matchday_squad(self, service):
        starters = [MockSquadPlayer(player_id=i) for i in range(11)]
        subs = [MockSquadPlayer(player_id=i + 11) for i in range(7)]
        result = service.validate_matchday_squad(starters, subs)
        assert result.is_valid is True
        assert result.errors == []

    def test_too_few_starters(self, service):
        starters = [MockSquadPlayer(player_id=i) for i in range(10)]
        subs = [MockSquadPlayer(player_id=i + 10) for i in range(7)]
        result = service.validate_matchday_squad(starters, subs)
        assert result.is_valid is False
        assert any("11 starters" in e for e in result.errors)

    def test_too_many_starters(self, service):
        starters = [MockSquadPlayer(player_id=i) for i in range(12)]
        subs = [MockSquadPlayer(player_id=i + 12) for i in range(7)]
        result = service.validate_matchday_squad(starters, subs)
        assert result.is_valid is False

    def test_too_few_subs(self, service):
        starters = [MockSquadPlayer(player_id=i) for i in range(11)]
        subs = [MockSquadPlayer(player_id=i + 11) for i in range(6)]
        result = service.validate_matchday_squad(starters, subs)
        assert result.is_valid is False
        assert any("7 substitutes" in e for e in result.errors)

    def test_too_many_subs(self, service):
        starters = [MockSquadPlayer(player_id=i) for i in range(11)]
        subs = [MockSquadPlayer(player_id=i + 11) for i in range(8)]
        result = service.validate_matchday_squad(starters, subs)
        assert result.is_valid is False

    def test_empty_squad(self, service):
        result = service.validate_matchday_squad([], [])
        assert result.is_valid is False


# ===================================================================
# 7.3 Player contract tracking tests
# ===================================================================


class TestContractTracking:
    """Tests for player contract tracking."""

    def test_get_contract_info(self, service, mock_squad_player):
        info = service.get_contract_info(mock_squad_player)
        assert isinstance(info, ContractInfo)
        assert info.player_id == 1
        assert info.wage == 50000
        assert info.months_remaining == 30
        assert info.is_expiring_soon is False

    def test_get_contract_info_expiring(self, service):
        sp = MockSquadPlayer(contract_months_remaining=5)
        info = service.get_contract_info(sp)
        assert info.is_expiring_soon is True

    def test_get_contract_info_exactly_threshold(self, service):
        sp = MockSquadPlayer(contract_months_remaining=6)
        info = service.get_contract_info(sp)
        assert info.is_expiring_soon is True

    def test_check_expiring_contracts(self, service):
        players = [
            MockSquadPlayer(player_id=1, contract_months_remaining=3),
            MockSquadPlayer(player_id=2, contract_months_remaining=12),
            MockSquadPlayer(player_id=3, contract_months_remaining=5),
            MockSquadPlayer(player_id=4, contract_months_remaining=24),
        ]
        expiring = service.check_expiring_contracts(players)
        assert len(expiring) == 2
        assert expiring[0].player_id == 1
        assert expiring[1].player_id == 3

    def test_check_expiring_contracts_custom_threshold(self, service):
        players = [
            MockSquadPlayer(player_id=1, contract_months_remaining=10),
            MockSquadPlayer(player_id=2, contract_months_remaining=15),
        ]
        expiring = service.check_expiring_contracts(players, threshold_months=12)
        assert len(expiring) == 1
        assert expiring[0].player_id == 1


# ===================================================================
# 7.4 Contract expiry notifications tests
# ===================================================================


class TestContractNotifications:
    """Tests for contract expiry notifications."""

    def test_generate_notifications(self, service):
        players = [
            MockSquadPlayer(player_id=1, contract_months_remaining=3),
            MockSquadPlayer(player_id=2, contract_months_remaining=5),
            MockSquadPlayer(player_id=3, contract_months_remaining=24),
        ]
        names = {1: "John Smith", 2: "Jane Doe", 3: "Bob Wilson"}
        notifications = service.generate_contract_notifications(players, names)
        assert len(notifications) == 2
        # Sorted by months remaining
        assert notifications[0].player_name == "John Smith"
        assert notifications[0].months_remaining == 3
        assert notifications[1].player_name == "Jane Doe"
        assert notifications[1].months_remaining == 5

    def test_generate_notifications_no_names(self, service):
        players = [MockSquadPlayer(player_id=42, contract_months_remaining=2)]
        notifications = service.generate_contract_notifications(players)
        assert len(notifications) == 1
        assert notifications[0].player_name == "Player 42"

    def test_generate_notifications_none_expiring(self, service):
        players = [
            MockSquadPlayer(player_id=1, contract_months_remaining=12),
            MockSquadPlayer(player_id=2, contract_months_remaining=24),
        ]
        notifications = service.generate_contract_notifications(players)
        assert len(notifications) == 0


# ===================================================================
# 7.5 Squad status system tests
# ===================================================================


class TestSquadStatusSystem:
    """Tests for squad status management."""

    def test_set_squad_status_valid(self, service, mock_squad_player):
        service.set_squad_status(mock_squad_player, SquadStatus.KEY_PLAYER)
        # The status should be updated
        assert mock_squad_player.squad_status in (
            SquadStatus.KEY_PLAYER, "KEY_PLAYER"
        )

    def test_set_squad_status_invalid(self, service, mock_squad_player):
        with pytest.raises(ValueError):
            service.set_squad_status(mock_squad_player, "INVALID_STATUS")

    def test_get_squad_by_status(self, service):
        players = [
            MockSquadPlayer(player_id=1, squad_status="KEY_PLAYER"),
            MockSquadPlayer(player_id=2, squad_status="FIRST_TEAM"),
            MockSquadPlayer(player_id=3, squad_status="KEY_PLAYER"),
            MockSquadPlayer(player_id=4, squad_status="BACKUP"),
        ]
        key_players = service.get_squad_by_status(players, SquadStatus.KEY_PLAYER)
        assert len(key_players) == 2
        assert key_players[0].player_id == 1
        assert key_players[1].player_id == 3

    def test_get_squad_by_status_empty(self, service):
        players = [
            MockSquadPlayer(player_id=1, squad_status="FIRST_TEAM"),
        ]
        not_needed = service.get_squad_by_status(players, SquadStatus.NOT_NEEDED)
        assert len(not_needed) == 0


# ===================================================================
# 7.6 Player morale calculation tests
# ===================================================================


class TestMoraleCalculation:
    """Tests for player morale calculation."""

    def test_morale_good_form_good_time(self, service):
        sp = MockSquadPlayer(morale=70, squad_status="FIRST_TEAM",
                             contract_months_remaining=24)
        results = ["win", "win", "win", "draw", "win"]
        morale = service.calculate_morale(sp, results, playing_time_ratio=0.7)
        assert 1 <= morale <= 100
        # Good form + good playing time should yield high morale
        assert morale >= 50

    def test_morale_bad_form_low_time(self, service):
        sp = MockSquadPlayer(morale=50, squad_status="KEY_PLAYER",
                             contract_months_remaining=24)
        results = ["loss", "loss", "loss", "loss", "draw"]
        morale = service.calculate_morale(sp, results, playing_time_ratio=0.2)
        assert 1 <= morale <= 100
        # Bad form + low playing time for key player should yield low morale
        assert morale < 50

    def test_morale_expiring_contract_penalty(self, service):
        sp = MockSquadPlayer(morale=60, squad_status="FIRST_TEAM",
                             contract_months_remaining=3)
        results = ["draw", "draw", "draw"]
        morale = service.calculate_morale(sp, results, playing_time_ratio=0.5)
        assert 1 <= morale <= 100

    def test_morale_clamped_to_range(self, service):
        sp = MockSquadPlayer(morale=1, squad_status="NOT_NEEDED",
                             contract_months_remaining=1)
        results = ["loss", "loss", "loss", "loss", "loss"]
        morale = service.calculate_morale(sp, results, playing_time_ratio=0.0)
        assert morale >= 1

    def test_morale_empty_results(self, service):
        sp = MockSquadPlayer(morale=70, squad_status="FIRST_TEAM",
                             contract_months_remaining=24)
        morale = service.calculate_morale(sp, [], playing_time_ratio=0.6)
        assert 1 <= morale <= 100


# ===================================================================
# 7.7 Morale impact on CA tests
# ===================================================================


class TestMoraleImpactOnCA:
    """Tests for morale impact on effective CA."""

    def test_normal_morale_no_penalty(self, service):
        assert service.get_effective_ca(150, 50) == 150

    def test_high_morale_no_penalty(self, service):
        assert service.get_effective_ca(150, 100) == 150

    def test_morale_at_threshold_no_penalty(self, service):
        assert service.get_effective_ca(150, 40) == 150

    def test_low_morale_penalty(self, service):
        # morale 39 < 40, so 5% penalty: 150 * 0.05 = 7.5, int(150 - 7.5) = 142
        effective = service.get_effective_ca(150, 39)
        assert effective == 142  # 150 - int(7.5) via int(150 - 7.5)

    def test_very_low_morale_penalty(self, service):
        # morale 10 < 40, 5% of 100 = 5
        effective = service.get_effective_ca(100, 10)
        assert effective == 95

    def test_minimum_ca_floor(self, service):
        # Even with penalty, CA should not go below 1
        effective = service.get_effective_ca(1, 1)
        assert effective >= 1


# ===================================================================
# 7.8 Player interaction system tests
# ===================================================================


class TestPlayerInteraction:
    """Tests for player interaction system."""

    def test_praise_low_morale(self, service):
        sp = MockSquadPlayer(morale=30)
        result = service.interact_with_player(sp, "praise")
        assert result.morale_change == 10
        assert result.new_morale == 40
        assert sp.morale == 40

    def test_praise_medium_morale(self, service):
        sp = MockSquadPlayer(morale=50)
        result = service.interact_with_player(sp, "praise")
        assert result.morale_change == 7
        assert result.new_morale == 57

    def test_praise_high_morale(self, service):
        sp = MockSquadPlayer(morale=80)
        result = service.interact_with_player(sp, "praise")
        assert result.morale_change == 5
        assert result.new_morale == 85

    def test_criticise_low_morale(self, service):
        sp = MockSquadPlayer(morale=20)
        result = service.interact_with_player(sp, "criticise")
        assert result.morale_change == -15
        assert result.new_morale == 5

    def test_criticise_medium_morale(self, service):
        sp = MockSquadPlayer(morale=50)
        result = service.interact_with_player(sp, "criticise")
        assert result.morale_change == -10
        assert result.new_morale == 40

    def test_criticise_high_morale(self, service):
        sp = MockSquadPlayer(morale=80)
        result = service.interact_with_player(sp, "criticise")
        assert result.morale_change == -5
        assert result.new_morale == 75

    def test_promise_time(self, service):
        sp = MockSquadPlayer(morale=50)
        result = service.interact_with_player(sp, "promise_time")
        assert result.morale_change == 10
        assert result.new_morale == 60

    def test_discuss_contract_expiring(self, service):
        sp = MockSquadPlayer(morale=50, contract_months_remaining=4)
        result = service.interact_with_player(sp, "discuss_contract")
        assert result.morale_change == 8
        assert result.new_morale == 58

    def test_discuss_contract_not_expiring(self, service):
        sp = MockSquadPlayer(morale=50, contract_months_remaining=24)
        result = service.interact_with_player(sp, "discuss_contract")
        assert result.morale_change == 5
        assert result.new_morale == 55

    def test_invalid_interaction_type(self, service, mock_squad_player):
        with pytest.raises(ValueError):
            service.interact_with_player(mock_squad_player, "bribe")

    def test_morale_capped_at_100(self, service):
        sp = MockSquadPlayer(morale=95)
        result = service.interact_with_player(sp, "promise_time")
        assert result.new_morale == 100

    def test_morale_floor_at_1(self, service):
        sp = MockSquadPlayer(morale=5)
        result = service.interact_with_player(sp, "criticise")
        assert result.new_morale >= 1


# ===================================================================
# 7.9 Transfer request logic tests
# ===================================================================


class TestTransferRequest:
    """Tests for transfer request logic."""

    def test_transfer_request_triggered(self, service):
        sp = MockSquadPlayer(morale=15)
        assert service.check_transfer_request(sp, 3) is True

    def test_transfer_request_not_enough_weeks(self, service):
        sp = MockSquadPlayer(morale=15)
        assert service.check_transfer_request(sp, 2) is False

    def test_transfer_request_morale_too_high(self, service):
        sp = MockSquadPlayer(morale=25)
        assert service.check_transfer_request(sp, 5) is False

    def test_transfer_request_exactly_at_threshold(self, service):
        sp = MockSquadPlayer(morale=19)
        assert service.check_transfer_request(sp, 3) is True

    def test_transfer_request_morale_at_boundary(self, service):
        sp = MockSquadPlayer(morale=20)
        assert service.check_transfer_request(sp, 3) is False

    def test_transfer_request_many_weeks(self, service):
        sp = MockSquadPlayer(morale=10)
        assert service.check_transfer_request(sp, 10) is True


# ===================================================================
# 7.10 Player aging system tests
# ===================================================================


class TestPlayerAging:
    """Tests for player aging system."""

    def test_young_player_growth(self, service):
        player = MockPlayer(age=19)
        result = service.age_player(player, current_ca=120, current_pa=170)
        assert result.new_age == 20
        assert result.ca_change > 0
        assert result.new_ca > 120
        assert player.age == 20

    def test_peak_player_stable(self, service):
        player = MockPlayer(age=26)
        result = service.age_player(player, current_ca=160, current_pa=160)
        assert result.new_age == 27
        assert result.ca_change == 0

    def test_peak_player_slight_growth(self, service):
        player = MockPlayer(age=26)
        result = service.age_player(player, current_ca=155, current_pa=170)
        assert result.new_age == 27
        assert result.ca_change >= 0

    def test_early_decline(self, service):
        player = MockPlayer(age=30)
        result = service.age_player(player, current_ca=160, current_pa=170)
        assert result.new_age == 31
        assert result.ca_change < 0

    def test_significant_decline(self, service):
        player = MockPlayer(age=33)
        result = service.age_player(player, current_ca=140, current_pa=170)
        assert result.new_age == 34
        assert result.ca_change <= -3

    def test_very_old_player_decline(self, service):
        player = MockPlayer(age=36)
        result = service.age_player(player, current_ca=100, current_pa=170)
        assert result.new_age == 37
        assert result.ca_change == -4

    def test_ca_minimum_floor(self, service):
        player = MockPlayer(age=38)
        result = service.age_player(player, current_ca=3, current_pa=170)
        assert result.new_ca >= 1

    def test_young_player_at_potential(self, service):
        player = MockPlayer(age=20)
        result = service.age_player(player, current_ca=170, current_pa=170)
        assert result.ca_change == 0


# ===================================================================
# 7.11 Non-EU player restrictions tests
# ===================================================================


class TestNonEURestrictions:
    """Tests for non-EU player restrictions (league-configurable)."""

    def test_all_eu_players_valid(self, service):
        starters = [MockPlayer(nationality="Spain") for _ in range(11)]
        assert service.validate_non_eu_restriction(starters) is True

    def test_exactly_max_non_eu(self, service):
        starters = [MockPlayer(nationality="Spain") for _ in range(8)]
        starters += [MockPlayer(nationality="Brazil") for _ in range(3)]
        assert service.validate_non_eu_restriction(starters) is True

    def test_too_many_non_eu(self, service):
        starters = [MockPlayer(nationality="Spain") for _ in range(7)]
        starters += [MockPlayer(nationality="Brazil") for _ in range(4)]
        assert service.validate_non_eu_restriction(starters) is False

    def test_count_non_eu_players(self, service):
        players = [
            MockPlayer(nationality="Spain"),
            MockPlayer(nationality="Brazil"),
            MockPlayer(nationality="Germany"),
            MockPlayer(nationality="Argentina"),
            MockPlayer(nationality="France"),
        ]
        assert service.count_non_eu_players(players) == 2  # Brazil, Argentina

    def test_count_non_eu_empty_list(self, service):
        assert service.count_non_eu_players([]) == 0

    def test_custom_max_non_eu(self, service):
        starters = [MockPlayer(nationality="Spain") for _ in range(9)]
        starters += [MockPlayer(nationality="Brazil") for _ in range(2)]
        assert service.validate_non_eu_restriction(starters, max_non_eu=1) is False
        assert service.validate_non_eu_restriction(starters, max_non_eu=2) is True

    # --- League-specific tests ---

    def test_league_with_no_restriction_allows_all_foreign(self, service):
        """Leagues like England/Spain have no non-EU limit"""
        starters = [MockPlayer(nationality="Brazil") for _ in range(11)]
        # england_premier_league is not in LEAGUE_FOREIGN_PLAYER_RULES
        assert service.validate_non_eu_restriction(starters, league_key="england_premier_league") is True

    def test_turkey_super_lig_restriction(self, service):
        """Turkey has max 3 non-EU in starting 11"""
        starters = [MockPlayer(nationality="Spain") for _ in range(8)]
        starters += [MockPlayer(nationality="Brazil") for _ in range(3)]
        assert service.validate_non_eu_restriction(starters, league_key="turkey_super_lig") is True

        starters_too_many = [MockPlayer(nationality="Spain") for _ in range(7)]
        starters_too_many += [MockPlayer(nationality="Brazil") for _ in range(4)]
        assert service.validate_non_eu_restriction(starters_too_many, league_key="turkey_super_lig") is False

    def test_china_super_league_restriction(self, service):
        """China has max 5 foreign in starting 11"""
        starters = [MockPlayer(nationality="Spain") for _ in range(6)]
        starters += [MockPlayer(nationality="Brazil") for _ in range(5)]
        assert service.validate_non_eu_restriction(starters, league_key="china_super_league") is True

        starters_too_many = [MockPlayer(nationality="Spain") for _ in range(5)]
        starters_too_many += [MockPlayer(nationality="Brazil") for _ in range(6)]
        assert service.validate_non_eu_restriction(starters_too_many, league_key="china_super_league") is False

    def test_has_foreign_player_restriction(self, service):
        """Check which leagues have restrictions"""
        assert service.has_foreign_player_restriction("turkey_super_lig") is True
        assert service.has_foreign_player_restriction("saudi_pro_league") is True
        assert service.has_foreign_player_restriction("england_premier_league") is False
        assert service.has_foreign_player_restriction("spain_la_liga") is False

    def test_get_league_foreign_rules_exists(self, service):
        """Get rules for a league that has them"""
        rules = service.get_league_foreign_rules("turkey_super_lig")
        assert rules is not None
        assert rules["max_foreign_starters"] == 3
        assert rules["rule_type"] == "non_eu"

    def test_get_league_foreign_rules_not_exists(self, service):
        """Get rules for a league without restrictions returns None"""
        rules = service.get_league_foreign_rules("england_premier_league")
        assert rules is None

    def test_get_league_foreign_rules_none_key(self, service):
        """None league_key returns None"""
        rules = service.get_league_foreign_rules(None)
        assert rules is None


# ===================================================================
# 7.12 Player attribute display tests
# ===================================================================


class TestPlayerProfile:
    """Tests for player attribute display."""

    def test_full_profile_structure(self, service, mock_squad_player, mock_player):
        profile = service.get_player_full_profile(mock_squad_player, mock_player)

        # Check top-level keys
        assert "id" in profile
        assert "name" in profile
        assert "position" in profile
        assert "age" in profile
        assert "nationality" in profile
        assert "ability" in profile
        assert "technical" in profile
        assert "mental" in profile
        assert "physical" in profile
        assert "contract" in profile
        assert "squad" in profile
        assert "statistics" in profile
        assert "financial" in profile
        assert "traits" in profile

    def test_profile_ability_section(self, service, mock_squad_player, mock_player):
        profile = service.get_player_full_profile(mock_squad_player, mock_player)
        assert profile["ability"]["ca"] == 150
        assert profile["ability"]["pa"] == 170
        assert profile["ability"]["effective_ca"] == 150  # morale 70 > 40

    def test_profile_effective_ca_with_low_morale(self, service, mock_player):
        sp = MockSquadPlayer(morale=30)
        profile = service.get_player_full_profile(sp, mock_player)
        # 150 - 5% = int(150 - 7.5) = 142
        assert profile["ability"]["effective_ca"] == 142

    def test_profile_technical_attributes(self, service, mock_squad_player, mock_player):
        profile = service.get_player_full_profile(mock_squad_player, mock_player)
        tech = profile["technical"]
        assert len(tech) == 14
        assert tech["finishing"] == 17
        assert tech["dribbling"] == 16

    def test_profile_mental_attributes(self, service, mock_squad_player, mock_player):
        profile = service.get_player_full_profile(mock_squad_player, mock_player)
        mental = profile["mental"]
        assert len(mental) == 14
        assert mental["composure"] == 16
        assert mental["flair"] == 17

    def test_profile_physical_attributes(self, service, mock_squad_player, mock_player):
        profile = service.get_player_full_profile(mock_squad_player, mock_player)
        phys = profile["physical"]
        assert len(phys) == 8
        assert phys["pace"] == 15
        assert phys["strength"] == 12

    def test_profile_contract_info(self, service, mock_squad_player, mock_player):
        profile = service.get_player_full_profile(mock_squad_player, mock_player)
        contract = profile["contract"]
        assert contract["wage"] == 50000
        assert contract["months_remaining"] == 30

    def test_profile_statistics(self, service, mock_squad_player, mock_player):
        profile = service.get_player_full_profile(mock_squad_player, mock_player)
        stats = profile["statistics"]
        assert stats["appearances"] == 20
        assert stats["goals"] == 5
        assert stats["assists"] == 8
        assert stats["goals_per_appearance"] == 0.25

    def test_profile_squad_info(self, service, mock_squad_player, mock_player):
        profile = service.get_player_full_profile(mock_squad_player, mock_player)
        squad = profile["squad"]
        assert squad["status"] == "FIRST_TEAM"
        assert squad["number"] == 7
        assert squad["morale"] == 70
