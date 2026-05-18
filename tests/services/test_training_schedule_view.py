"""
Unit Tests for Training Schedule View (Task 10.7)

Tests the get_training_schedule_view method of TrainingService which provides
a formatted display representation of the current training schedule.
"""

import pytest
from datetime import date, timedelta

from app.models.training_schedule import TrainingSchedule, TrainingFocus, TrainingIntensity
from app.models.player import Player
from app.models.career import Career
from app.models.user import User
from app.models.club import Club
from app.models.squad_player import SquadPlayer, SquadStatus
from app.services.training_service import TrainingService


class TestTrainingScheduleView:
    """Test suite for training schedule view functionality"""

    @pytest.fixture
    async def test_user(self, test_db_session):
        """Create a test user"""
        user = User(
            telegram_id=999888777,
            username="training_view_user",
            first_name="ViewTest",
            language_code="en"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        return user

    @pytest.fixture
    async def test_club(self, test_db_session):
        """Create a test club"""
        club = Club(
            name="Training View FC",
            country="England",
            league="Premier League",
            reputation=75,
            balance=50000000,
            transfer_budget=20000000,
            wage_budget=500000
        )
        test_db_session.add(club)
        await test_db_session.commit()
        await test_db_session.refresh(club)
        return club

    @pytest.fixture
    async def test_career(self, test_db_session, test_user, test_club):
        """Create a test career"""
        career = Career(
            user_id=test_user.id,
            club_id=test_club.id,
            manager_name="View Test Manager"
        )
        test_db_session.add(career)
        await test_db_session.commit()
        await test_db_session.refresh(career)
        return career

    @pytest.fixture
    async def young_player(self, test_db_session):
        """Create a young player (age < 24) for improvement testing"""
        player = Player(
            uid="view_young_player_001",
            name="Young Talent",
            position="AM",
            age=20,
            ca=130,
            pa=180,
            nationality="Spain",
            club="Training View FC",
            corners=10, crossing=12, dribbling=15, finishing=14,
            first_touch=14, free_kicks=10, heading=8, long_shots=12,
            long_throws=6, marking=8, passing=14, penalty=10,
            tackling=8, technique=15,
            aggression=10, anticipation=13, bravery=11, composure=13,
            concentration=12, decisions=13, determination=15, flair=14,
            leadership=8, off_the_ball=14, positioning=12, teamwork=13,
            vision=14, work_rate=14,
            acceleration=16, agility=15, balance=14, jumping=12,
            stamina=14, pace=16, endurance=13, strength=11,
            price="£15,000,000", wage=30000,
            height=175, weight=70, left_foot=16, right_foot=10
        )
        test_db_session.add(player)
        await test_db_session.commit()
        await test_db_session.refresh(player)
        return player

    @pytest.fixture
    async def old_player(self, test_db_session):
        """Create an old player (age > 30) for decline testing"""
        player = Player(
            uid="view_old_player_001",
            name="Veteran Defender",
            position="DC",
            age=33,
            ca=145,
            pa=155,
            nationality="Italy",
            club="Training View FC",
            corners=6, crossing=8, dribbling=10, finishing=6,
            first_touch=12, free_kicks=8, heading=16, long_shots=6,
            long_throws=8, marking=17, passing=13, penalty=8,
            tackling=17, technique=12,
            aggression=14, anticipation=16, bravery=16, composure=15,
            concentration=16, decisions=16, determination=17, flair=8,
            leadership=16, off_the_ball=10, positioning=17, teamwork=15,
            vision=12, work_rate=14,
            acceleration=11, agility=10, balance=13, jumping=14,
            stamina=12, pace=10, endurance=12, strength=15,
            price="£8,000,000", wage=60000,
            height=188, weight=84, left_foot=14, right_foot=8
        )
        test_db_session.add(player)
        await test_db_session.commit()
        await test_db_session.refresh(player)
        return player

    @pytest.fixture
    async def mid_age_player(self, test_db_session):
        """Create a mid-age player (24-30) with no automatic changes"""
        player = Player(
            uid="view_mid_player_001",
            name="Prime Midfielder",
            position="CM",
            age=27,
            ca=155,
            pa=165,
            nationality="France",
            club="Training View FC",
            corners=12, crossing=13, dribbling=14, finishing=12,
            first_touch=15, free_kicks=12, heading=12, long_shots=13,
            long_throws=8, marking=13, passing=16, penalty=12,
            tackling=14, technique=15,
            aggression=12, anticipation=15, bravery=13, composure=15,
            concentration=15, decisions=16, determination=15, flair=13,
            leadership=13, off_the_ball=14, positioning=15, teamwork=16,
            vision=15, work_rate=15,
            acceleration=14, agility=14, balance=14, jumping=13,
            stamina=15, pace=13, endurance=14, strength=14,
            price="£30,000,000", wage=70000,
            height=182, weight=78, left_foot=15, right_foot=13
        )
        test_db_session.add(player)
        await test_db_session.commit()
        await test_db_session.refresh(player)
        return player

    @pytest.fixture
    async def young_squad_player(self, test_db_session, test_career, young_player):
        """Create squad player for young player"""
        today = date.today()
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=young_player.id,
            contract_start_date=today,
            contract_end_date=today + timedelta(days=365 * 4),
            wage=30000,
            squad_status=SquadStatus.FIRST_TEAM,
            squad_number=10,
            morale=80
        )
        test_db_session.add(squad_player)
        await test_db_session.commit()
        await test_db_session.refresh(squad_player)
        return squad_player

    @pytest.fixture
    async def old_squad_player(self, test_db_session, test_career, old_player):
        """Create squad player for old player"""
        today = date.today()
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=old_player.id,
            contract_start_date=today,
            contract_end_date=today + timedelta(days=365 * 2),
            wage=60000,
            squad_status=SquadStatus.KEY_PLAYER,
            squad_number=4,
            morale=70
        )
        test_db_session.add(squad_player)
        await test_db_session.commit()
        await test_db_session.refresh(squad_player)
        return squad_player

    @pytest.fixture
    async def mid_squad_player(self, test_db_session, test_career, mid_age_player):
        """Create squad player for mid-age player"""
        today = date.today()
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=mid_age_player.id,
            contract_start_date=today,
            contract_end_date=today + timedelta(days=365 * 3),
            wage=70000,
            squad_status=SquadStatus.KEY_PLAYER,
            squad_number=6,
            morale=85
        )
        test_db_session.add(squad_player)
        await test_db_session.commit()
        await test_db_session.refresh(squad_player)
        return squad_player

    @pytest.fixture
    async def training_schedules(
        self, test_db_session, test_career,
        young_player, old_player, mid_age_player,
        young_squad_player, old_squad_player, mid_squad_player
    ):
        """Create training schedules for all players"""
        schedules = [
            # Young player on attacking training, 3 consecutive weeks
            TrainingSchedule(
                career_id=test_career.id,
                player_id=young_player.id,
                squad_player_id=young_squad_player.id,
                training_focus=TrainingFocus.ATTACKING,
                training_intensity=TrainingIntensity.NORMAL,
                season=1,
                week=5,
                consecutive_weeks=3,
                is_injured=False
            ),
            # Old player on defending training, 6 consecutive weeks
            TrainingSchedule(
                career_id=test_career.id,
                player_id=old_player.id,
                squad_player_id=old_squad_player.id,
                training_focus=TrainingFocus.DEFENDING,
                training_intensity=TrainingIntensity.NORMAL,
                season=1,
                week=5,
                consecutive_weeks=6,
                is_injured=False
            ),
            # Mid-age player on tactics training, 2 consecutive weeks
            TrainingSchedule(
                career_id=test_career.id,
                player_id=mid_age_player.id,
                squad_player_id=mid_squad_player.id,
                training_focus=TrainingFocus.TACTICS,
                training_intensity=TrainingIntensity.NORMAL,
                season=1,
                week=5,
                consecutive_weeks=2,
                is_injured=False
            ),
        ]
        for s in schedules:
            test_db_session.add(s)
        await test_db_session.commit()
        for s in schedules:
            await test_db_session.refresh(s)
        return schedules

    @pytest.mark.asyncio
    async def test_get_training_schedule_view_returns_all_players(
        self, test_db_session, test_career, training_schedules
    ):
        """Test that the view returns all players with training schedules"""
        service = TrainingService(test_db_session)
        view = await service.get_training_schedule_view(
            career_id=test_career.id, season=1, week=5
        )

        assert view["total_players"] == 3
        assert view["season"] == 1
        assert view["week"] == 5
        assert len(view["players"]) == 3

    @pytest.mark.asyncio
    async def test_get_training_schedule_view_player_details(
        self, test_db_session, test_career, training_schedules,
        young_player, young_squad_player
    ):
        """Test that player entries contain correct details"""
        service = TrainingService(test_db_session)
        view = await service.get_training_schedule_view(
            career_id=test_career.id, season=1, week=5
        )

        # Find the young player entry
        young_entry = next(
            p for p in view["players"] if p["player_id"] == young_player.id
        )

        assert young_entry["name"] == "Young Talent"
        assert young_entry["position"] == "AM"
        assert young_entry["age"] == 20
        assert young_entry["squad_number"] == 10
        assert young_entry["training_focus"] == "attacking"
        assert young_entry["training_focus_display"] == "Attacking"
        assert young_entry["training_intensity"] == "normal"
        assert young_entry["consecutive_weeks"] == 3
        assert young_entry["is_injured"] is False

    @pytest.mark.asyncio
    async def test_get_training_schedule_view_young_player_progress(
        self, test_db_session, test_career, training_schedules, young_player
    ):
        """Test progress calculation for young player (improvement path)"""
        service = TrainingService(test_db_session)
        view = await service.get_training_schedule_view(
            career_id=test_career.id, season=1, week=5
        )

        young_entry = next(
            p for p in view["players"] if p["player_id"] == young_player.id
        )

        progress = young_entry["progress"]
        assert progress["eligible"] is True
        assert progress["type"] == "improvement"
        assert progress["current_weeks"] == 3
        assert progress["required_weeks"] == 4
        assert progress["percentage"] == 75

    @pytest.mark.asyncio
    async def test_get_training_schedule_view_old_player_progress(
        self, test_db_session, test_career, training_schedules, old_player
    ):
        """Test progress calculation for old player (decline path)"""
        service = TrainingService(test_db_session)
        view = await service.get_training_schedule_view(
            career_id=test_career.id, season=1, week=5
        )

        old_entry = next(
            p for p in view["players"] if p["player_id"] == old_player.id
        )

        progress = old_entry["progress"]
        assert progress["eligible"] is True
        assert progress["type"] == "decline"
        assert progress["current_weeks"] == 6
        assert progress["required_weeks"] == 8
        assert progress["percentage"] == 75

    @pytest.mark.asyncio
    async def test_get_training_schedule_view_mid_age_player_progress(
        self, test_db_session, test_career, training_schedules, mid_age_player
    ):
        """Test progress calculation for mid-age player (no changes)"""
        service = TrainingService(test_db_session)
        view = await service.get_training_schedule_view(
            career_id=test_career.id, season=1, week=5
        )

        mid_entry = next(
            p for p in view["players"] if p["player_id"] == mid_age_player.id
        )

        progress = mid_entry["progress"]
        assert progress["eligible"] is False
        assert progress["type"] == "none"
        assert progress["percentage"] == 0

    @pytest.mark.asyncio
    async def test_get_training_schedule_view_focus_summary(
        self, test_db_session, test_career, training_schedules
    ):
        """Test that focus summary correctly counts players per area"""
        service = TrainingService(test_db_session)
        view = await service.get_training_schedule_view(
            career_id=test_career.id, season=1, week=5
        )

        focus_summary = view["focus_summary"]
        assert focus_summary["attacking"] == 1
        assert focus_summary["defending"] == 1
        assert focus_summary["tactics"] == 1

    @pytest.mark.asyncio
    async def test_get_training_schedule_view_injured_player(
        self, test_db_session, test_career,
        young_player, young_squad_player
    ):
        """Test that injured players are correctly identified"""
        # Create an injured player schedule
        schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=young_player.id,
            squad_player_id=young_squad_player.id,
            training_focus=TrainingFocus.REHABILITATION,
            training_intensity=TrainingIntensity.LIGHT,
            season=1,
            week=10,
            consecutive_weeks=2,
            is_injured=True
        )
        test_db_session.add(schedule)
        await test_db_session.commit()

        service = TrainingService(test_db_session)
        view = await service.get_training_schedule_view(
            career_id=test_career.id, season=1, week=10
        )

        assert len(view["injured_players"]) == 1
        injured = view["injured_players"][0]
        assert injured["player_id"] == young_player.id
        assert injured["is_injured"] is True
        assert injured["training_focus"] == "rehabilitation"
        assert injured["training_focus_display"] == "Rehabilitation"

    @pytest.mark.asyncio
    async def test_get_training_schedule_view_empty_schedule(
        self, test_db_session, test_career
    ):
        """Test view returns empty result when no schedules exist"""
        service = TrainingService(test_db_session)
        view = await service.get_training_schedule_view(
            career_id=test_career.id, season=1, week=99
        )

        assert view["total_players"] == 0
        assert view["players"] == []
        assert view["injured_players"] == []
        assert view["focus_summary"] == {}
        assert view["training_intensity"] == "normal"

    @pytest.mark.asyncio
    async def test_get_training_schedule_view_affected_attributes(
        self, test_db_session, test_career, training_schedules, young_player
    ):
        """Test that affected attributes are included for each player"""
        service = TrainingService(test_db_session)
        view = await service.get_training_schedule_view(
            career_id=test_career.id, season=1, week=5
        )

        young_entry = next(
            p for p in view["players"] if p["player_id"] == young_player.id
        )

        # Attacking focus should affect these attributes
        assert "finishing" in young_entry["affected_attributes"]
        assert "dribbling" in young_entry["affected_attributes"]
        assert "passing" in young_entry["affected_attributes"]

    @pytest.mark.asyncio
    async def test_get_training_schedule_view_training_intensity(
        self, test_db_session, test_career,
        young_player, young_squad_player
    ):
        """Test that training intensity is correctly reported"""
        schedule = TrainingSchedule(
            career_id=test_career.id,
            player_id=young_player.id,
            squad_player_id=young_squad_player.id,
            training_focus=TrainingFocus.FITNESS,
            training_intensity=TrainingIntensity.HEAVY,
            season=2,
            week=1,
            consecutive_weeks=1,
            is_injured=False
        )
        test_db_session.add(schedule)
        await test_db_session.commit()

        service = TrainingService(test_db_session)
        view = await service.get_training_schedule_view(
            career_id=test_career.id, season=2, week=1
        )

        assert view["training_intensity"] == "heavy"


class TestImprovementProgressCalculation:
    """Test the _calculate_improvement_progress helper method"""

    def test_young_player_zero_weeks(self):
        """Young player with 0 weeks should show 0% progress"""
        service = TrainingService.__new__(TrainingService)
        progress = service._calculate_improvement_progress(20, 1)
        assert progress["type"] == "improvement"
        assert progress["percentage"] == 25

    def test_young_player_full_progress(self):
        """Young player at 4 weeks should show 100% progress"""
        service = TrainingService.__new__(TrainingService)
        progress = service._calculate_improvement_progress(20, 4)
        assert progress["type"] == "improvement"
        assert progress["percentage"] == 100

    def test_young_player_over_threshold(self):
        """Young player over threshold should cap at 100%"""
        service = TrainingService.__new__(TrainingService)
        progress = service._calculate_improvement_progress(20, 6)
        assert progress["percentage"] == 100

    def test_old_player_decline_progress(self):
        """Old player should show decline progress"""
        service = TrainingService.__new__(TrainingService)
        progress = service._calculate_improvement_progress(33, 4)
        assert progress["type"] == "decline"
        assert progress["required_weeks"] == 8
        assert progress["percentage"] == 50

    def test_mid_age_player_no_progress(self):
        """Mid-age player should show no automatic changes"""
        service = TrainingService.__new__(TrainingService)
        progress = service._calculate_improvement_progress(27, 5)
        assert progress["type"] == "none"
        assert progress["eligible"] is False
        assert progress["percentage"] == 0


class TestFocusDisplayName:
    """Test the _get_focus_display_name static method"""

    def test_all_focus_areas_have_display_names(self):
        """All training focus areas should have human-readable display names"""
        for focus in TrainingFocus:
            display_name = TrainingService._get_focus_display_name(focus)
            assert display_name is not None
            assert len(display_name) > 0
            # Should not be the raw enum value (except for simple ones)
            assert display_name[0].isupper()

    def test_specific_display_names(self):
        """Test specific display name mappings"""
        assert TrainingService._get_focus_display_name(TrainingFocus.SET_PIECES) == "Set Pieces"
        assert TrainingService._get_focus_display_name(TrainingFocus.INDIVIDUAL_TECHNICAL) == "Individual Technical"
        assert TrainingService._get_focus_display_name(TrainingFocus.REHABILITATION) == "Rehabilitation"
