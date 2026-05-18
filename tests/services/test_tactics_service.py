"""
Tests for TacticsService - Tactic Editor Implementation

Covers tasks 18.1 through 18.13:
- 18.1: 15 standard formations
- 18.2: Player role assignment system
- 18.3: Team mentality configuration (6 levels)
- 18.4: Pressing intensity settings (4 levels)
- 18.5: Defensive line height configuration (4 levels)
- 18.6: Width configuration (3 levels)
- 18.7: Tempo configuration (3 levels)
- 18.8: Tactic preset storage (up to 5 presets)
- 18.9: Tactic application in match simulation
- 18.10: Visual pitch diagram display
- 18.11: Drag-and-drop player positioning
- 18.12: Position compatibility validation
- 18.13: In-match tactical adjustments
"""

import pytest

from app.services.tactics_service import (
    TacticsService,
    TacticPreset,
    TacticMentality,
    PressingIntensity,
    DefensiveLineHeight,
    TeamWidth,
    TeamTempo,
    PositionType,
    Formation,
    PositionCoordinate,
    PlayerPositionAssignment,
    MatchModifiers,
    STANDARD_FORMATIONS,
    POSITION_ROLES,
)


@pytest.fixture
def service():
    """Create a TacticsService instance."""
    return TacticsService()


@pytest.fixture
def default_preset():
    """Create a default tactic preset."""
    return TacticPreset(name="Default", formation_name="4-4-2")


@pytest.fixture
def preset_with_players():
    """Create a preset with player assignments."""
    preset = TacticPreset(name="Test", formation_name="4-4-2")
    preset.player_assignments = [
        PlayerPositionAssignment(player_id=1, position_index=0, role="Goalkeeper"),
        PlayerPositionAssignment(player_id=2, position_index=1, role="Full-Back"),
        PlayerPositionAssignment(player_id=10, position_index=9, role="Poacher"),
        PlayerPositionAssignment(player_id=11, position_index=10, role="Target Man"),
    ]
    return preset


# ============================================================================
# Task 18.1: 15 Standard Formations
# ============================================================================


class TestFormations:
    """Tests for 15 standard formations."""

    def test_has_15_formations(self, service):
        """Verify exactly 15 formations are defined."""
        formations = service.get_all_formations()
        assert len(formations) == 15

    def test_all_formation_names(self, service):
        """Verify all expected formation names exist."""
        expected = [
            "4-4-2", "4-3-3", "3-5-2", "4-2-3-1", "5-3-2",
            "4-1-4-1", "4-5-1", "3-4-3", "4-4-1-1", "4-3-2-1",
            "5-4-1", "4-2-2-2", "3-4-1-2", "4-1-2-1-2", "4-3-1-2",
        ]
        names = service.get_formation_names()
        for name in expected:
            assert name in names, f"Formation {name} not found"

    def test_each_formation_has_11_positions(self, service):
        """Every formation must have exactly 11 positions."""
        for formation in service.get_all_formations():
            assert len(formation.positions) == 11, (
                f"Formation {formation.name} has {len(formation.positions)} positions"
            )

    def test_each_formation_has_goalkeeper(self, service):
        """Every formation must include a goalkeeper."""
        for formation in service.get_all_formations():
            gk_positions = [
                p for p in formation.positions if p.position_type == PositionType.GK
            ]
            assert len(gk_positions) == 1, (
                f"Formation {formation.name} has {len(gk_positions)} goalkeepers"
            )

    def test_positions_within_bounds(self, service):
        """All position coordinates must be within 0-100."""
        for formation in service.get_all_formations():
            for pos in formation.positions:
                assert 0 <= pos.x <= 100, (
                    f"{formation.name}: x={pos.x} out of bounds"
                )
                assert 0 <= pos.y <= 100, (
                    f"{formation.name}: y={pos.y} out of bounds"
                )

    def test_get_formation_by_name(self, service):
        """Can retrieve a specific formation by name."""
        formation = service.get_formation("4-3-3")
        assert formation is not None
        assert formation.name == "4-3-3"

    def test_get_invalid_formation(self, service):
        """Returns None for invalid formation name."""
        assert service.get_formation("9-9-9") is None

    def test_formation_serialization(self, service):
        """Formations can be serialized and deserialized."""
        formation = service.get_formation("4-4-2")
        data = formation.to_dict()
        restored = Formation.from_dict(data)
        assert restored.name == formation.name
        assert len(restored.positions) == 11


# ============================================================================
# Task 18.2: Player Role Assignment System
# ============================================================================


class TestPlayerRoles:
    """Tests for player role assignment."""

    def test_all_position_types_have_roles(self, service):
        """Every position type should have at least one role."""
        for pos_type in PositionType:
            roles = service.get_roles_for_position(pos_type)
            assert len(roles) >= 1, f"No roles for {pos_type.value}"

    def test_striker_roles(self, service):
        """Striker position should have expected roles."""
        roles = service.get_roles_for_position(PositionType.ST)
        role_names = [r.name for r in roles]
        assert "Poacher" in role_names
        assert "Target Man" in role_names
        assert "Complete Forward" in role_names

    def test_goalkeeper_roles(self, service):
        """Goalkeeper should have specific roles."""
        roles = service.get_roles_for_position(PositionType.GK)
        role_names = [r.name for r in roles]
        assert "Goalkeeper" in role_names
        assert "Sweeper Keeper" in role_names

    def test_get_roles_for_formation_position(self, service):
        """Can get roles for a specific position index in a formation."""
        # Position 0 in 4-4-2 is GK
        roles = service.get_roles_for_formation_position("4-4-2", 0)
        role_names = [r.name for r in roles]
        assert "Goalkeeper" in role_names

    def test_get_roles_invalid_formation(self, service):
        """Returns empty list for invalid formation."""
        roles = service.get_roles_for_formation_position("invalid", 0)
        assert roles == []

    def test_get_roles_invalid_position_index(self, service):
        """Returns empty list for invalid position index."""
        roles = service.get_roles_for_formation_position("4-4-2", 99)
        assert roles == []

    def test_assign_valid_role(self, service, default_preset):
        """Can assign a valid role to a position."""
        # Position 9 in 4-4-2 is ST
        default_preset.player_assignments.append(
            PlayerPositionAssignment(player_id=10, position_index=9, role="Poacher")
        )
        result = service.assign_role(default_preset, 9, "Target Man")
        assert result is True

    def test_assign_invalid_role(self, service, default_preset):
        """Cannot assign an invalid role to a position."""
        # Position 0 is GK - "Poacher" is not valid for GK
        result = service.assign_role(default_preset, 0, "Poacher")
        assert result is False


# ============================================================================
# Task 18.3: Team Mentality Configuration (6 levels)
# ============================================================================


class TestMentality:
    """Tests for team mentality configuration."""

    def test_six_mentality_levels(self, service):
        """Should have exactly 6 mentality levels."""
        levels = service.get_mentality_levels()
        assert len(levels) == 6

    def test_mentality_values(self, service):
        """Verify all mentality level values."""
        levels = service.get_mentality_levels()
        values = [l.value for l in levels]
        assert "Very Defensive" in values
        assert "Defensive" in values
        assert "Cautious" in values
        assert "Balanced" in values
        assert "Attacking" in values
        assert "Very Attacking" in values

    def test_set_mentality(self, service, default_preset):
        """Can set mentality on a preset."""
        service.set_mentality(default_preset, TacticMentality.ATTACKING)
        assert default_preset.mentality == TacticMentality.ATTACKING


# ============================================================================
# Task 18.4: Pressing Intensity Settings (4 levels)
# ============================================================================


class TestPressing:
    """Tests for pressing intensity settings."""

    def test_four_pressing_levels(self, service):
        """Should have exactly 4 pressing levels."""
        levels = service.get_pressing_levels()
        assert len(levels) == 4

    def test_pressing_values(self, service):
        """Verify all pressing level values."""
        levels = service.get_pressing_levels()
        values = [l.value for l in levels]
        assert "Low" in values
        assert "Medium" in values
        assert "High" in values
        assert "Extreme" in values

    def test_set_pressing(self, service, default_preset):
        """Can set pressing on a preset."""
        service.set_pressing(default_preset, PressingIntensity.EXTREME)
        assert default_preset.pressing == PressingIntensity.EXTREME


# ============================================================================
# Task 18.5: Defensive Line Height Configuration (4 levels)
# ============================================================================


class TestDefensiveLine:
    """Tests for defensive line height configuration."""

    def test_four_line_levels(self, service):
        """Should have exactly 4 defensive line levels."""
        levels = service.get_defensive_line_levels()
        assert len(levels) == 4

    def test_line_values(self, service):
        """Verify all defensive line values."""
        levels = service.get_defensive_line_levels()
        values = [l.value for l in levels]
        assert "Deep" in values
        assert "Standard" in values
        assert "High" in values
        assert "Very High" in values

    def test_set_defensive_line(self, service, default_preset):
        """Can set defensive line on a preset."""
        service.set_defensive_line(default_preset, DefensiveLineHeight.VERY_HIGH)
        assert default_preset.defensive_line == DefensiveLineHeight.VERY_HIGH


# ============================================================================
# Task 18.6: Width Configuration (3 levels)
# ============================================================================


class TestWidth:
    """Tests for width configuration."""

    def test_three_width_levels(self, service):
        """Should have exactly 3 width levels."""
        levels = service.get_width_levels()
        assert len(levels) == 3

    def test_width_values(self, service):
        """Verify all width values."""
        levels = service.get_width_levels()
        values = [l.value for l in levels]
        assert "Narrow" in values
        assert "Normal" in values
        assert "Wide" in values

    def test_set_width(self, service, default_preset):
        """Can set width on a preset."""
        service.set_width(default_preset, TeamWidth.WIDE)
        assert default_preset.width == TeamWidth.WIDE


# ============================================================================
# Task 18.7: Tempo Configuration (3 levels)
# ============================================================================


class TestTempo:
    """Tests for tempo configuration."""

    def test_three_tempo_levels(self, service):
        """Should have exactly 3 tempo levels."""
        levels = service.get_tempo_levels()
        assert len(levels) == 3

    def test_tempo_values(self, service):
        """Verify all tempo values."""
        levels = service.get_tempo_levels()
        values = [l.value for l in levels]
        assert "Slow" in values
        assert "Normal" in values
        assert "Fast" in values

    def test_set_tempo(self, service, default_preset):
        """Can set tempo on a preset."""
        service.set_tempo(default_preset, TeamTempo.FAST)
        assert default_preset.tempo == TeamTempo.FAST


# ============================================================================
# Task 18.8: Tactic Preset Storage (up to 5 presets)
# ============================================================================


class TestPresetStorage:
    """Tests for tactic preset storage."""

    def test_create_preset(self, service):
        """Can create a new preset."""
        preset = service.create_preset("Attack", "4-3-3", [])
        assert preset is not None
        assert preset.name == "Attack"
        assert preset.formation_name == "4-3-3"

    def test_max_5_presets(self, service):
        """Cannot create more than 5 presets."""
        existing = [
            TacticPreset(name=f"Preset {i}", formation_name="4-4-2")
            for i in range(5)
        ]
        result = service.create_preset("Sixth", "4-4-2", existing)
        assert result is None

    def test_create_with_invalid_formation(self, service):
        """Cannot create preset with invalid formation."""
        result = service.create_preset("Bad", "9-9-9", [])
        assert result is None

    def test_delete_preset(self, service):
        """Can delete a preset by name."""
        presets = [
            TacticPreset(name="A", formation_name="4-4-2"),
            TacticPreset(name="B", formation_name="4-3-3"),
        ]
        result = service.delete_preset("A", presets)
        assert len(result) == 1
        assert result[0].name == "B"

    def test_rename_preset(self, service, default_preset):
        """Can rename a preset."""
        service.rename_preset(default_preset, "New Name")
        assert default_preset.name == "New Name"

    def test_serialize_deserialize_presets(self, service):
        """Presets can be serialized and deserialized."""
        presets = [
            TacticPreset(
                name="Test",
                formation_name="4-3-3",
                mentality=TacticMentality.ATTACKING,
                pressing=PressingIntensity.HIGH,
                defensive_line=DefensiveLineHeight.HIGH,
                width=TeamWidth.WIDE,
                tempo=TeamTempo.FAST,
                player_assignments=[
                    PlayerPositionAssignment(
                        player_id=1, position_index=0, role="Goalkeeper"
                    )
                ],
            )
        ]
        data = service.serialize_presets(presets)
        restored = service.deserialize_presets(data)
        assert len(restored) == 1
        assert restored[0].name == "Test"
        assert restored[0].formation_name == "4-3-3"
        assert restored[0].mentality == TacticMentality.ATTACKING
        assert restored[0].pressing == PressingIntensity.HIGH
        assert restored[0].defensive_line == DefensiveLineHeight.HIGH
        assert restored[0].width == TeamWidth.WIDE
        assert restored[0].tempo == TeamTempo.FAST
        assert len(restored[0].player_assignments) == 1
        assert restored[0].player_assignments[0].player_id == 1


# ============================================================================
# Task 18.9: Tactic Application in Match Simulation
# ============================================================================


class TestMatchModifiers:
    """Tests for tactic match modifiers."""

    def test_balanced_modifiers_are_neutral(self, service, default_preset):
        """Balanced preset should produce neutral modifiers."""
        modifiers = service.get_tactic_match_modifiers(default_preset)
        assert modifiers.possession_bonus == 0.0
        assert modifiers.shot_frequency == 1.0
        assert modifiers.defensive_strength == 1.0
        assert modifiers.pressing_effectiveness == 1.0
        assert modifiers.stamina_drain_rate == 1.0
        assert modifiers.crossing_frequency == 1.0
        assert modifiers.passing_risk == 1.0

    def test_attacking_mentality_increases_shots(self, service):
        """Attacking mentality should increase shot frequency."""
        preset = TacticPreset(
            name="Attack", formation_name="4-3-3",
            mentality=TacticMentality.VERY_ATTACKING,
        )
        modifiers = service.get_tactic_match_modifiers(preset)
        assert modifiers.shot_frequency > 1.0
        assert modifiers.defensive_strength < 1.0

    def test_defensive_mentality_increases_defense(self, service):
        """Defensive mentality should increase defensive strength."""
        preset = TacticPreset(
            name="Defend", formation_name="5-4-1",
            mentality=TacticMentality.VERY_DEFENSIVE,
        )
        modifiers = service.get_tactic_match_modifiers(preset)
        assert modifiers.defensive_strength > 1.0
        assert modifiers.shot_frequency < 1.0
        assert modifiers.counter_attack_bonus > 0.0

    def test_extreme_pressing_drains_stamina(self, service):
        """Extreme pressing should increase stamina drain."""
        preset = TacticPreset(
            name="Press", formation_name="4-3-3",
            pressing=PressingIntensity.EXTREME,
        )
        modifiers = service.get_tactic_match_modifiers(preset)
        assert modifiers.stamina_drain_rate > 1.0
        assert modifiers.pressing_effectiveness > 1.0

    def test_low_pressing_saves_stamina(self, service):
        """Low pressing should reduce stamina drain."""
        preset = TacticPreset(
            name="Low", formation_name="4-4-2",
            pressing=PressingIntensity.LOW,
        )
        modifiers = service.get_tactic_match_modifiers(preset)
        assert modifiers.stamina_drain_rate < 1.0

    def test_high_line_increases_offside_trap(self, service):
        """Very high line should increase offside trap chance."""
        preset = TacticPreset(
            name="High", formation_name="4-3-3",
            defensive_line=DefensiveLineHeight.VERY_HIGH,
        )
        modifiers = service.get_tactic_match_modifiers(preset)
        assert modifiers.offside_trap_chance > 0.0
        assert modifiers.space_behind_defense > 0.0

    def test_wide_increases_crossing(self, service):
        """Wide width should increase crossing frequency."""
        preset = TacticPreset(
            name="Wide", formation_name="4-4-2",
            width=TeamWidth.WIDE,
        )
        modifiers = service.get_tactic_match_modifiers(preset)
        assert modifiers.crossing_frequency > 1.0

    def test_fast_tempo_increases_passing_risk(self, service):
        """Fast tempo should increase passing risk."""
        preset = TacticPreset(
            name="Fast", formation_name="4-3-3",
            tempo=TeamTempo.FAST,
        )
        modifiers = service.get_tactic_match_modifiers(preset)
        assert modifiers.passing_risk > 1.0

    def test_modifiers_serialization(self, service, default_preset):
        """Modifiers can be serialized to dict."""
        modifiers = service.get_tactic_match_modifiers(default_preset)
        data = modifiers.to_dict()
        assert "possession_bonus" in data
        assert "shot_frequency" in data
        assert "defensive_strength" in data


# ============================================================================
# Task 18.10: Visual Pitch Diagram Display
# ============================================================================


class TestPitchDiagram:
    """Tests for pitch diagram data generation."""

    def test_pitch_diagram_basic(self, service, default_preset):
        """Pitch diagram returns correct structure."""
        data = service.get_pitch_diagram_data(default_preset)
        assert data["formation_name"] == "4-4-2"
        assert len(data["positions"]) == 11
        assert data["pitch_bounds"] == {"width": 100, "height": 100}

    def test_pitch_diagram_positions_have_coordinates(self, service, default_preset):
        """Each position in diagram has x, y, and position_type."""
        data = service.get_pitch_diagram_data(default_preset)
        for pos in data["positions"]:
            assert "x" in pos
            assert "y" in pos
            assert "position_type" in pos
            assert "index" in pos

    def test_pitch_diagram_with_player_assignments(self, service, preset_with_players):
        """Diagram includes player assignment data."""
        data = service.get_pitch_diagram_data(preset_with_players)
        # Position 0 should have player_id=1
        pos_0 = data["positions"][0]
        assert pos_0["player_id"] == 1
        assert pos_0["role"] == "Goalkeeper"

    def test_pitch_diagram_custom_positions(self, service):
        """Custom positions override formation defaults."""
        preset = TacticPreset(name="Custom", formation_name="4-4-2")
        preset.player_assignments = [
            PlayerPositionAssignment(
                player_id=5, position_index=3, role="Central Defender",
                custom_x=55.0, custom_y=22.0,
            )
        ]
        data = service.get_pitch_diagram_data(preset)
        pos_3 = data["positions"][3]
        assert pos_3["x"] == 55.0
        assert pos_3["y"] == 22.0
        assert pos_3["player_id"] == 5

    def test_pitch_diagram_invalid_formation(self, service):
        """Returns empty data for invalid formation."""
        preset = TacticPreset(name="Bad", formation_name="invalid")
        data = service.get_pitch_diagram_data(preset)
        assert data["positions"] == []


# ============================================================================
# Task 18.11: Drag-and-Drop Player Positioning
# ============================================================================


class TestPlayerPositioning:
    """Tests for player positioning (drag-and-drop)."""

    def test_set_player_position(self, service, default_preset):
        """Can set a player to a position."""
        result = service.set_player_position(default_preset, player_id=5, position_index=3)
        assert result is True
        assert len(default_preset.player_assignments) == 1
        assert default_preset.player_assignments[0].player_id == 5
        assert default_preset.player_assignments[0].position_index == 3

    def test_set_player_with_custom_coords(self, service, default_preset):
        """Can set a player with custom coordinates."""
        result = service.set_player_position(
            default_preset, player_id=5, position_index=3, x=55.0, y=22.0
        )
        assert result is True
        assert default_preset.player_assignments[0].custom_x == 55.0
        assert default_preset.player_assignments[0].custom_y == 22.0

    def test_set_player_invalid_position_index(self, service, default_preset):
        """Cannot set player to invalid position index."""
        result = service.set_player_position(default_preset, player_id=5, position_index=99)
        assert result is False

    def test_set_player_invalid_coordinates(self, service, default_preset):
        """Cannot set player with out-of-bounds coordinates."""
        result = service.set_player_position(
            default_preset, player_id=5, position_index=3, x=150.0
        )
        assert result is False

    def test_move_player_position(self, service, preset_with_players):
        """Can move an existing player to new coordinates."""
        result = service.move_player_position(preset_with_players, player_id=1, new_x=45.0, new_y=8.0)
        assert result is True
        assignment = next(a for a in preset_with_players.player_assignments if a.player_id == 1)
        assert assignment.custom_x == 45.0
        assert assignment.custom_y == 8.0

    def test_move_nonexistent_player(self, service, default_preset):
        """Cannot move a player that isn't assigned."""
        result = service.move_player_position(default_preset, player_id=999, new_x=50.0, new_y=50.0)
        assert result is False

    def test_move_player_invalid_coords(self, service, preset_with_players):
        """Cannot move player to invalid coordinates."""
        result = service.move_player_position(preset_with_players, player_id=1, new_x=-5.0, new_y=50.0)
        assert result is False

    def test_reset_player_position(self, service, preset_with_players):
        """Can reset a player's custom position."""
        # First move the player
        service.move_player_position(preset_with_players, player_id=1, new_x=45.0, new_y=8.0)
        # Then reset
        result = service.reset_player_position(preset_with_players, player_id=1)
        assert result is True
        assignment = next(a for a in preset_with_players.player_assignments if a.player_id == 1)
        assert assignment.custom_x is None
        assert assignment.custom_y is None

    def test_set_player_replaces_existing(self, service, default_preset):
        """Setting a player to a position replaces any existing assignment."""
        service.set_player_position(default_preset, player_id=5, position_index=3)
        service.set_player_position(default_preset, player_id=6, position_index=3)
        # Only one assignment for position 3
        pos3_assignments = [
            a for a in default_preset.player_assignments if a.position_index == 3
        ]
        assert len(pos3_assignments) == 1
        assert pos3_assignments[0].player_id == 6


# ============================================================================
# Task 18.12: Position Compatibility Validation
# ============================================================================


class TestPositionCompatibility:
    """Tests for position compatibility validation."""

    def test_goalkeeper_natural(self, service):
        """GK player is compatible with GK position."""
        result = service.validate_position_compatibility("GK", PositionType.GK)
        assert result.is_compatible is True
        assert result.compatibility_score == 1.0

    def test_centre_back_natural(self, service):
        """D C player is compatible with CB position."""
        result = service.validate_position_compatibility("D C", PositionType.CB)
        assert result.is_compatible is True
        assert result.compatibility_score == 1.0

    def test_striker_natural(self, service):
        """ST C player is compatible with ST position."""
        result = service.validate_position_compatibility("ST C", PositionType.ST)
        assert result.is_compatible is True
        assert result.compatibility_score == 1.0

    def test_multi_position_player(self, service):
        """AM/ST RL player is compatible with LW."""
        result = service.validate_position_compatibility("AM/ST RL", PositionType.LW)
        assert result.is_compatible is True
        assert result.compatibility_score == 1.0

    def test_adjacent_position(self, service):
        """CM player can play DM with reduced effectiveness."""
        result = service.validate_position_compatibility("M C", PositionType.AM)
        assert result.is_compatible is True
        assert result.compatibility_score < 1.0
        assert result.compatibility_score > 0.0

    def test_incompatible_position(self, service):
        """GK cannot play ST."""
        result = service.validate_position_compatibility("GK", PositionType.ST)
        assert result.is_compatible is False
        assert result.compatibility_score == 0.0

    def test_left_back_to_left_wingback(self, service):
        """D L player is compatible with LWB."""
        result = service.validate_position_compatibility("D L", PositionType.LWB)
        assert result.is_compatible is True

    def test_midfielder_wide(self, service):
        """M RL player is compatible with LM and RM."""
        result_lm = service.validate_position_compatibility("M RL", PositionType.LM)
        result_rm = service.validate_position_compatibility("M RL", PositionType.RM)
        assert result_lm.is_compatible is True
        assert result_rm.is_compatible is True

    def test_compatibility_result_has_natural_positions(self, service):
        """Compatibility result includes natural positions list."""
        result = service.validate_position_compatibility("D C", PositionType.CB)
        assert len(result.natural_positions) > 0
        assert "CB" in result.natural_positions

    def test_empty_position_string(self, service):
        """Empty position string returns incompatible."""
        result = service.validate_position_compatibility("", PositionType.ST)
        assert result.is_compatible is False


# ============================================================================
# Task 18.13: In-Match Tactical Adjustments
# ============================================================================


class TestInMatchAdjustments:
    """Tests for in-match tactical adjustments."""

    def test_formation_change(self, service, default_preset):
        """Can change formation during match."""
        result = service.apply_in_match_adjustment(
            default_preset, "formation_change",
            {"new_formation": "4-3-3"}, minute=60,
        )
        assert result is not None
        assert default_preset.formation_name == "4-3-3"
        assert result.minute == 60

    def test_formation_change_invalid(self, service, default_preset):
        """Invalid formation change returns None."""
        result = service.apply_in_match_adjustment(
            default_preset, "formation_change",
            {"new_formation": "9-9-9"}, minute=60,
        )
        assert result is None
        assert default_preset.formation_name == "4-4-2"  # Unchanged

    def test_mentality_shift(self, service, default_preset):
        """Can shift mentality during match."""
        result = service.apply_in_match_adjustment(
            default_preset, "mentality_shift",
            {"new_mentality": "Attacking"}, minute=70,
        )
        assert result is not None
        assert default_preset.mentality == TacticMentality.ATTACKING

    def test_mentality_shift_invalid(self, service, default_preset):
        """Invalid mentality shift returns None."""
        result = service.apply_in_match_adjustment(
            default_preset, "mentality_shift",
            {"new_mentality": "Super Attacking"}, minute=70,
        )
        assert result is None

    def test_pressing_change(self, service, default_preset):
        """Can change pressing during match."""
        result = service.apply_in_match_adjustment(
            default_preset, "pressing_change",
            {"new_pressing": "Extreme"}, minute=55,
        )
        assert result is not None
        assert default_preset.pressing == PressingIntensity.EXTREME

    def test_defensive_line_change(self, service, default_preset):
        """Can change defensive line during match."""
        result = service.apply_in_match_adjustment(
            default_preset, "defensive_line_change",
            {"new_line": "Deep"}, minute=80,
        )
        assert result is not None
        assert default_preset.defensive_line == DefensiveLineHeight.DEEP

    def test_width_change(self, service, default_preset):
        """Can change width during match."""
        result = service.apply_in_match_adjustment(
            default_preset, "width_change",
            {"new_width": "Wide"}, minute=45,
        )
        assert result is not None
        assert default_preset.width == TeamWidth.WIDE

    def test_tempo_change(self, service, default_preset):
        """Can change tempo during match."""
        result = service.apply_in_match_adjustment(
            default_preset, "tempo_change",
            {"new_tempo": "Fast"}, minute=30,
        )
        assert result is not None
        assert default_preset.tempo == TeamTempo.FAST

    def test_substitution(self, service, preset_with_players):
        """Can make a substitution during match."""
        result = service.apply_in_match_adjustment(
            preset_with_players, "substitution",
            {"player_out_id": 10, "player_in_id": 20, "role": "Complete Forward"},
            minute=65,
        )
        assert result is not None
        # Player 10 should be replaced by player 20
        player_ids = [a.player_id for a in preset_with_players.player_assignments]
        assert 20 in player_ids
        assert 10 not in player_ids

    def test_substitution_missing_params(self, service, preset_with_players):
        """Substitution without required params returns None."""
        result = service.apply_in_match_adjustment(
            preset_with_players, "substitution",
            {"player_out_id": 10}, minute=65,
        )
        assert result is None

    def test_unknown_adjustment_type(self, service, default_preset):
        """Unknown adjustment type returns None."""
        result = service.apply_in_match_adjustment(
            default_preset, "unknown_type", {}, minute=50,
        )
        assert result is None

    def test_formation_change_clears_custom_positions(self, service):
        """Formation change should clear custom positions."""
        preset = TacticPreset(name="Test", formation_name="4-4-2")
        preset.player_assignments = [
            PlayerPositionAssignment(
                player_id=5, position_index=3, role="Central Defender",
                custom_x=55.0, custom_y=22.0,
            )
        ]
        service.apply_in_match_adjustment(
            preset, "formation_change", {"new_formation": "4-3-3"}, minute=60,
        )
        assert preset.player_assignments[0].custom_x is None
        assert preset.player_assignments[0].custom_y is None

    def test_get_available_adjustments(self, service):
        """Returns list of available adjustment types."""
        adjustments = service.get_available_adjustments()
        assert "formation_change" in adjustments
        assert "mentality_shift" in adjustments
        assert "substitution" in adjustments
        assert len(adjustments) == 7
