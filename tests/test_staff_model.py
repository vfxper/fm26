"""
Unit Tests for Staff Model
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.staff import Staff, StaffRole


class TestStaffModel:
    """Test suite for Staff model"""
    
    @pytest.mark.asyncio
    async def test_create_staff_with_all_attributes(self, test_db_session):
        """Test creating a staff member with all required attributes"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 3)  # 3 years
        
        staff = Staff(
            career_id=1,
            club_id=1,
            name="John Smith",
            role=StaffRole.FITNESS_COACH,
            age=45,
            nationality="England",
            coaching=16,
            tactical_knowledge=14,
            man_management=15,
            scouting=10,
            medical=12,
            fitness=18,
            technical=13,
            mental=14,
            wage=5000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=3,
            morale=75,
            performance_rating=16
        )
        
        test_db_session.add(staff)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        
        assert staff.id is not None
        assert staff.career_id == 1
        assert staff.club_id == 1
        assert staff.name == "John Smith"
        assert staff.role == StaffRole.FITNESS_COACH
        assert staff.age == 45
        assert staff.nationality == "England"
        assert staff.coaching == 16
        assert staff.fitness == 18
        assert staff.wage == 5000
        assert staff.contract_years == 3
        assert staff.morale == 75
        assert staff.performance_rating == 16
    
    @pytest.mark.asyncio
    async def test_staff_role_enum(self, test_db_session):
        """Test staff role enumeration values"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Test CHIEF_SCOUT role
        scout = Staff(
            career_id=1,
            club_id=1,
            name="Scout Master",
            role=StaffRole.CHIEF_SCOUT,
            age=50,
            nationality="Spain",
            scouting=19,
            wage=6000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(scout)
        await test_db_session.commit()
        await test_db_session.refresh(scout)
        
        assert scout.role == StaffRole.CHIEF_SCOUT
        assert scout.get_role_display_name() == "Chief Scout"
    
    @pytest.mark.asyncio
    async def test_all_staff_roles(self, test_db_session):
        """Test creating staff members with all 8 roles"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        roles = [
            StaffRole.ASSISTANT_MANAGER,
            StaffRole.FITNESS_COACH,
            StaffRole.GOALKEEPING_COACH,
            StaffRole.DEFENSIVE_COACH,
            StaffRole.ATTACKING_COACH,
            StaffRole.CHIEF_SCOUT,
            StaffRole.PHYSIO,
            StaffRole.SPORTS_SCIENTIST,
        ]
        
        for i, role in enumerate(roles):
            staff = Staff(
                career_id=1,
                club_id=1,
                name=f"Staff Member {i+1}",
                role=role,
                age=40,
                nationality="England",
                wage=4000,
                contract_start_date=now,
                contract_expiry_date=contract_expiry,
                contract_years=2
            )
            test_db_session.add(staff)
        
        await test_db_session.commit()
        
        # Query all staff
        result = await test_db_session.execute(
            select(Staff).where(Staff.career_id == 1)
        )
        all_staff = result.scalars().all()
        
        assert len(all_staff) == 8
    
    @pytest.mark.asyncio
    async def test_staff_age_constraint(self, test_db_session):
        """Test that age must be between 18 and 80"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Test invalid age (17)
        invalid_staff = Staff(
            career_id=1,
            club_id=1,
            name="Too Young",
            role=StaffRole.FITNESS_COACH,
            age=17,  # Invalid: must be >= 18
            nationality="England",
            wage=3000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(invalid_staff)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_staff_attribute_constraints(self, test_db_session):
        """Test that staff attributes must be between 1 and 20"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Test invalid coaching attribute (21)
        invalid_staff = Staff(
            career_id=1,
            club_id=1,
            name="Invalid Coach",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            coaching=21,  # Invalid: must be <= 20
            wage=3000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(invalid_staff)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_staff_wage_constraint(self, test_db_session):
        """Test that wage must be positive"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Test invalid wage (0)
        invalid_staff = Staff(
            career_id=1,
            club_id=1,
            name="No Wage",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            wage=0,  # Invalid: must be > 0
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(invalid_staff)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_staff_contract_years_constraint(self, test_db_session):
        """Test that contract_years must be between 1 and 5"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 6)
        
        # Test invalid contract_years (6)
        invalid_staff = Staff(
            career_id=1,
            club_id=1,
            name="Long Contract",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            wage=3000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=6  # Invalid: must be <= 5
        )
        
        test_db_session.add(invalid_staff)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_staff_morale_constraint(self, test_db_session):
        """Test that morale must be between 1 and 100"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Test invalid morale (101)
        invalid_staff = Staff(
            career_id=1,
            club_id=1,
            name="High Morale",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            wage=3000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2,
            morale=101  # Invalid: must be <= 100
        )
        
        test_db_session.add(invalid_staff)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_staff_performance_rating_constraint(self, test_db_session):
        """Test that performance_rating must be between 1 and 20"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Test invalid performance_rating (21)
        invalid_staff = Staff(
            career_id=1,
            club_id=1,
            name="High Performance",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            wage=3000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2,
            performance_rating=21  # Invalid: must be <= 20
        )
        
        test_db_session.add(invalid_staff)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_staff_to_dict(self, test_db_session):
        """Test converting staff to dictionary"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 3)
        
        staff = Staff(
            career_id=1,
            club_id=1,
            name="Test Coach",
            role=StaffRole.ATTACKING_COACH,
            age=42,
            nationality="Brazil",
            coaching=17,
            tactical_knowledge=16,
            man_management=15,
            scouting=11,
            medical=10,
            fitness=14,
            technical=16,
            mental=15,
            wage=5500,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=3,
            morale=80,
            performance_rating=17
        )
        
        test_db_session.add(staff)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        
        staff_dict = staff.to_dict()
        
        assert staff_dict["career_id"] == 1
        assert staff_dict["club_id"] == 1
        assert staff_dict["name"] == "Test Coach"
        assert staff_dict["role"] == "attacking_coach"
        assert staff_dict["age"] == 42
        assert staff_dict["nationality"] == "Brazil"
        assert staff_dict["attributes"]["coaching"] == 17
        assert staff_dict["attributes"]["tactical_knowledge"] == 16
        assert staff_dict["contract"]["wage"] == 5500
        assert staff_dict["contract"]["contract_years"] == 3
        assert staff_dict["morale"] == 80
        assert staff_dict["performance_rating"] == 17
    
    @pytest.mark.asyncio
    async def test_staff_repr(self, test_db_session):
        """Test staff string representation"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        staff = Staff(
            career_id=1,
            club_id=1,
            name="John Doe",
            role=StaffRole.PHYSIO,
            age=38,
            nationality="Germany",
            wage=4500,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(staff)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        
        repr_str = repr(staff)
        
        assert "Staff" in repr_str
        assert "John Doe" in repr_str
        assert "physio" in repr_str
        assert "club_id=1" in repr_str
    
    @pytest.mark.asyncio
    async def test_get_primary_attribute(self, test_db_session):
        """Test getting primary attribute for different roles"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Fitness Coach - primary attribute is fitness
        fitness_coach = Staff(
            career_id=1,
            club_id=1,
            name="Fitness Coach",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            coaching=14,
            fitness=18,
            wage=4000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(fitness_coach)
        await test_db_session.commit()
        await test_db_session.refresh(fitness_coach)
        
        assert fitness_coach.get_primary_attribute() == 18
        
        # Chief Scout - primary attribute is scouting
        chief_scout = Staff(
            career_id=1,
            club_id=1,
            name="Chief Scout",
            role=StaffRole.CHIEF_SCOUT,
            age=50,
            nationality="Spain",
            coaching=12,
            scouting=19,
            wage=5000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(chief_scout)
        await test_db_session.commit()
        await test_db_session.refresh(chief_scout)
        
        assert chief_scout.get_primary_attribute() == 19
    
    @pytest.mark.asyncio
    async def test_get_average_attribute(self, test_db_session):
        """Test calculating average attribute"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        staff = Staff(
            career_id=1,
            club_id=1,
            name="Average Coach",
            role=StaffRole.DEFENSIVE_COACH,
            age=45,
            nationality="Italy",
            coaching=16,
            tactical_knowledge=14,
            man_management=15,
            scouting=10,
            medical=12,
            fitness=13,
            technical=14,
            mental=14,
            wage=4500,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(staff)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        
        avg = staff.get_average_attribute()
        expected_avg = (16 + 14 + 15 + 10 + 12 + 13 + 14 + 14) / 8
        assert abs(avg - expected_avg) < 0.01
    
    @pytest.mark.asyncio
    async def test_is_high_morale(self, test_db_session):
        """Test checking if staff has high morale"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        staff = Staff(
            career_id=1,
            club_id=1,
            name="Happy Coach",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            wage=4000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2,
            morale=75
        )
        
        test_db_session.add(staff)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        
        assert staff.is_high_morale() is True
        assert staff.is_low_morale() is False
    
    @pytest.mark.asyncio
    async def test_is_low_morale(self, test_db_session):
        """Test checking if staff has low morale"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        staff = Staff(
            career_id=1,
            club_id=1,
            name="Unhappy Coach",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            wage=4000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2,
            morale=35
        )
        
        test_db_session.add(staff)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        
        assert staff.is_low_morale() is True
        assert staff.is_high_morale() is False
    
    @pytest.mark.asyncio
    async def test_provides_fitness_bonus(self, test_db_session):
        """Test checking if staff provides fitness bonus"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Fitness Coach with coaching > 15 should provide bonus
        good_fitness_coach = Staff(
            career_id=1,
            club_id=1,
            name="Elite Fitness Coach",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            coaching=16,
            wage=5000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(good_fitness_coach)
        await test_db_session.commit()
        await test_db_session.refresh(good_fitness_coach)
        
        assert good_fitness_coach.provides_fitness_bonus() is True
        assert good_fitness_coach.get_fitness_bonus_percentage() == 10.0
    
    @pytest.mark.asyncio
    async def test_provides_scouting_bonus(self, test_db_session):
        """Test checking if staff provides scouting bonus"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Chief Scout with scouting > 15 should provide bonus
        good_scout = Staff(
            career_id=1,
            club_id=1,
            name="Elite Scout",
            role=StaffRole.CHIEF_SCOUT,
            age=50,
            nationality="Spain",
            scouting=18,
            wage=6000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(good_scout)
        await test_db_session.commit()
        await test_db_session.refresh(good_scout)
        
        assert good_scout.provides_scouting_bonus() is True
        assert good_scout.get_scouting_time_reduction_percentage() == 20.0
    
    @pytest.mark.asyncio
    async def test_provides_medical_bonus(self, test_db_session):
        """Test checking if staff provides medical bonus"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Physio with medical > 15 should provide bonus
        good_physio = Staff(
            career_id=1,
            club_id=1,
            name="Elite Physio",
            role=StaffRole.PHYSIO,
            age=45,
            nationality="Germany",
            medical=17,
            wage=5500,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(good_physio)
        await test_db_session.commit()
        await test_db_session.refresh(good_physio)
        
        assert good_physio.provides_medical_bonus() is True
        assert good_physio.get_injury_recovery_reduction_percentage() == 10.0
    
    @pytest.mark.asyncio
    async def test_is_elite_staff(self, test_db_session):
        """Test checking if staff is elite"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        elite_coach = Staff(
            career_id=1,
            club_id=1,
            name="Elite Coach",
            role=StaffRole.ATTACKING_COACH,
            age=50,
            nationality="Argentina",
            coaching=19,
            wage=8000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(elite_coach)
        await test_db_session.commit()
        await test_db_session.refresh(elite_coach)
        
        assert elite_coach.is_elite_staff() is True
        assert elite_coach.is_good_staff() is True
    
    @pytest.mark.asyncio
    async def test_update_morale(self, test_db_session):
        """Test updating staff morale"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        staff = Staff(
            career_id=1,
            club_id=1,
            name="Test Coach",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            wage=4000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2,
            morale=70
        )
        
        test_db_session.add(staff)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        
        # Increase morale
        staff.update_morale(10)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        assert staff.morale == 80
        
        # Decrease morale
        staff.update_morale(-15)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        assert staff.morale == 65
        
        # Test morale cap at 100
        staff.update_morale(50)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        assert staff.morale == 100
        
        # Test morale floor at 1
        staff.update_morale(-150)
        await test_db_session.commit()
        await test_db_session.refresh(staff)
        assert staff.morale == 1
    
    @pytest.mark.asyncio
    async def test_query_staff_by_role(self, test_db_session):
        """Test querying staff by role"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Create multiple staff with different roles
        fitness_coach = Staff(
            career_id=1,
            club_id=1,
            name="Fitness Coach",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            wage=4000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        scout = Staff(
            career_id=1,
            club_id=1,
            name="Chief Scout",
            role=StaffRole.CHIEF_SCOUT,
            age=50,
            nationality="Spain",
            wage=5000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(fitness_coach)
        test_db_session.add(scout)
        await test_db_session.commit()
        
        # Query fitness coaches
        result = await test_db_session.execute(
            select(Staff).where(Staff.role == StaffRole.FITNESS_COACH)
        )
        fitness_coaches = result.scalars().all()
        
        assert len(fitness_coaches) == 1
        assert fitness_coaches[0].name == "Fitness Coach"
    
    @pytest.mark.asyncio
    async def test_query_staff_by_career_and_club(self, test_db_session):
        """Test querying staff by career and club"""
        now = datetime.now()
        contract_expiry = now + timedelta(days=365 * 2)
        
        # Create staff for different careers and clubs
        career1_club1_staff = Staff(
            career_id=1,
            club_id=1,
            name="Career 1 Club 1",
            role=StaffRole.FITNESS_COACH,
            age=40,
            nationality="England",
            wage=4000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        career1_club2_staff = Staff(
            career_id=1,
            club_id=2,
            name="Career 1 Club 2",
            role=StaffRole.CHIEF_SCOUT,
            age=50,
            nationality="Spain",
            wage=5000,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        career2_club1_staff = Staff(
            career_id=2,
            club_id=1,
            name="Career 2 Club 1",
            role=StaffRole.PHYSIO,
            age=45,
            nationality="Germany",
            wage=4500,
            contract_start_date=now,
            contract_expiry_date=contract_expiry,
            contract_years=2
        )
        
        test_db_session.add(career1_club1_staff)
        test_db_session.add(career1_club2_staff)
        test_db_session.add(career2_club1_staff)
        await test_db_session.commit()
        
        # Query staff for career 1, club 1
        result = await test_db_session.execute(
            select(Staff).where(
                Staff.career_id == 1,
                Staff.club_id == 1
            )
        )
        career1_club1_staff_list = result.scalars().all()
        
        assert len(career1_club1_staff_list) == 1
        assert career1_club1_staff_list[0].name == "Career 1 Club 1"
