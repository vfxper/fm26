"""
Demonstration: 8 Training Focus Areas

This script demonstrates how the 8 training focus areas work in the Training Module.
It shows:
1. All available training focus areas
2. Which attributes each focus area affects
3. How training intensity affects development and injury risk
4. Player development rules based on age
"""

from app.models.training_schedule import TrainingFocus, TrainingIntensity, TrainingSchedule


def print_header(title):
    """Print a formatted header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()


def print_section(title):
    """Print a formatted section header."""
    print()
    print(f"--- {title} ---")
    print()


def demo_training_focus_areas():
    """Demonstrate all 8 training focus areas."""
    
    print_header("TRAINING FOCUS AREAS DEMONSTRATION")
    
    # List all 8 training focus areas
    print("The Training Module supports 8 training focus areas:")
    print()
    
    focus_areas = [
        TrainingFocus.GENERAL,
        TrainingFocus.FITNESS,
        TrainingFocus.TACTICS,
        TrainingFocus.ATTACKING,
        TrainingFocus.DEFENDING,
        TrainingFocus.SET_PIECES,
        TrainingFocus.INDIVIDUAL_TECHNICAL,
        TrainingFocus.INDIVIDUAL_MENTAL,
    ]
    
    for i, focus in enumerate(focus_areas, 1):
        print(f"  {i}. {focus.value.upper().replace('_', ' ')}")
    
    print()
    print(f"Total: {len(focus_areas)} training focus areas")
    
    # Show affected attributes for each focus area
    print_section("AFFECTED ATTRIBUTES BY FOCUS AREA")
    
    for focus in focus_areas:
        # Create a temporary training schedule to demonstrate
        schedule = TrainingSchedule(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            training_focus=focus,
            training_intensity=TrainingIntensity.NORMAL,
            season=1,
            week=1
        )
        
        affected_attrs = schedule.get_affected_attributes()
        
        print(f"📋 {focus.value.upper().replace('_', ' ')}")
        print(f"   Affects {len(affected_attrs)} attributes:")
        
        # Format attributes in rows of 3
        for i in range(0, len(affected_attrs), 3):
            attrs_row = affected_attrs[i:i+3]
            print(f"   • {', '.join(attrs_row)}")
        
        print()


def demo_training_intensity():
    """Demonstrate training intensity effects."""
    
    print_section("TRAINING INTENSITY EFFECTS")
    
    intensities = [
        TrainingIntensity.LIGHT,
        TrainingIntensity.NORMAL,
        TrainingIntensity.HEAVY,
    ]
    
    print("Training intensity affects both injury risk and development rate:")
    print()
    
    for intensity in intensities:
        schedule = TrainingSchedule(
            career_id=1,
            player_id=1,
            squad_player_id=1,
            training_focus=TrainingFocus.GENERAL,
            training_intensity=intensity,
            season=1,
            week=1
        )
        
        injury_risk = schedule.get_injury_risk_multiplier()
        dev_rate = schedule.get_development_rate_multiplier()
        
        print(f"⚙️  {intensity.value.upper()}")
        print(f"   Injury Risk: {injury_risk}x", end="")
        if injury_risk < 1.0:
            print(" (safer)")
        elif injury_risk > 1.0:
            print(" (riskier)")
        else:
            print(" (baseline)")
        
        print(f"   Development Rate: {dev_rate}x", end="")
        if dev_rate < 1.0:
            print(" (slower)")
        elif dev_rate > 1.0:
            print(" (faster)")
        else:
            print(" (baseline)")
        
        print()


def demo_player_development_rules():
    """Demonstrate player development rules."""
    
    print_section("PLAYER DEVELOPMENT RULES")
    
    # Young player development
    print("🌟 YOUNG PLAYERS (Under 24 years old)")
    print()
    
    young_schedule = TrainingSchedule(
        career_id=1,
        player_id=1,
        squad_player_id=1,
        training_focus=TrainingFocus.ATTACKING,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=1,
        consecutive_weeks=4
    )
    
    player_age = 22
    is_ready = young_schedule.is_ready_for_improvement(player_age)
    
    print(f"   Player Age: {player_age}")
    print(f"   Training Focus: {young_schedule.training_focus.value.upper().replace('_', ' ')}")
    print(f"   Consecutive Weeks: {young_schedule.consecutive_weeks}")
    print(f"   Ready for Improvement: {'✅ YES' if is_ready else '❌ NO'}")
    print()
    print("   Rule: Players under 24 improve after 4 consecutive weeks in same focus")
    print("   Improvement: +1 to relevant attributes (capped at PA)")
    print()
    
    # Older player decline
    print("👴 OLDER PLAYERS (Over 30 years old)")
    print()
    
    old_schedule = TrainingSchedule(
        career_id=1,
        player_id=2,
        squad_player_id=2,
        training_focus=TrainingFocus.TACTICS,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=1,
        consecutive_weeks=8
    )
    
    old_player_age = 32
    should_decline = old_schedule.should_decline_attributes(old_player_age)
    
    print(f"   Player Age: {old_player_age}")
    print(f"   Training Focus: {old_schedule.training_focus.value.upper().replace('_', ' ')}")
    print(f"   Consecutive Weeks: {old_schedule.consecutive_weeks}")
    print(f"   Should Decline: {'⚠️  YES' if should_decline else '✅ NO'}")
    print()
    print("   Rule: Players over 30 decline after 8 weeks without fitness training")
    print("   Decline: -1 to stamina and pace attributes")
    print()


def demo_automatic_rehabilitation():
    """Demonstrate automatic rehabilitation for injured players."""
    
    print_section("AUTOMATIC REHABILITATION")
    
    print("When a player gets injured, they are automatically assigned to rehabilitation:")
    print()
    
    # Create a normal training schedule
    schedule = TrainingSchedule(
        career_id=1,
        player_id=1,
        squad_player_id=1,
        training_focus=TrainingFocus.ATTACKING,
        training_intensity=TrainingIntensity.NORMAL,
        season=1,
        week=1,
        consecutive_weeks=3,
        is_injured=False
    )
    
    print(f"   Before Injury:")
    print(f"   • Training Focus: {schedule.training_focus.value.upper().replace('_', ' ')}")
    print(f"   • Consecutive Weeks: {schedule.consecutive_weeks}")
    print(f"   • Is Injured: {schedule.is_injured}")
    print()
    
    # Simulate injury
    schedule.set_injured()
    
    print(f"   After Injury:")
    print(f"   • Training Focus: {schedule.training_focus.value.upper().replace('_', ' ')}")
    print(f"   • Consecutive Weeks: {schedule.consecutive_weeks} (reset)")
    print(f"   • Is Injured: {schedule.is_injured}")
    print()
    print("   ℹ️  Rehabilitation provides no attribute improvements - recovery only")
    print()


def demo_usage_example():
    """Show a practical usage example."""
    
    print_section("PRACTICAL USAGE EXAMPLE")
    
    print("Example: Setting up training for a young striker")
    print()
    
    # Create a training schedule for a young striker
    striker_schedule = TrainingSchedule(
        career_id=1,
        player_id=10,
        squad_player_id=10,
        training_focus=TrainingFocus.ATTACKING,
        training_intensity=TrainingIntensity.HEAVY,
        season=1,
        week=15,
        consecutive_weeks=1,
        is_injured=False
    )
    
    print("   Player: Young Striker (Age 21)")
    print(f"   Training Focus: {striker_schedule.training_focus.value.upper().replace('_', ' ')}")
    print(f"   Training Intensity: {striker_schedule.training_intensity.value.upper()}")
    print()
    
    affected_attrs = striker_schedule.get_affected_attributes()
    print(f"   Attributes Being Trained ({len(affected_attrs)}):")
    print(f"   {', '.join(affected_attrs)}")
    print()
    
    injury_risk = striker_schedule.get_injury_risk_multiplier()
    dev_rate = striker_schedule.get_development_rate_multiplier()
    
    print(f"   Effects:")
    print(f"   • Injury Risk: {injury_risk}x (50% higher due to HEAVY intensity)")
    print(f"   • Development Rate: {dev_rate}x (20% faster due to HEAVY intensity)")
    print()
    
    print(f"   Development Progress:")
    print(f"   • Consecutive Weeks: {striker_schedule.consecutive_weeks}/4")
    print(f"   • Weeks Until Improvement: {4 - striker_schedule.consecutive_weeks}")
    print(f"   • Expected Improvement: +1 to attacking attributes after 4 weeks")
    print()


def main():
    """Run all demonstrations."""
    
    demo_training_focus_areas()
    demo_training_intensity()
    demo_player_development_rules()
    demo_automatic_rehabilitation()
    demo_usage_example()
    
    print_header("DEMONSTRATION COMPLETE")
    
    print("Summary:")
    print()
    print("✅ 8 training focus areas implemented")
    print("✅ Each focus area affects specific player attributes")
    print("✅ 3 training intensity levels (Light, Normal, Heavy)")
    print("✅ Age-based player development rules")
    print("✅ Automatic rehabilitation for injured players")
    print("✅ Consecutive weeks tracking for development")
    print()
    print("The Training Module foundation is complete and ready for use!")
    print()


if __name__ == "__main__":
    main()
