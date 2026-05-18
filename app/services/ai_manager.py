"""
AI Manager Module - Manages opponent teams in matches and competitions

This module implements the AI_Manager class which controls all non-player clubs
in the game, making decisions about tactics, squad selection, substitutions,
and transfers.

Based on requirements:
- Requirement 6.7: AI_Manager generates transfer bids for listed players
- Requirement 14.3: AI_Manager simulates all non-player-managed matches
- Requirement 19: AI_Manager manages opponent teams with tactical decisions

Design principles:
- Difficulty scaling based on club reputation
- Realistic decision-making based on club resources and player attributes
- Consistent club identity across seasons
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import random


class WeatherCondition(Enum):
    """Weather conditions affecting match tactics"""
    CLEAR = "clear"
    RAINY = "rainy"
    SNOWY = "snowy"
    FOGGY = "foggy"
    WINDY = "windy"


class AIPersonality(Enum):
    """AI manager personality types affecting tactical decisions"""
    DEFENSIVE = "defensive"
    BALANCED = "balanced"
    ATTACKING = "attacking"
    PRAGMATIC = "pragmatic"  # Adapts based on opponent strength
    POSSESSION = "possession"  # Focus on ball retention


class TacticMentality(Enum):
    """Team mentality levels"""
    DEFENSIVE = "Defensive"
    CAUTIOUS = "Cautious"
    BALANCED = "Balanced"
    POSITIVE = "Positive"
    ATTACKING = "Attacking"
    VERY_ATTACKING = "Very Attacking"


class PressingIntensity(Enum):
    """Pressing intensity levels"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    GEGENPRESSING = "Gegenpressing"


class DefensiveLine(Enum):
    """Defensive line height"""
    DEEP = "Deep"
    STANDARD = "Standard"
    HIGH = "High"
    VERY_HIGH = "Very High"


class Width(Enum):
    """Team width setting"""
    NARROW = "Narrow"
    STANDARD = "Standard"
    WIDE = "Wide"


class Tempo(Enum):
    """Team tempo setting"""
    SLOW = "Slow"
    STANDARD = "Standard"
    FAST = "Fast"


@dataclass
class TacticPreset:
    """Complete tactical setup for a team"""
    formation: str
    mentality: TacticMentality
    pressing: PressingIntensity
    defensive_line: DefensiveLine
    width: Width
    tempo: Tempo
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "formation": self.formation,
            "mentality": self.mentality.value,
            "pressing": self.pressing.value,
            "defensive_line": self.defensive_line.value,
            "width": self.width.value,
            "tempo": self.tempo.value,
        }


@dataclass
class ClubProfile:
    """Profile of a club for AI decision-making"""
    club_id: int
    reputation: int  # 1-100
    transfer_budget: int
    wage_budget: int
    balance: int
    squad_average_ca: float
    squad_size: int
    league_position: Optional[int] = None
    recent_form: Optional[List[str]] = None  # ["W", "L", "D", "W", "W"]
    injured_key_players: int = 0  # Number of key players injured
    squad_fitness: float = 100.0  # Average squad fitness (0-100)


@dataclass
class HeadToHeadRecord:
    """Head-to-head record between two clubs"""
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    
    def get_confidence_factor(self) -> float:
        """
        Calculate confidence factor from head-to-head record.
        
        Returns:
            float: Confidence factor (-1.0 to +1.0)
        """
        if self.wins + self.draws + self.losses == 0:
            return 0.0
        
        total_matches = self.wins + self.draws + self.losses
        win_rate = self.wins / total_matches
        
        # Convert to -1 to +1 scale
        return (win_rate - 0.5) * 2


class AIManager:
    """
    AI Manager class for controlling opponent teams.
    
    Responsibilities:
    - Select match tactics based on opponent strength and club profile
    - Make substitution decisions during matches
    - Generate transfer bids based on club needs and budget
    - Manage squad rotation and player development
    - Adapt difficulty based on player-manager's progression
    
    The AI uses a personality-based system where each club has a consistent
    playing style and decision-making approach across seasons.
    """
    
    # Standard formations available to AI
    FORMATIONS = [
        "4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2",
        "4-5-1", "3-4-3", "4-1-4-1", "4-3-2-1", "5-4-1",
        "3-6-1", "4-4-1-1", "4-2-2-2", "3-4-1-2", "4-3-1-2"
    ]
    
    # Formation preferences by personality
    FORMATION_PREFERENCES = {
        AIPersonality.DEFENSIVE: ["5-3-2", "5-4-1", "4-5-1", "4-4-2"],
        AIPersonality.BALANCED: ["4-4-2", "4-2-3-1", "4-3-3", "4-3-2-1"],
        AIPersonality.ATTACKING: ["4-3-3", "3-4-3", "4-2-3-1", "3-5-2"],
        AIPersonality.PRAGMATIC: ["4-4-2", "4-2-3-1", "4-3-3", "5-3-2"],
        AIPersonality.POSSESSION: ["4-3-3", "4-2-3-1", "3-4-3", "4-1-4-1"],
    }
    
    def __init__(self, difficulty_multiplier: float = 1.0):
        """
        Initialize AI Manager.
        
        Args:
            difficulty_multiplier: Multiplier for AI decision quality (0.5-2.0)
                                  Higher values make AI more challenging
        """
        self.difficulty_multiplier = max(0.5, min(2.0, difficulty_multiplier))
        self._club_personalities: Dict[int, AIPersonality] = {}
    
    # ========================================================================
    # DIFFICULTY SCALING (Task 5.8)
    # ========================================================================
    
    @staticmethod
    def calculate_difficulty_from_reputation(
        player_club_reputation: int,
        ai_club_reputation: int,
        season_number: int = 1,
        player_league_position: Optional[int] = None,
        player_trophies_won: int = 0,
    ) -> float:
        """
        Calculate AI difficulty multiplier based on the player-manager's club reputation.
        
        The difficulty scales so that:
        - When the player manages a top club (rep 80+), AI opponents are tougher (1.2-1.8)
        - When the player manages a mid club (rep 40-79), AI is moderate (0.9-1.3)
        - When the player manages a low club (rep <40), AI is easier (0.6-1.0)
        
        Additional scaling factors:
        - Season progression: difficulty increases slightly each season
        - League position: if player is overperforming, AI adapts
        - Trophies: winning trophies increases future difficulty
        - AI club reputation relative to player: stronger AI clubs are harder
        
        Args:
            player_club_reputation: Player-manager's club reputation (1-100)
            ai_club_reputation: AI-controlled club's reputation (1-100)
            season_number: Current season number (1+)
            player_league_position: Player's current league position (1-20, lower = better)
            player_trophies_won: Total trophies won by player-manager
        
        Returns:
            float: Difficulty multiplier (0.5-2.0)
        """
        # Base difficulty from player's club reputation
        # Higher reputation = player chose a stronger club = AI should be harder
        if player_club_reputation >= 80:
            base_difficulty = 1.3
        elif player_club_reputation >= 65:
            base_difficulty = 1.1
        elif player_club_reputation >= 50:
            base_difficulty = 1.0
        elif player_club_reputation >= 35:
            base_difficulty = 0.85
        else:
            base_difficulty = 0.7
        
        # AI club reputation factor
        # Stronger AI clubs should be harder regardless of player's club
        reputation_ratio = ai_club_reputation / max(1, player_club_reputation)
        
        if reputation_ratio >= 1.5:
            # AI club much stronger than player's club
            base_difficulty += 0.2
        elif reputation_ratio >= 1.2:
            # AI club somewhat stronger
            base_difficulty += 0.1
        elif reputation_ratio <= 0.5:
            # AI club much weaker
            base_difficulty -= 0.15
        elif reputation_ratio <= 0.7:
            # AI club somewhat weaker
            base_difficulty -= 0.08
        
        # Season progression factor (difficulty increases over time)
        # +0.03 per season, capped at +0.3 (10 seasons)
        season_bonus = min(0.3, (season_number - 1) * 0.03)
        base_difficulty += season_bonus
        
        # Overperformance factor
        # If player is doing better than expected, AI adapts
        if player_league_position is not None:
            # Expected position based on reputation (rough estimate)
            expected_position = max(1, 21 - int(player_club_reputation / 5))
            
            overperformance = expected_position - player_league_position
            
            if overperformance >= 5:
                # Significantly overperforming - AI gets harder
                base_difficulty += 0.15
            elif overperformance >= 3:
                # Moderately overperforming
                base_difficulty += 0.08
            elif overperformance <= -5:
                # Significantly underperforming - AI eases slightly
                base_difficulty -= 0.08
        
        # Trophy factor (winning makes future seasons harder)
        if player_trophies_won >= 5:
            base_difficulty += 0.15
        elif player_trophies_won >= 3:
            base_difficulty += 0.10
        elif player_trophies_won >= 1:
            base_difficulty += 0.05
        
        # Clamp to valid range
        return max(0.5, min(2.0, base_difficulty))
    
    def update_difficulty(
        self,
        player_club_reputation: int,
        ai_club_reputation: int,
        season_number: int = 1,
        player_league_position: Optional[int] = None,
        player_trophies_won: int = 0,
    ) -> float:
        """
        Update the AI difficulty multiplier based on current game state.
        
        Should be called at the start of each match or season to adjust
        AI difficulty dynamically.
        
        Args:
            player_club_reputation: Player-manager's club reputation (1-100)
            ai_club_reputation: AI-controlled club's reputation (1-100)
            season_number: Current season number (1+)
            player_league_position: Player's current league position (1-20)
            player_trophies_won: Total trophies won by player-manager
        
        Returns:
            float: Updated difficulty multiplier
        """
        self.difficulty_multiplier = self.calculate_difficulty_from_reputation(
            player_club_reputation=player_club_reputation,
            ai_club_reputation=ai_club_reputation,
            season_number=season_number,
            player_league_position=player_league_position,
            player_trophies_won=player_trophies_won,
        )
        return self.difficulty_multiplier
    
    def get_match_difficulty(
        self,
        player_club_reputation: int,
        ai_club_reputation: int,
        match_importance: int = 5,
        is_cup_final: bool = False,
        is_derby: bool = False,
        season_number: int = 1,
        player_league_position: Optional[int] = None,
        player_trophies_won: int = 0,
    ) -> float:
        """
        Get difficulty multiplier for a specific match context.
        
        Adds match-specific modifiers on top of the base difficulty:
        - Cup finals and important matches are harder
        - Derbies have extra intensity
        - AI clubs "raise their game" for big matches
        
        Args:
            player_club_reputation: Player-manager's club reputation (1-100)
            ai_club_reputation: AI-controlled club's reputation (1-100)
            match_importance: Match importance (1-10)
            is_cup_final: Whether this is a cup final
            is_derby: Whether this is a local derby
            season_number: Current season number
            player_league_position: Player's league position
            player_trophies_won: Total trophies won
        
        Returns:
            float: Match-specific difficulty multiplier (0.5-2.0)
        """
        base = self.calculate_difficulty_from_reputation(
            player_club_reputation=player_club_reputation,
            ai_club_reputation=ai_club_reputation,
            season_number=season_number,
            player_league_position=player_league_position,
            player_trophies_won=player_trophies_won,
        )
        
        # Match importance modifier
        if match_importance >= 9:
            base += 0.15  # Very important match - AI raises game
        elif match_importance >= 7:
            base += 0.08  # Important match
        elif match_importance <= 3:
            base -= 0.05  # Less important - AI may not try as hard
        
        # Cup final modifier
        if is_cup_final:
            base += 0.12  # Cup finals are always intense
        
        # Derby modifier
        if is_derby:
            base += 0.08  # Derbies have extra intensity
        
        return max(0.5, min(2.0, base))
    
    def get_club_personality(self, club_id: int, club_reputation: int) -> AIPersonality:
        """
        Get or assign a consistent personality to a club.
        
        Personality is determined by club reputation and cached for consistency.
        
        Args:
            club_id: Club ID
            club_reputation: Club reputation (1-100)
        
        Returns:
            AIPersonality: The club's playing style personality
        """
        if club_id not in self._club_personalities:
            # Assign personality based on reputation with some randomness
            random.seed(club_id)  # Consistent randomness per club
            
            if club_reputation >= 80:
                # Top clubs: more likely to be attacking or possession-based
                personalities = [
                    AIPersonality.ATTACKING,
                    AIPersonality.POSSESSION,
                    AIPersonality.BALANCED,
                ]
                weights = [0.4, 0.4, 0.2]
            elif club_reputation >= 60:
                # Mid-high clubs: balanced mix
                personalities = [
                    AIPersonality.BALANCED,
                    AIPersonality.ATTACKING,
                    AIPersonality.PRAGMATIC,
                ]
                weights = [0.4, 0.3, 0.3]
            elif club_reputation >= 40:
                # Mid-low clubs: more pragmatic
                personalities = [
                    AIPersonality.PRAGMATIC,
                    AIPersonality.BALANCED,
                    AIPersonality.DEFENSIVE,
                ]
                weights = [0.5, 0.3, 0.2]
            else:
                # Low clubs: defensive or pragmatic
                personalities = [
                    AIPersonality.DEFENSIVE,
                    AIPersonality.PRAGMATIC,
                    AIPersonality.BALANCED,
                ]
                weights = [0.5, 0.3, 0.2]
            
            self._club_personalities[club_id] = random.choices(
                personalities, weights=weights
            )[0]
            
            random.seed()  # Reset random seed
        
        return self._club_personalities[club_id]
    
    def select_match_tactics(
        self,
        club_profile: ClubProfile,
        opponent_profile: ClubProfile,
        is_home: bool = True,
        competition_importance: int = 5,  # 1-10 scale
        weather: WeatherCondition = WeatherCondition.CLEAR,
        head_to_head: Optional[HeadToHeadRecord] = None,
        opponent_likely_formation: Optional[str] = None,
    ) -> TacticPreset:
        """
        Select tactics for a match based on club profile and opponent.
        
        Enhanced decision factors:
        - Club personality (consistent playing style)
        - Opponent strength analysis (CA, reputation, form)
        - Home/away status with crowd pressure
        - Competition importance (affects risk-taking)
        - Recent form and momentum
        - Squad quality and depth considerations
        - Weather conditions (affects playing style)
        - Head-to-head history (psychological factor)
        - Player availability and fitness
        - Tactical counters to opponent's style
        - Difficulty multiplier for AI challenge
        
        Args:
            club_profile: Profile of the AI-controlled club
            opponent_profile: Profile of the opponent club
            is_home: Whether playing at home
            competition_importance: Importance of the competition (1-10)
            weather: Weather conditions for the match
            head_to_head: Historical record against opponent
            opponent_likely_formation: Opponent's likely formation for tactical counter
        
        Returns:
            TacticPreset: Complete tactical setup for the match
        """
        personality = self.get_club_personality(
            club_profile.club_id,
            club_profile.reputation
        )
        
        # Enhanced strength analysis
        strength_diff = club_profile.squad_average_ca - opponent_profile.squad_average_ca
        reputation_diff = club_profile.reputation - opponent_profile.reputation
        
        # Analyze opponent form for tactical adjustment
        opponent_form_factor = self._analyze_form(opponent_profile.recent_form)
        own_form_factor = self._analyze_form(club_profile.recent_form)
        
        # Analyze head-to-head psychological factor
        h2h_confidence = 0.0
        if head_to_head:
            h2h_confidence = head_to_head.get_confidence_factor()
        
        # Analyze player availability impact
        availability_factor = self._analyze_availability(
            club_profile.injured_key_players,
            club_profile.squad_fitness
        )
        
        # Determine base mentality based on comprehensive analysis
        mentality = self._select_mentality(
            personality=personality,
            strength_diff=strength_diff,
            reputation_diff=reputation_diff,
            is_home=is_home,
            recent_form=club_profile.recent_form,
            competition_importance=competition_importance,
            opponent_form_factor=opponent_form_factor,
            own_form_factor=own_form_factor,
            h2h_confidence=h2h_confidence,
            availability_factor=availability_factor,
            weather=weather,
        )
        
        # Select formation based on personality and tactical needs
        formation = self._select_formation(
            personality=personality,
            mentality=mentality,
            opponent_strength=opponent_profile.squad_average_ca,
            own_strength=club_profile.squad_average_ca,
            competition_importance=competition_importance,
            opponent_formation=opponent_likely_formation,
            weather=weather,
        )
        
        # Determine pressing intensity based on squad quality
        pressing = self._select_pressing(
            personality=personality,
            mentality=mentality,
            squad_average_ca=club_profile.squad_average_ca,
            opponent_strength=opponent_profile.squad_average_ca,
            squad_fitness=club_profile.squad_fitness,
            weather=weather,
        )
        
        # Determine defensive line
        defensive_line = self._select_defensive_line(
            mentality=mentality,
            pressing=pressing,
            opponent_strength=opponent_profile.squad_average_ca,
        )
        
        # Determine width based on formation and opponent
        width = self._select_width(
            formation=formation,
            mentality=mentality,
            opponent_formation=opponent_likely_formation or self._estimate_opponent_formation(opponent_profile),
            weather=weather,
        )
        
        # Determine tempo based on tactical approach
        tempo = self._select_tempo(
            personality=personality,
            mentality=mentality,
            squad_average_ca=club_profile.squad_average_ca,
            pressing=pressing,
            weather=weather,
        )
        
        return TacticPreset(
            formation=formation,
            mentality=mentality,
            pressing=pressing,
            defensive_line=defensive_line,
            width=width,
            tempo=tempo,
        )
    
    def _analyze_form(self, recent_form: Optional[List[str]]) -> float:
        """
        Analyze recent form and return a form factor.
        
        Args:
            recent_form: Recent match results (["W", "L", "D", ...])
        
        Returns:
            float: Form factor (-1.0 to +1.0, where negative = poor form, positive = good form)
        """
        if not recent_form or len(recent_form) == 0:
            return 0.0
        
        # Consider last 5 matches
        recent = recent_form[-5:]
        wins = recent.count("W")
        draws = recent.count("D")
        losses = recent.count("L")
        
        # Calculate form score
        form_score = (wins * 3 + draws * 1) / (len(recent) * 3)  # Normalize to 0-1
        
        # Convert to -1 to +1 scale
        return (form_score - 0.5) * 2
    
    def _analyze_availability(
        self,
        injured_key_players: int,
        squad_fitness: float,
    ) -> float:
        """
        Analyze player availability and fitness impact on tactics.
        
        Args:
            injured_key_players: Number of key players injured
            squad_fitness: Average squad fitness (0-100)
        
        Returns:
            float: Availability factor (-1.0 to +1.0, negative = weakened squad)
        """
        availability_score = 0.0
        
        # Injury impact (each key player injury reduces confidence)
        if injured_key_players > 0:
            availability_score -= injured_key_players * 0.2
        
        # Fitness impact
        if squad_fitness < 70:
            availability_score -= (70 - squad_fitness) / 100
        elif squad_fitness > 90:
            availability_score += (squad_fitness - 90) / 100
        
        return max(-1.0, min(1.0, availability_score))
    
    def _select_mentality(
        self,
        personality: AIPersonality,
        strength_diff: float,
        reputation_diff: int,
        is_home: bool,
        recent_form: Optional[List[str]] = None,
        competition_importance: int = 5,
        opponent_form_factor: float = 0.0,
        own_form_factor: float = 0.0,
        h2h_confidence: float = 0.0,
        availability_factor: float = 0.0,
        weather: WeatherCondition = WeatherCondition.CLEAR,
    ) -> TacticMentality:
        """
        Select team mentality based on comprehensive analysis.
        
        Enhanced to consider:
        - Competition importance (affects risk-taking)
        - Opponent's recent form
        - Own team's momentum
        - Head-to-head psychological factor
        - Player availability and fitness
        - Weather conditions
        
        Args:
            personality: Club's AI personality
            strength_diff: Difference in squad CA (positive = stronger)
            reputation_diff: Difference in reputation (positive = better reputation)
            is_home: Whether playing at home
            recent_form: Recent match results (["W", "L", "D", ...])
            competition_importance: Importance of competition (1-10)
            opponent_form_factor: Opponent's form factor (-1 to +1)
            own_form_factor: Own team's form factor (-1 to +1)
            h2h_confidence: Head-to-head confidence factor (-1 to +1)
            availability_factor: Player availability factor (-1 to +1)
            weather: Weather conditions
        
        Returns:
            TacticMentality: Selected mentality
        """
        # Base mentality score (-3 to +3, where negative = defensive, positive = attacking)
        mentality_score = 0.0
        
        # Personality influence (strongest factor)
        if personality == AIPersonality.DEFENSIVE:
            mentality_score -= 2.0
        elif personality == AIPersonality.ATTACKING:
            mentality_score += 2.0
        elif personality == AIPersonality.POSSESSION:
            mentality_score += 0.5
        elif personality == AIPersonality.PRAGMATIC:
            # Pragmatic adapts based on opponent
            if strength_diff > 20:
                mentality_score += 1.5
            elif strength_diff < -20:
                mentality_score -= 1.5
        
        # Strength difference influence
        if strength_diff > 30:
            mentality_score += 1.5
        elif strength_diff > 15:
            mentality_score += 0.5
        elif strength_diff < -30:
            mentality_score -= 1.5
        elif strength_diff < -15:
            mentality_score -= 0.5
        
        # Reputation difference (affects confidence)
        if reputation_diff > 30:
            mentality_score += 0.3
        elif reputation_diff < -30:
            mentality_score -= 0.3
        
        # Home advantage with crowd pressure
        if is_home:
            mentality_score += 0.5
            # Extra pressure at home for big clubs
            if reputation_diff > 20:
                mentality_score += 0.2
        else:
            mentality_score -= 0.3
        
        # Recent form influence (momentum)
        if recent_form and len(recent_form) >= 3:
            wins = recent_form[-5:].count("W")
            losses = recent_form[-5:].count("L")
            if wins >= 4:
                mentality_score += 0.5  # Confidence boost
            elif losses >= 4:
                mentality_score -= 0.5  # More cautious
        
        # Form factor influence
        mentality_score += own_form_factor * 0.4  # Own form affects confidence
        mentality_score -= opponent_form_factor * 0.2  # Opponent's good form makes us cautious
        
        # Head-to-head psychological factor
        mentality_score += h2h_confidence * 0.3  # Historical dominance boosts confidence
        
        # Player availability impact
        mentality_score += availability_factor * 0.4  # Injuries/fatigue make us more cautious
        
        # Competition importance (higher importance = more cautious unless much stronger)
        if competition_importance >= 8:
            # Very important match - more cautious unless clearly stronger
            if strength_diff < 20:
                mentality_score -= 0.4
        elif competition_importance <= 3:
            # Less important match - can take more risks
            mentality_score += 0.3
        
        # Weather impact on mentality
        if weather == WeatherCondition.RAINY:
            # Rain makes attacking play harder
            mentality_score -= 0.2
        elif weather == WeatherCondition.SNOWY:
            # Snow significantly reduces attacking intent
            mentality_score -= 0.4
        elif weather == WeatherCondition.FOGGY:
            # Fog makes teams more cautious
            mentality_score -= 0.3
        
        # Difficulty multiplier
        mentality_score *= self.difficulty_multiplier
        
        # Map score to mentality
        if mentality_score <= -2.0:
            return TacticMentality.DEFENSIVE
        elif mentality_score <= -0.5:
            return TacticMentality.CAUTIOUS
        elif mentality_score <= 0.5:
            return TacticMentality.BALANCED
        elif mentality_score <= 1.5:
            return TacticMentality.POSITIVE
        elif mentality_score <= 2.5:
            return TacticMentality.ATTACKING
        else:
            return TacticMentality.VERY_ATTACKING
    
    def _select_formation(
        self,
        personality: AIPersonality,
        mentality: TacticMentality,
        opponent_strength: float,
        own_strength: float,
        competition_importance: int = 5,
        opponent_formation: Optional[str] = None,
        weather: WeatherCondition = WeatherCondition.CLEAR,
    ) -> str:
        """
        Select formation based on personality, mentality, and tactical needs.
        
        Enhanced to consider:
        - Squad quality relative to opponent
        - Competition importance (affects risk-taking)
        - Mentality-formation synergy
        - Tactical counters to opponent's formation
        - Weather conditions
        
        Args:
            personality: Club's AI personality
            mentality: Selected mentality
            opponent_strength: Opponent's average CA
            own_strength: Own team's average CA
            competition_importance: Importance of competition (1-10)
            opponent_formation: Opponent's likely formation for tactical counter
            weather: Weather conditions
        
        Returns:
            str: Formation string (e.g., "4-4-2")
        """
        # Get preferred formations for personality
        preferred = self.FORMATION_PREFERENCES.get(
            personality,
            ["4-4-2", "4-3-3", "4-2-3-1"]
        )
        
        # Tactical counter to opponent's formation
        if opponent_formation:
            counter_formation = self._get_counter_formation(opponent_formation)
            if counter_formation and counter_formation in self.FORMATIONS:
                # 40% chance to use counter formation if it's in preferred list
                if counter_formation in preferred and random.random() < 0.4:
                    return counter_formation
                # 20% chance to use counter formation even if not preferred
                elif random.random() < 0.2:
                    return counter_formation
        
        # Adjust based on mentality
        if mentality in [TacticMentality.DEFENSIVE, TacticMentality.CAUTIOUS]:
            # Prefer defensive formations
            defensive_formations = ["5-3-2", "5-4-1", "4-5-1", "4-4-2"]
            preferred = [f for f in preferred if f in defensive_formations] or defensive_formations
        elif mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
            # Prefer attacking formations
            attacking_formations = ["4-3-3", "3-4-3", "4-2-3-1", "3-5-2"]
            preferred = [f for f in preferred if f in attacking_formations] or attacking_formations
        
        # Weather impact on formation choice
        if weather in [WeatherCondition.RAINY, WeatherCondition.SNOWY]:
            # Bad weather favors more compact formations
            compact_formations = ["4-4-2", "4-5-1", "5-4-1", "4-2-3-1"]
            # Increase preference for compact formations
            preferred = [f for f in preferred if f in compact_formations] or preferred
        
        # Consider strength difference for formation choice
        strength_diff = own_strength - opponent_strength
        
        if strength_diff < -25 and competition_importance >= 7:
            # Much weaker in important match - ultra defensive
            if "5-4-1" in preferred:
                return "5-4-1"
            elif "5-3-2" in preferred:
                return "5-3-2"
        elif strength_diff > 25 and mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
            # Much stronger and attacking - go for goals
            if "4-3-3" in preferred:
                return "4-3-3"
            elif "3-4-3" in preferred:
                return "3-4-3"
        
        # Select from preferred formations
        return random.choice(preferred[:3])  # Top 3 preferences
    
    def _get_counter_formation(self, opponent_formation: str) -> Optional[str]:
        """
        Get a tactical counter formation to opponent's setup.
        
        Tactical counters:
        - Against 3 at the back: use wingers (4-3-3, 4-2-3-1)
        - Against 4-4-2: use midfield overload (4-3-3, 4-5-1)
        - Against 4-3-3: match with 4-3-3 or use 4-2-3-1
        - Against narrow formations: use width (4-3-3, 4-4-2)
        
        Args:
            opponent_formation: Opponent's formation
        
        Returns:
            Optional[str]: Counter formation or None
        """
        if not opponent_formation:
            return None
        
        # Against 3 at the back - exploit flanks
        if opponent_formation.startswith("3-"):
            return random.choice(["4-3-3", "4-2-3-1", "4-4-2"])
        
        # Against 5 at the back - need attacking width
        elif opponent_formation.startswith("5-"):
            return random.choice(["4-3-3", "3-4-3"])
        
        # Against 4-4-2 - midfield overload
        elif opponent_formation == "4-4-2":
            return random.choice(["4-3-3", "4-5-1", "4-2-3-1"])
        
        # Against 4-3-3 - match or counter with defensive midfield
        elif opponent_formation == "4-3-3":
            return random.choice(["4-3-3", "4-2-3-1", "4-5-1"])
        
        # Against narrow formations (4-1-4-1, 4-3-2-1) - use width
        elif opponent_formation in ["4-1-4-1", "4-3-2-1", "3-6-1"]:
            return random.choice(["4-3-3", "4-4-2", "3-5-2"])
        
        # Against 4-2-3-1 - match or use 4-3-3
        elif opponent_formation == "4-2-3-1":
            return random.choice(["4-2-3-1", "4-3-3", "4-4-2"])
        
        return None
    
    def _select_pressing(
        self,
        personality: AIPersonality,
        mentality: TacticMentality,
        squad_average_ca: float,
        opponent_strength: float,
        squad_fitness: float = 100.0,
        weather: WeatherCondition = WeatherCondition.CLEAR,
    ) -> PressingIntensity:
        """
        Select pressing intensity based on squad quality and tactical approach.
        
        Enhanced to consider:
        - Opponent strength (press weaker opponents more)
        - Squad fitness requirements
        - Weather conditions (affects stamina)
        
        Args:
            personality: Club's AI personality
            mentality: Selected mentality
            squad_average_ca: Squad's average CA
            opponent_strength: Opponent's average CA
            squad_fitness: Average squad fitness (0-100)
            weather: Weather conditions
        
        Returns:
            PressingIntensity: Selected pressing intensity
        """
        strength_diff = squad_average_ca - opponent_strength
        
        # Reduce pressing if squad fitness is low
        fitness_penalty = 0
        if squad_fitness < 70:
            fitness_penalty = 1  # Reduce pressing level
        elif squad_fitness < 85:
            fitness_penalty = 0.5  # Slightly reduce pressing
        
        # Weather impact on pressing
        weather_penalty = 0
        if weather in [WeatherCondition.RAINY, WeatherCondition.SNOWY]:
            weather_penalty = 0.5  # Harder to press in bad weather
        elif weather == WeatherCondition.WINDY:
            weather_penalty = 0.3  # Slightly harder
        
        # High CA teams can press more effectively
        if squad_average_ca >= 140:
            if mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
                # More likely to gegenpress if much stronger and fit
                if strength_diff > 20 and fitness_penalty == 0 and weather_penalty == 0:
                    return PressingIntensity.GEGENPRESSING if random.random() < 0.5 else PressingIntensity.HIGH
                # Reduce pressing based on fitness and weather
                if fitness_penalty > 0 or weather_penalty > 0:
                    return PressingIntensity.HIGH if random.random() < 0.5 else PressingIntensity.MEDIUM
                return PressingIntensity.GEGENPRESSING if random.random() < 0.3 else PressingIntensity.HIGH
            elif mentality == TacticMentality.POSITIVE:
                if fitness_penalty > 0 or weather_penalty > 0:
                    return PressingIntensity.MEDIUM
                return PressingIntensity.HIGH
            elif mentality == TacticMentality.BALANCED:
                return PressingIntensity.MEDIUM
            else:
                return PressingIntensity.LOW
        elif squad_average_ca >= 120:
            if mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
                # Press more against weaker opponents if fit
                if strength_diff > 15 and fitness_penalty == 0:
                    return PressingIntensity.HIGH
                # Reduce pressing based on fitness and weather
                if fitness_penalty > 0 or weather_penalty > 0:
                    return PressingIntensity.MEDIUM if random.random() < 0.6 else PressingIntensity.LOW
                return PressingIntensity.HIGH if random.random() < 0.7 else PressingIntensity.MEDIUM
            elif mentality in [TacticMentality.POSITIVE, TacticMentality.BALANCED]:
                if fitness_penalty > 0 or weather_penalty > 0:
                    return PressingIntensity.LOW
                return PressingIntensity.MEDIUM
            else:
                return PressingIntensity.LOW
        else:
            # Lower CA teams: less pressing to conserve energy
            if mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
                # Only press if significantly stronger and fit
                if strength_diff > 20 and fitness_penalty == 0 and weather_penalty == 0:
                    return PressingIntensity.MEDIUM
                return PressingIntensity.MEDIUM if random.random() < 0.5 else PressingIntensity.LOW
            else:
                return PressingIntensity.LOW
    
    def _select_defensive_line(
        self,
        mentality: TacticMentality,
        pressing: PressingIntensity,
        opponent_strength: float,
    ) -> DefensiveLine:
        """
        Select defensive line height based on mentality, pressing, and opponent.
        
        Enhanced to consider opponent strength (higher line against weaker opponents).
        
        Args:
            mentality: Selected mentality
            pressing: Selected pressing intensity
            opponent_strength: Opponent's average CA
        
        Returns:
            DefensiveLine: Selected defensive line height
        """
        # High pressing requires high line
        if pressing == PressingIntensity.GEGENPRESSING:
            return DefensiveLine.VERY_HIGH
        elif pressing == PressingIntensity.HIGH:
            # Consider opponent strength for high line
            if opponent_strength < 120:
                return DefensiveLine.HIGH
            return DefensiveLine.HIGH if random.random() < 0.7 else DefensiveLine.STANDARD
        
        # Otherwise based on mentality
        if mentality in [TacticMentality.DEFENSIVE, TacticMentality.CAUTIOUS]:
            return DefensiveLine.DEEP
        elif mentality == TacticMentality.BALANCED:
            return DefensiveLine.STANDARD
        elif mentality == TacticMentality.POSITIVE:
            return DefensiveLine.STANDARD if random.random() < 0.5 else DefensiveLine.HIGH
        else:  # ATTACKING, VERY_ATTACKING
            return DefensiveLine.HIGH
    
    def _estimate_opponent_formation(self, opponent_profile: ClubProfile) -> str:
        """
        Estimate opponent's likely formation based on their profile.
        
        Args:
            opponent_profile: Opponent's club profile
        
        Returns:
            str: Estimated formation
        """
        # Simple estimation based on reputation
        if opponent_profile.reputation >= 70:
            # Top clubs likely use attacking formations
            return random.choice(["4-3-3", "4-2-3-1", "3-4-3"])
        elif opponent_profile.reputation >= 50:
            # Mid-tier clubs use balanced formations
            return random.choice(["4-4-2", "4-2-3-1", "4-3-3"])
        else:
            # Lower clubs use defensive formations
            return random.choice(["4-4-2", "5-3-2", "4-5-1"])
    
    def _select_width(
        self,
        formation: str,
        mentality: TacticMentality,
        opponent_formation: str = "4-4-2",
        weather: WeatherCondition = WeatherCondition.CLEAR,
    ) -> Width:
        """
        Select team width based on formation, mentality, and opponent.
        
        Enhanced to consider:
        - Opponent formation for tactical advantage
        - Weather conditions (wind affects wide play)
        
        Args:
            formation: Selected formation
            mentality: Selected mentality
            opponent_formation: Estimated opponent formation
            weather: Weather conditions
        
        Returns:
            Width: Selected width
        """
        # Wide formations prefer wide play
        wide_formations = ["4-3-3", "4-4-2", "3-5-2", "4-2-3-1"]
        narrow_formations = ["4-1-4-1", "4-3-2-1", "3-6-1"]
        
        # Weather impact on width
        if weather == WeatherCondition.WINDY:
            # Wind makes wide play less effective
            if formation in narrow_formations:
                return Width.NARROW
            else:
                return Width.STANDARD
        
        # Exploit narrow opponent formations with width
        if opponent_formation in narrow_formations:
            if formation in wide_formations:
                return Width.WIDE
        
        if formation in wide_formations:
            if mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
                return Width.WIDE
            else:
                return Width.STANDARD
        elif formation in narrow_formations:
            return Width.NARROW
        else:
            return Width.STANDARD
    
    def _select_tempo(
        self,
        personality: AIPersonality,
        mentality: TacticMentality,
        squad_average_ca: float,
        pressing: PressingIntensity,
        weather: WeatherCondition = WeatherCondition.CLEAR,
    ) -> Tempo:
        """
        Select team tempo based on personality, mentality, and pressing.
        
        Enhanced to consider:
        - Pressing intensity (high pressing needs faster tempo)
        - Weather conditions (affects pace of play)
        
        Args:
            personality: Club's AI personality
            mentality: Selected mentality
            squad_average_ca: Squad's average CA
            pressing: Selected pressing intensity
            weather: Weather conditions
        
        Returns:
            Tempo: Selected tempo
        """
        # Weather impact on tempo
        if weather in [WeatherCondition.RAINY, WeatherCondition.SNOWY]:
            # Bad weather slows down play
            if personality == AIPersonality.POSSESSION:
                return Tempo.SLOW
            else:
                return Tempo.STANDARD
        elif weather == WeatherCondition.FOGGY:
            # Fog makes teams play more cautiously
            return Tempo.SLOW if random.random() < 0.6 else Tempo.STANDARD
        
        # Possession personality prefers slower tempo
        if personality == AIPersonality.POSSESSION:
            return Tempo.SLOW if squad_average_ca >= 130 else Tempo.STANDARD
        
        # High pressing requires faster tempo
        if pressing in [PressingIntensity.GEGENPRESSING, PressingIntensity.HIGH]:
            return Tempo.FAST
        
        # Attacking mentality prefers faster tempo
        if mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
            return Tempo.FAST
        elif mentality in [TacticMentality.DEFENSIVE, TacticMentality.CAUTIOUS]:
            return Tempo.SLOW
        else:
            return Tempo.STANDARD
    
    def should_make_substitution(
        self,
        minute: int,
        score_difference: int,  # positive = winning, negative = losing
        player_stamina: float,  # 0.0-1.0
        player_rating: float,  # 1.0-10.0
        substitutions_remaining: int,
        player_position: str = "M",  # Position category: 'D', 'M', 'F'
        is_key_player: bool = False,
        injury_risk: float = 0.0,  # 0.0-1.0, calculated from stamina and match intensity
        current_mentality: Optional[TacticMentality] = None,
    ) -> bool:
        """
        Enhanced substitution decision-making with sophisticated logic.
        
        Considers:
        - Position-specific substitution needs (forwards tire faster)
        - Tactical substitutions (changing formation/mentality)
        - Injury risk management (substitute tired players before injury)
        - Score-based substitution strategies
        - Time-based substitution windows (optimal timing)
        - Substitution budget management (don't waste all subs early)
        
        Args:
            minute: Current match minute
            score_difference: Goal difference (positive = winning)
            player_stamina: Player's current stamina (0.0-1.0)
            player_rating: Player's current match rating (1.0-10.0)
            substitutions_remaining: Number of substitutions remaining
            player_position: Position category ('D', 'M', 'F')
            is_key_player: Whether this is a key player
            injury_risk: Injury risk factor (0.0-1.0)
            current_mentality: Current team mentality
        
        Returns:
            bool: True if should substitute, False otherwise
        """
        if substitutions_remaining <= 0:
            return False
        
        # Calculate substitution urgency score (0-10)
        urgency_score = 0.0
        
        # 1. INJURY RISK MANAGEMENT
        # High injury risk should trigger immediate substitution
        if injury_risk > 0.7:
            urgency_score += 5.0
        elif injury_risk > 0.5:
            urgency_score += 3.0
        elif injury_risk > 0.3:
            urgency_score += 1.5
        
        # 2. STAMINA-BASED URGENCY (position-specific)
        # Forwards and attacking midfielders tire faster and need earlier subs
        if player_position == 'F':
            # Forwards: substitute earlier due to high work rate
            if player_stamina < 0.35:
                urgency_score += 4.0
            elif player_stamina < 0.5:
                urgency_score += 2.5
            elif player_stamina < 0.65:
                urgency_score += 1.0
        elif player_position == 'M':
            # Midfielders: moderate stamina requirements
            if player_stamina < 0.3:
                urgency_score += 4.0
            elif player_stamina < 0.45:
                urgency_score += 2.0
            elif player_stamina < 0.6:
                urgency_score += 0.5
        else:  # 'D' - Defenders
            # Defenders: can play longer with lower stamina
            if player_stamina < 0.25:
                urgency_score += 4.0
            elif player_stamina < 0.4:
                urgency_score += 1.5
        
        # 3. PERFORMANCE-BASED URGENCY
        if player_rating < 4.5:
            urgency_score += 3.0  # Very poor performance
        elif player_rating < 5.5:
            urgency_score += 1.5  # Below average performance
        elif player_rating < 6.0:
            urgency_score += 0.5  # Slightly below average
        
        # 4. TIME-BASED SUBSTITUTION WINDOWS
        # Optimal substitution timing: 60-65, 70-75, 80-85 minutes
        substitution_window_bonus = 0.0
        
        if 60 <= minute <= 65:
            substitution_window_bonus = 1.0  # First window
        elif 70 <= minute <= 75:
            substitution_window_bonus = 1.5  # Second window (prime time)
        elif 80 <= minute <= 85:
            substitution_window_bonus = 2.0  # Final window (urgent)
        elif minute > 85:
            substitution_window_bonus = 0.5  # Too late, limited impact
        
        urgency_score += substitution_window_bonus
        
        # 5. SCORE-BASED TACTICAL ADJUSTMENTS
        if score_difference < 0:  # Losing
            if minute >= 60:
                urgency_score += 2.0  # Need to change something
            if minute >= 75:
                urgency_score += 1.5  # Desperate for goals
            
            # Substitute defensive players for attackers when losing late
            if minute >= 70 and player_position == 'D' and not is_key_player:
                urgency_score += 1.5
        
        elif score_difference > 0:  # Winning
            if minute >= 75:
                # Substitute tired players to maintain lead
                if player_stamina < 0.5:
                    urgency_score += 1.5
            
            # Substitute attacking players for defensive ones when winning late
            if minute >= 80 and player_position == 'F' and player_stamina < 0.6:
                urgency_score += 1.0
        
        else:  # Drawing
            if minute >= 70:
                # Moderate urgency to find a winner
                urgency_score += 0.5
        
        # 6. SUBSTITUTION BUDGET MANAGEMENT
        # Don't waste all substitutions too early
        if minute < 60:
            # Very conservative early on
            if substitutions_remaining <= 1:
                urgency_score *= 0.3  # Save last sub for emergencies
            elif substitutions_remaining <= 2:
                urgency_score *= 0.5
            
            # Only substitute for critical issues early
            if urgency_score < 4.0:
                return False
        
        elif minute < 70:
            # Moderate conservation
            if substitutions_remaining <= 1:
                urgency_score *= 0.6
            
            if urgency_score < 3.0:
                return False
        
        else:  # minute >= 70
            # More liberal with substitutions
            if substitutions_remaining <= 1 and minute < 80:
                urgency_score *= 0.8  # Still save one for late game
        
        # 7. KEY PLAYER PROTECTION
        # Be more reluctant to substitute key players unless necessary
        if is_key_player:
            urgency_score *= 0.8
        
        # 8. TACTICAL MENTALITY CONSIDERATIONS
        if current_mentality:
            if current_mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
                # Attacking mentality: substitute tired players earlier to maintain intensity
                if player_stamina < 0.55:
                    urgency_score += 0.5
            elif current_mentality == TacticMentality.DEFENSIVE:
                # Defensive mentality: can tolerate lower stamina
                urgency_score *= 0.9
        
        # 9. DECISION THRESHOLD
        # Base threshold: 4.0 (moderate urgency)
        # Add randomness to avoid predictable patterns
        threshold = 4.0 + random.uniform(-0.5, 0.5)
        
        # Adjust threshold based on time
        if minute >= 80:
            threshold -= 1.0  # Lower threshold late in game
        elif minute >= 70:
            threshold -= 0.5
        elif minute < 60:
            threshold += 1.0  # Higher threshold early in game
        
        return urgency_score >= threshold
    
    def calculate_injury_risk(
        self,
        player_stamina: float,
        match_intensity: float = 0.7,  # 0.0-1.0
        player_age: int = 25,
        player_injury_proneness: float = 0.0,  # 0.0-1.0
    ) -> float:
        """
        Calculate injury risk for a player based on stamina and other factors.
        
        Args:
            player_stamina: Player's current stamina (0.0-1.0)
            match_intensity: Match intensity level (0.0-1.0)
            player_age: Player's age
            player_injury_proneness: Player's injury proneness factor (0.0-1.0)
        
        Returns:
            float: Injury risk (0.0-1.0)
        """
        risk = 0.0
        
        # Stamina is the primary factor
        if player_stamina < 0.3:
            risk += 0.5
        elif player_stamina < 0.5:
            risk += 0.3
        elif player_stamina < 0.7:
            risk += 0.1
        
        # Match intensity increases risk
        risk += match_intensity * 0.2
        
        # Age factor (older players more injury-prone)
        if player_age >= 33:
            risk += 0.15
        elif player_age >= 30:
            risk += 0.08
        elif player_age <= 20:
            risk += 0.05  # Young players also slightly more prone
        
        # Player-specific injury proneness
        risk += player_injury_proneness * 0.3
        
        return min(1.0, risk)
    
    def calculate_transfer_need_score(
        self,
        position: str,
        squad_players_in_position: int,
        squad_average_ca_in_position: float,
        club_reputation: int,
        squad_age_average_in_position: Optional[float] = None,
        injured_players_in_position: int = 0,
        players_leaving_in_position: int = 0,
    ) -> float:
        """
        Enhanced transfer need calculation with comprehensive factors.
        
        Considers:
        - Squad depth (number of players in position)
        - Squad quality (average CA vs club ambition)
        - Squad age profile (aging squad needs replacements)
        - Injury situation (injured players create urgent needs)
        - Contract situations (players leaving on free transfers)
        
        Args:
            position: Position to evaluate (e.g., "ST", "CM", "CB")
            squad_players_in_position: Number of players in this position
            squad_average_ca_in_position: Average CA of players in this position
            club_reputation: Club reputation (1-100)
            squad_age_average_in_position: Average age of players in position
            injured_players_in_position: Number of injured players in position
            players_leaving_in_position: Number of players leaving (contracts expiring)
        
        Returns:
            float: Need score (0.0-10.0, higher = more needed)
        """
        need_score = 0.0
        
        # 1. POSITION DEPTH NEED
        ideal_players = {
            "GK": 2,
            "CB": 4,
            "LB": 2, "RB": 2, "WB": 2,
            "DM": 2, "CM": 4, "AM": 2,
            "LW": 2, "RW": 2,
            "ST": 3, "CF": 3,
        }
        
        ideal = ideal_players.get(position, 2)
        
        # Account for players leaving and injured
        effective_players = squad_players_in_position - players_leaving_in_position
        available_players = effective_players - injured_players_in_position
        
        if effective_players < ideal - 1:
            # Critical shortage (2+ below ideal)
            need_score += 4.0
        elif effective_players < ideal:
            # Urgent need (1 below ideal)
            need_score += 2.5
        elif effective_players == ideal:
            # At ideal but could use depth
            need_score += 0.5
        
        # Additional urgency if many players unavailable
        if available_players < ideal - 1:
            need_score += 2.0  # Immediate need due to injuries
        
        # 2. QUALITY NEED BASED ON CLUB AMBITION
        target_ca = club_reputation * 1.5  # Target CA based on reputation
        
        if squad_average_ca_in_position < target_ca - 30:
            need_score += 4.0  # Severe quality gap
        elif squad_average_ca_in_position < target_ca - 20:
            need_score += 3.0  # Significant quality gap
        elif squad_average_ca_in_position < target_ca - 10:
            need_score += 1.5  # Moderate quality gap
        elif squad_average_ca_in_position < target_ca:
            need_score += 0.5  # Minor quality gap
        
        # 3. AGE PROFILE NEED
        if squad_age_average_in_position is not None:
            if squad_age_average_in_position >= 32:
                # Aging squad needs urgent replacement
                need_score += 2.5
            elif squad_age_average_in_position >= 30:
                # Aging squad needs planning
                need_score += 1.5
            elif squad_age_average_in_position >= 28:
                # Squad entering peak, moderate need for succession
                need_score += 0.5
            elif squad_age_average_in_position <= 20:
                # Very young squad needs experience
                need_score += 1.0
        
        # 4. CONTRACT SITUATION URGENCY
        if players_leaving_in_position > 0:
            # Players leaving creates urgent need
            need_score += players_leaving_in_position * 2.0
        
        # 5. INJURY CRISIS URGENCY
        if injured_players_in_position >= 2:
            # Multiple injuries create immediate need
            need_score += 1.5
        elif injured_players_in_position >= 1:
            need_score += 0.5
        
        return min(10.0, need_score)
    
    def generate_transfer_bid(
        self,
        club_profile: ClubProfile,
        player_ca: int,
        player_pa: int,
        player_market_value: int,
        player_age: int,
        player_position: str,
        need_score: float,
        player_wage: int,
        player_contract_months_remaining: int = 24,
        is_transfer_window_open: bool = True,
        current_season_week: int = 1,
    ) -> Optional[Dict]:
        """
        Enhanced transfer bid generation with comprehensive logic.
        
        Considers:
        - Club budget constraints (don't overspend)
        - Player value assessment (age, potential, contract situation)
        - Transfer window timing (urgency affects bid amount)
        - Wage affordability (must fit wage budget)
        - Need-based bidding (higher need = willing to pay more)
        - Contract length negotiation (age-appropriate contracts)
        - Opportunity assessment (bargains vs premium targets)
        
        Args:
            club_profile: Profile of the bidding club
            player_ca: Player's current ability
            player_pa: Player's potential ability
            player_market_value: Player's market value
            player_age: Player's age
            player_position: Player's position
            need_score: How much the club needs this player (0-10)
            player_wage: Player's current wage
            player_contract_months_remaining: Months left on contract
            is_transfer_window_open: Whether transfer window is open
            current_season_week: Current week of season (1-52)
        
        Returns:
            Optional[Dict]: Bid details or None if club won't bid
        """
        # 1. TRANSFER WINDOW CHECK
        if not is_transfer_window_open:
            # Only emergency loans outside window
            if need_score < 8.0:  # Only for critical needs
                return None
        
        # 2. BUDGET AFFORDABILITY CHECK
        # Don't spend more than 40% of budget on single player
        max_affordable_fee = int(club_profile.transfer_budget * 0.4)
        
        if player_market_value * 0.5 > max_affordable_fee:
            return None  # Can't afford even a low bid
        
        # 3. QUALITY MATCH CHECK
        # Player should match club ambition
        target_ca = club_profile.reputation * 1.5
        
        if player_ca < target_ca - 30:
            return None  # Player too weak for club ambition
        
        if player_ca > target_ca + 50:
            # Player too good/expensive unless critical need
            if need_score < 7.0:
                return None
        
        # 4. WAGE AFFORDABILITY CHECK
        # Estimate wage offer (typically 10-20% increase from current wage)
        estimated_wage_offer = int(player_wage * random.uniform(1.1, 1.2))
        
        # Check if wage fits budget (assume max 30% of wage budget on one player)
        max_affordable_wage = int(club_profile.wage_budget * 0.3)
        
        if estimated_wage_offer > max_affordable_wage:
            return None  # Can't afford wages
        
        # 5. CALCULATE BASE BID AMOUNT
        base_bid = player_market_value
        bid_multiplier = 1.0
        
        # 6. NEED-BASED ADJUSTMENT
        if need_score >= 8.0:
            # Critical need - willing to overpay significantly
            bid_multiplier = random.uniform(1.15, 1.35)
        elif need_score >= 6.0:
            # High need - willing to pay premium
            bid_multiplier = random.uniform(1.05, 1.20)
        elif need_score >= 4.0:
            # Moderate need - fair value
            bid_multiplier = random.uniform(0.95, 1.10)
        else:
            # Low need - opportunistic bid
            bid_multiplier = random.uniform(0.75, 0.95)
        
        # 7. AGE-BASED ADJUSTMENT
        if player_age <= 21:
            # Young player with potential - premium
            bid_multiplier *= 1.15
        elif player_age <= 24:
            # Prime development age - slight premium
            bid_multiplier *= 1.08
        elif player_age >= 30:
            # Older player - discount
            bid_multiplier *= 0.85
        elif player_age >= 32:
            # Veteran - significant discount
            bid_multiplier *= 0.70
        
        # 8. POTENTIAL-BASED ADJUSTMENT
        potential_gap = player_pa - player_ca
        if potential_gap >= 20 and player_age <= 23:
            # High potential young player - premium
            bid_multiplier *= 1.12
        elif potential_gap >= 10 and player_age <= 25:
            # Good potential - slight premium
            bid_multiplier *= 1.05
        
        # 9. CONTRACT SITUATION ADJUSTMENT
        if player_contract_months_remaining <= 6:
            # Contract expiring soon - significant discount
            bid_multiplier *= 0.65
        elif player_contract_months_remaining <= 12:
            # Contract expiring within year - discount
            bid_multiplier *= 0.80
        elif player_contract_months_remaining <= 18:
            # Contract running down - slight discount
            bid_multiplier *= 0.90
        
        # 10. TRANSFER WINDOW TIMING ADJUSTMENT
        # Summer window: weeks 1-8, Winter window: weeks 26-30
        if is_transfer_window_open:
            if current_season_week <= 2 or current_season_week == 26:
                # Early in window - can negotiate, lower bids
                bid_multiplier *= 0.95
            elif current_season_week >= 7 or current_season_week >= 29:
                # Late in window - urgency, higher bids
                if need_score >= 5.0:
                    bid_multiplier *= 1.10
        
        # 11. CLUB FINANCIAL SITUATION ADJUSTMENT
        if club_profile.balance < 0:
            # Club in debt - more conservative
            bid_multiplier *= 0.85
        elif club_profile.balance > club_profile.transfer_budget * 2:
            # Club financially healthy - can be more aggressive
            bid_multiplier *= 1.05
        
        # 12. CALCULATE FINAL BID AMOUNT
        bid_amount = int(base_bid * bid_multiplier)
        
        # 13. BUDGET CONSTRAINT CHECK
        if bid_amount > max_affordable_fee:
            bid_amount = max_affordable_fee
        
        # Don't bid more than 150% of market value (too unrealistic)
        if bid_amount > player_market_value * 1.5:
            bid_amount = int(player_market_value * 1.5)
        
        # Minimum bid should be at least 50% of market value
        if bid_amount < player_market_value * 0.5:
            return None  # Bid too low to be realistic
        
        # 14. CALCULATE WAGE OFFER
        # Base wage offer on player's current wage and club's wage structure
        wage_increase_multiplier = 1.0
        
        if need_score >= 7.0:
            # High need - offer significant wage increase
            wage_increase_multiplier = random.uniform(1.15, 1.30)
        elif need_score >= 5.0:
            # Moderate need - offer decent increase
            wage_increase_multiplier = random.uniform(1.10, 1.20)
        else:
            # Low need - modest increase
            wage_increase_multiplier = random.uniform(1.05, 1.15)
        
        # Adjust for club reputation (bigger clubs can offer more)
        if club_profile.reputation >= 80:
            wage_increase_multiplier *= 1.10
        elif club_profile.reputation >= 60:
            wage_increase_multiplier *= 1.05
        elif club_profile.reputation <= 40:
            wage_increase_multiplier *= 0.95
        
        wage_offer = int(player_wage * wage_increase_multiplier)
        
        # Final wage affordability check
        if wage_offer > max_affordable_wage:
            wage_offer = max_affordable_wage
        
        # 15. DETERMINE CONTRACT LENGTH
        # Age-appropriate contract lengths
        if player_age <= 23:
            # Young player - longer contract to secure future
            contract_length = random.choice([4, 5, 5])  # Prefer 5 years
        elif player_age <= 27:
            # Prime age - standard contract
            contract_length = random.choice([3, 4, 4, 5])  # Prefer 4 years
        elif player_age <= 30:
            # Approaching 30 - shorter contract
            contract_length = random.choice([3, 3, 4])  # Prefer 3 years
        elif player_age <= 32:
            # Over 30 - short contract
            contract_length = random.choice([2, 3, 3])  # Prefer 3 years
        else:
            # Veteran - very short contract
            contract_length = random.choice([1, 2, 2])  # Prefer 2 years
        
        # 16. CALCULATE TRANSFER PRIORITY
        # Priority score helps determine which transfers to pursue first
        priority_score = need_score * 10  # Base on need
        
        # Adjust for value
        if bid_amount < player_market_value * 0.9:
            priority_score += 15  # Bargain opportunity
        elif bid_amount > player_market_value * 1.2:
            priority_score -= 10  # Expensive purchase
        
        # Adjust for age and potential
        if player_age <= 23 and potential_gap >= 15:
            priority_score += 20  # High-potential youngster
        elif player_age >= 32:
            priority_score -= 15  # Aging player
        
        # Adjust for contract situation
        if player_contract_months_remaining <= 6:
            priority_score += 25  # Bargain due to contract
        
        # 17. RETURN BID DETAILS
        return {
            "bid_amount": bid_amount,
            "wage_offer": wage_offer,
            "contract_length": contract_length,
            "need_score": need_score,
            "priority_score": min(100, max(0, priority_score)),
            "bid_multiplier": bid_multiplier,
            "estimated_total_cost": bid_amount + (wage_offer * 52 * contract_length),
        }
    
    def should_rest_player(
        self,
        player_ca: int,
        squad_average_ca: float,
        matches_played_recently: int,
        next_match_importance: int,  # 1-10
        current_match_importance: int,  # 1-10
    ) -> bool:
        """
        Decide whether to rest a key player for squad rotation.
        
        Implements requirement 19.7: AI clubs rest key players before important matches.
        
        Args:
            player_ca: Player's current ability
            squad_average_ca: Squad's average CA
            matches_played_recently: Number of matches in last 2 weeks
            next_match_importance: Importance of next match (1-10)
            current_match_importance: Importance of current match (1-10)
        
        Returns:
            bool: True if player should be rested, False otherwise
        """
        # Only rest key players (CA significantly above average)
        if player_ca < squad_average_ca + 10:
            return False  # Not a key player
        
        # Don't rest if current match is very important
        if current_match_importance >= 8:
            return False
        
        # Rest if next match is much more important
        if next_match_importance >= current_match_importance + 3:
            if matches_played_recently >= 3:
                return random.random() < 0.7  # 70% chance to rest
        
        # Rest if player has played many matches recently
        if matches_played_recently >= 4:
            return random.random() < 0.5  # 50% chance to rest
        
        return False
    
    def select_starting_11(
        self,
        squad_players: List[Tuple],  # List of (player, ca, position, stamina, morale)
        formation: str,
        rest_key_players: bool = False,
    ) -> Tuple[List[int], List[int]]:
        """
        Select starting 11 and substitutes from squad.
        
        Args:
            squad_players: List of tuples (player_id, ca, position, stamina, morale)
            formation: Formation string (e.g., "4-4-2")
            rest_key_players: Whether to rest key players for rotation
        
        Returns:
            Tuple of (starting_11_ids, substitute_ids)
        """
        # Parse formation to determine position requirements
        position_requirements = self._parse_formation_requirements(formation)
        
        # Sort players by effective CA (considering stamina and morale)
        sorted_players = sorted(
            squad_players,
            key=lambda p: self._calculate_selection_score(p[1], p[3], p[4]),
            reverse=True
        )
        
        starting_11 = []
        substitutes = []
        
        # Select goalkeeper first
        for player_id, ca, position, stamina, morale in sorted_players:
            if 'GK' in position.upper() and len([p for p in starting_11 if 'GK' in p[2].upper()]) == 0:
                starting_11.append((player_id, ca, position, stamina, morale))
                break
        
        # Select outfield players based on formation requirements
        for pos_category, count in position_requirements.items():
            if pos_category == 'GK':
                continue
            
            selected_count = 0
            for player_id, ca, position, stamina, morale in sorted_players:
                if player_id in [p[0] for p in starting_11]:
                    continue
                
                if self._position_matches_category(position, pos_category):
                    starting_11.append((player_id, ca, position, stamina, morale))
                    selected_count += 1
                    
                    if selected_count >= count:
                        break
        
        # Fill remaining spots if needed
        while len(starting_11) < 11:
            for player_id, ca, position, stamina, morale in sorted_players:
                if player_id not in [p[0] for p in starting_11]:
                    starting_11.append((player_id, ca, position, stamina, morale))
                    break
        
        # Select substitutes (best remaining players)
        for player_id, ca, position, stamina, morale in sorted_players:
            if player_id not in [p[0] for p in starting_11] and len(substitutes) < 7:
                substitutes.append(player_id)
        
        return [p[0] for p in starting_11[:11]], substitutes[:7]
    
    def _parse_formation_requirements(self, formation: str) -> Dict[str, int]:
        """
        Parse formation string to determine position requirements.
        
        Args:
            formation: Formation string (e.g., "4-4-2")
        
        Returns:
            Dict mapping position categories to counts
        """
        parts = formation.split('-')
        
        if len(parts) == 3:
            defenders, midfielders, forwards = map(int, parts)
            return {
                'GK': 1,
                'D': defenders,
                'M': midfielders,
                'F': forwards,
            }
        elif len(parts) == 4:
            # Formation like 4-2-3-1
            defenders, dm, am, forwards = map(int, parts)
            return {
                'GK': 1,
                'D': defenders,
                'M': dm + am,
                'F': forwards,
            }
        else:
            # Default to 4-4-2
            return {
                'GK': 1,
                'D': 4,
                'M': 4,
                'F': 2,
            }
    
    def _position_matches_category(self, position: str, category: str) -> bool:
        """
        Check if a player position matches a formation category.
        
        Args:
            position: Player position (e.g., "CB", "CM", "ST")
            category: Formation category ('D', 'M', 'F')
        
        Returns:
            bool: True if position matches category
        """
        position_upper = position.upper()
        
        if category == 'D':
            return any(p in position_upper for p in ['CB', 'LB', 'RB', 'WB', 'D '])
        elif category == 'M':
            return any(p in position_upper for p in ['CM', 'DM', 'AM', 'M ']) and 'GK' not in position_upper
        elif category == 'F':
            return any(p in position_upper for p in ['ST', 'CF', 'W', 'F '])
        
        return False
    
    def _calculate_selection_score(self, ca: int, stamina: float, morale: int) -> float:
        """
        Calculate player selection score considering CA, stamina, and morale.
        
        Args:
            ca: Current ability
            stamina: Stamina (0-100)
            morale: Morale (0-100)
        
        Returns:
            float: Selection score
        """
        score = float(ca)
        
        # Reduce score for low stamina
        if stamina < 50:
            score *= 0.9
        elif stamina < 70:
            score *= 0.95
        
        # Reduce score for low morale
        if morale < 40:
            score *= 0.95
        elif morale < 60:
            score *= 0.98
        
        return score
    
    def should_make_tactical_adjustment(
        self,
        minute: int,
        score_difference: int,
        possession_percentage: float,
        shots_ratio: float,
        current_mentality: TacticMentality,
    ) -> Optional[TacticMentality]:
        """
        Decide whether to make in-match tactical adjustment.
        
        Args:
            minute: Current match minute
            score_difference: Goal difference (positive = winning)
            possession_percentage: Team's possession percentage (0-100)
            shots_ratio: Ratio of team shots to opponent shots
            current_mentality: Current team mentality
        
        Returns:
            Optional[TacticMentality]: New mentality if adjustment needed, None otherwise
        """
        # Don't adjust too early
        if minute < 30:
            return None
        
        # Losing badly - go more attacking
        if score_difference <= -2 and minute >= 60:
            if current_mentality in [TacticMentality.DEFENSIVE, TacticMentality.CAUTIOUS, TacticMentality.BALANCED]:
                return TacticMentality.ATTACKING
        
        # Losing by 1 - go more positive
        elif score_difference == -1 and minute >= 70:
            if current_mentality in [TacticMentality.DEFENSIVE, TacticMentality.CAUTIOUS]:
                return TacticMentality.POSITIVE
        
        # Winning - consider going more defensive late
        elif score_difference >= 1 and minute >= 75:
            if current_mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
                # 50% chance to become more defensive
                if random.random() < 0.5:
                    return TacticMentality.BALANCED
        
        # Dominating possession but not scoring - go more attacking
        elif score_difference == 0 and minute >= 60:
            if possession_percentage > 65 and shots_ratio < 1.2:
                if current_mentality == TacticMentality.BALANCED:
                    return TacticMentality.POSITIVE
        
        return None
    
    def evaluate_tactical_adjustment_need(
        self,
        minute: int,
        score_difference: int,
        possession_percentage: float,
        shots_on_target: int,
        opponent_shots_on_target: int,
        dangerous_attacks: int,
        opponent_dangerous_attacks: int,
        current_tactics: TacticPreset,
        team_stamina_average: float = 0.7,
        opponent_stamina_average: float = 0.7,
        recent_momentum: str = "neutral",  # "positive", "negative", "neutral"
    ) -> Optional[Dict[str, any]]:
        """
        Comprehensive evaluation of whether tactical adjustments are needed.
        
        This is the main method for Task 5.5 - AI in-match tactical adjustments.
        Analyzes match state and recommends tactical changes including:
        - Mentality adjustments
        - Formation changes
        - Pressing intensity changes
        - Defensive line adjustments
        - Width and tempo changes
        
        Args:
            minute: Current match minute
            score_difference: Goal difference (positive = winning)
            possession_percentage: Team's possession percentage (0-100)
            shots_on_target: Team's shots on target
            opponent_shots_on_target: Opponent's shots on target
            dangerous_attacks: Team's dangerous attacks
            opponent_dangerous_attacks: Opponent's dangerous attacks
            current_tactics: Current tactical setup
            team_stamina_average: Team's average stamina (0.0-1.0)
            opponent_stamina_average: Opponent's average stamina (0.0-1.0)
            recent_momentum: Recent match momentum
        
        Returns:
            Optional[Dict]: Tactical adjustment recommendations or None
        """
        # Don't adjust too early in the match
        if minute < 30:
            return None
        
        # Calculate match performance metrics
        performance_score = self._calculate_performance_score(
            possession_percentage=possession_percentage,
            shots_on_target=shots_on_target,
            opponent_shots_on_target=opponent_shots_on_target,
            dangerous_attacks=dangerous_attacks,
            opponent_dangerous_attacks=opponent_dangerous_attacks,
        )
        
        # Determine adjustment urgency (0.0-1.0)
        urgency = self._calculate_adjustment_urgency(
            minute=minute,
            score_difference=score_difference,
            performance_score=performance_score,
            recent_momentum=recent_momentum,
        )
        
        # If urgency is low, don't adjust
        if urgency < 0.3:
            return None
        
        # Build adjustment recommendations
        adjustments = {}
        
        # 1. MENTALITY ADJUSTMENTS
        new_mentality = self._recommend_mentality_adjustment(
            minute=minute,
            score_difference=score_difference,
            current_mentality=current_tactics.mentality,
            performance_score=performance_score,
            urgency=urgency,
        )
        if new_mentality and new_mentality != current_tactics.mentality:
            adjustments["mentality"] = new_mentality
        
        # 2. FORMATION CHANGES
        new_formation = self._recommend_formation_change(
            minute=minute,
            score_difference=score_difference,
            current_formation=current_tactics.formation,
            current_mentality=current_tactics.mentality,
            performance_score=performance_score,
        )
        if new_formation and new_formation != current_tactics.formation:
            adjustments["formation"] = new_formation
        
        # 3. PRESSING INTENSITY ADJUSTMENTS
        new_pressing = self._recommend_pressing_adjustment(
            minute=minute,
            score_difference=score_difference,
            current_pressing=current_tactics.pressing,
            team_stamina_average=team_stamina_average,
            opponent_stamina_average=opponent_stamina_average,
            performance_score=performance_score,
        )
        if new_pressing and new_pressing != current_tactics.pressing:
            adjustments["pressing"] = new_pressing
        
        # 4. DEFENSIVE LINE ADJUSTMENTS
        new_defensive_line = self._recommend_defensive_line_adjustment(
            minute=minute,
            score_difference=score_difference,
            current_defensive_line=current_tactics.defensive_line,
            current_pressing=current_tactics.pressing,
            opponent_dangerous_attacks=opponent_dangerous_attacks,
        )
        if new_defensive_line and new_defensive_line != current_tactics.defensive_line:
            adjustments["defensive_line"] = new_defensive_line
        
        # 5. WIDTH ADJUSTMENTS
        new_width = self._recommend_width_adjustment(
            minute=minute,
            score_difference=score_difference,
            current_width=current_tactics.width,
            possession_percentage=possession_percentage,
            performance_score=performance_score,
        )
        if new_width and new_width != current_tactics.width:
            adjustments["width"] = new_width
        
        # 6. TEMPO ADJUSTMENTS
        new_tempo = self._recommend_tempo_adjustment(
            minute=minute,
            score_difference=score_difference,
            current_tempo=current_tactics.tempo,
            team_stamina_average=team_stamina_average,
            performance_score=performance_score,
        )
        if new_tempo and new_tempo != current_tactics.tempo:
            adjustments["tempo"] = new_tempo
        
        # Return adjustments if any were recommended
        if adjustments:
            return {
                "adjustments": adjustments,
                "urgency": urgency,
                "reason": self._generate_adjustment_reason(
                    minute, score_difference, performance_score, adjustments
                ),
            }
        
        return None
    
    def _calculate_performance_score(
        self,
        possession_percentage: float,
        shots_on_target: int,
        opponent_shots_on_target: int,
        dangerous_attacks: int,
        opponent_dangerous_attacks: int,
    ) -> float:
        """
        Calculate overall team performance score (-1.0 to +1.0).
        
        Negative = underperforming, Positive = dominating
        
        Args:
            possession_percentage: Team's possession (0-100)
            shots_on_target: Team's shots on target
            opponent_shots_on_target: Opponent's shots on target
            dangerous_attacks: Team's dangerous attacks
            opponent_dangerous_attacks: Opponent's dangerous attacks
        
        Returns:
            float: Performance score (-1.0 to +1.0)
        """
        score = 0.0
        
        # Possession factor (weight: 0.3)
        possession_factor = (possession_percentage - 50) / 50  # -1 to +1
        score += possession_factor * 0.3
        
        # Shots on target factor (weight: 0.4)
        total_shots = shots_on_target + opponent_shots_on_target
        if total_shots > 0:
            shots_factor = (shots_on_target - opponent_shots_on_target) / total_shots
            score += shots_factor * 0.4
        
        # Dangerous attacks factor (weight: 0.3)
        total_attacks = dangerous_attacks + opponent_dangerous_attacks
        if total_attacks > 0:
            attacks_factor = (dangerous_attacks - opponent_dangerous_attacks) / total_attacks
            score += attacks_factor * 0.3
        
        return max(-1.0, min(1.0, score))
    
    def _calculate_adjustment_urgency(
        self,
        minute: int,
        score_difference: int,
        performance_score: float,
        recent_momentum: str,
    ) -> float:
        """
        Calculate urgency of tactical adjustment (0.0-1.0).
        
        Args:
            minute: Current match minute
            score_difference: Goal difference
            performance_score: Performance score (-1 to +1)
            recent_momentum: Recent momentum ("positive", "negative", "neutral")
        
        Returns:
            float: Urgency score (0.0-1.0)
        """
        urgency = 0.0
        
        # Score-based urgency
        if score_difference <= -2:
            urgency += 0.6  # Losing badly - very urgent
        elif score_difference == -1:
            urgency += 0.4  # Losing by 1 - urgent
        elif score_difference == 0:
            urgency += 0.25  # Drawing - moderate urgency
        elif score_difference == 1:
            urgency += 0.15  # Winning by 1 - low urgency
        elif score_difference >= 2:
            urgency += 0.1  # Winning by 2+ - very low urgency
        
        # Time-based urgency multiplier
        if minute >= 75:
            urgency *= 1.5  # Late game - more urgent
        elif minute >= 60:
            urgency *= 1.2  # Mid-late game - slightly more urgent
        elif minute < 45:
            urgency *= 0.7  # First half - less urgent
        
        # Performance-based urgency
        if performance_score < -0.5:
            urgency += 0.3  # Being dominated
        elif performance_score < -0.2:
            urgency += 0.15  # Underperforming
        elif performance_score > 0.5:
            urgency -= 0.1  # Dominating - less urgent to change
        
        # Momentum-based urgency
        if recent_momentum == "negative":
            urgency += 0.2  # Negative momentum - need change
        elif recent_momentum == "positive":
            urgency -= 0.1  # Positive momentum - don't change
        
        return max(0.0, min(1.0, urgency))
    
    def _recommend_mentality_adjustment(
        self,
        minute: int,
        score_difference: int,
        current_mentality: TacticMentality,
        performance_score: float,
        urgency: float,
    ) -> Optional[TacticMentality]:
        """
        Recommend mentality adjustment based on match state.
        
        Args:
            minute: Current match minute
            score_difference: Goal difference
            current_mentality: Current mentality
            performance_score: Performance score (-1 to +1)
            urgency: Adjustment urgency (0-1)
        
        Returns:
            Optional[TacticMentality]: Recommended mentality or None
        """
        mentality_values = {
            TacticMentality.DEFENSIVE: 1,
            TacticMentality.CAUTIOUS: 2,
            TacticMentality.BALANCED: 3,
            TacticMentality.POSITIVE: 4,
            TacticMentality.ATTACKING: 5,
            TacticMentality.VERY_ATTACKING: 6,
        }
        
        current_value = mentality_values[current_mentality]
        target_value = current_value
        
        # Adjust based on score
        if score_difference <= -2 and minute >= 60:
            target_value = 5  # Attacking
        elif score_difference == -1 and minute >= 70:
            target_value = max(4, current_value)  # At least Positive
        elif score_difference >= 2 and minute >= 75:
            target_value = min(2, current_value)  # At most Cautious
        elif score_difference == 1 and minute >= 80:
            target_value = min(3, current_value)  # At most Balanced
        
        # Adjust based on performance
        if performance_score < -0.4 and score_difference <= 0:
            target_value += 1  # More attacking if underperforming
        elif performance_score > 0.4 and score_difference >= 0:
            target_value -= 1  # More defensive if dominating
        
        # Clamp to valid range
        target_value = max(1, min(6, target_value))
        
        # Only change if significantly different and urgency is high enough
        if abs(target_value - current_value) >= 1 and urgency >= 0.4:
            for mentality, value in mentality_values.items():
                if value == target_value:
                    return mentality
        
        return None
    
    def _recommend_formation_change(
        self,
        minute: int,
        score_difference: int,
        current_formation: str,
        current_mentality: TacticMentality,
        performance_score: float,
    ) -> Optional[str]:
        """
        Recommend formation change based on match state.
        
        Args:
            minute: Current match minute
            score_difference: Goal difference
            current_formation: Current formation
            current_mentality: Current mentality
            performance_score: Performance score
        
        Returns:
            Optional[str]: Recommended formation or None
        """
        # Only change formation in critical situations
        if minute < 60:
            return None
        
        # Parse current formation
        parts = current_formation.split('-')
        if len(parts) < 3:
            return None
        
        defenders = int(parts[0])
        
        # Losing badly late in game - go more attacking
        if score_difference <= -2 and minute >= 70:
            if defenders >= 4:
                # Switch to more attacking formation
                attacking_formations = ["4-3-3", "4-2-3-1", "3-4-3"]
                return random.choice([f for f in attacking_formations if f != current_formation])
        
        # Losing by 1 very late - add attacker
        elif score_difference == -1 and minute >= 80:
            if current_formation == "4-4-2":
                return "4-3-3"  # More attacking
            elif current_formation == "4-3-3":
                return "3-4-3"  # Even more attacking
        
        # Winning and under pressure - go more defensive
        elif score_difference >= 1 and minute >= 75 and performance_score < -0.3:
            if defenders <= 4:
                # Switch to more defensive formation
                defensive_formations = ["5-4-1", "5-3-2", "4-5-1"]
                return random.choice([f for f in defensive_formations if f != current_formation])
        
        return None
    
    def _recommend_pressing_adjustment(
        self,
        minute: int,
        score_difference: int,
        current_pressing: PressingIntensity,
        team_stamina_average: float,
        opponent_stamina_average: float,
        performance_score: float,
    ) -> Optional[PressingIntensity]:
        """
        Recommend pressing intensity adjustment.
        
        Args:
            minute: Current match minute
            score_difference: Goal difference
            current_pressing: Current pressing intensity
            team_stamina_average: Team stamina (0-1)
            opponent_stamina_average: Opponent stamina (0-1)
            performance_score: Performance score
        
        Returns:
            Optional[PressingIntensity]: Recommended pressing or None
        """
        pressing_values = {
            PressingIntensity.LOW: 1,
            PressingIntensity.MEDIUM: 2,
            PressingIntensity.HIGH: 3,
            PressingIntensity.GEGENPRESSING: 4,
        }
        
        current_value = pressing_values[current_pressing]
        target_value = current_value
        
        # Reduce pressing if team is tired
        if team_stamina_average < 0.5:
            target_value = min(2, current_value)  # At most Medium
        elif team_stamina_average < 0.65:
            target_value = min(3, current_value)  # At most High
        
        # Increase pressing if opponent is tired and we're chasing
        if opponent_stamina_average < 0.5 and score_difference <= 0 and minute >= 60:
            if team_stamina_average > 0.6:
                target_value = max(3, current_value)  # At least High
        
        # Reduce pressing when winning late to conserve energy
        if score_difference >= 1 and minute >= 75:
            target_value = min(2, current_value)  # At most Medium
        
        # Increase pressing when losing and need ball back
        if score_difference <= -1 and minute >= 60 and team_stamina_average > 0.55:
            target_value = max(3, current_value)  # At least High
        
        # Clamp to valid range
        target_value = max(1, min(4, target_value))
        
        # Only change if different
        if target_value != current_value:
            for pressing, value in pressing_values.items():
                if value == target_value:
                    return pressing
        
        return None
    
    def _recommend_defensive_line_adjustment(
        self,
        minute: int,
        score_difference: int,
        current_defensive_line: DefensiveLine,
        current_pressing: PressingIntensity,
        opponent_dangerous_attacks: int,
    ) -> Optional[DefensiveLine]:
        """
        Recommend defensive line adjustment.
        
        Args:
            minute: Current match minute
            score_difference: Goal difference
            current_defensive_line: Current defensive line
            current_pressing: Current pressing intensity
            opponent_dangerous_attacks: Opponent's dangerous attacks
        
        Returns:
            Optional[DefensiveLine]: Recommended defensive line or None
        """
        line_values = {
            DefensiveLine.DEEP: 1,
            DefensiveLine.STANDARD: 2,
            DefensiveLine.HIGH: 3,
            DefensiveLine.VERY_HIGH: 4,
        }
        
        current_value = line_values[current_defensive_line]
        target_value = current_value
        
        # Drop deeper if opponent is creating many chances
        if opponent_dangerous_attacks >= 5 and minute >= 45:
            target_value = min(2, current_value)  # At most Standard
        
        # Push higher when chasing game
        if score_difference <= -1 and minute >= 65:
            target_value = max(3, current_value)  # At least High
        
        # Drop deeper when protecting lead
        if score_difference >= 2 and minute >= 75:
            target_value = min(2, current_value)  # At most Standard
        
        # Align with pressing (high pressing needs high line)
        if current_pressing in [PressingIntensity.HIGH, PressingIntensity.GEGENPRESSING]:
            target_value = max(3, target_value)  # At least High
        elif current_pressing == PressingIntensity.LOW:
            target_value = min(2, target_value)  # At most Standard
        
        # Clamp to valid range
        target_value = max(1, min(4, target_value))
        
        # Only change if different
        if target_value != current_value:
            for line, value in line_values.items():
                if value == target_value:
                    return line
        
        return None
    
    def _recommend_width_adjustment(
        self,
        minute: int,
        score_difference: int,
        current_width: Width,
        possession_percentage: float,
        performance_score: float,
    ) -> Optional[Width]:
        """
        Recommend width adjustment.
        
        Args:
            minute: Current match minute
            score_difference: Goal difference
            current_width: Current width
            possession_percentage: Possession percentage
            performance_score: Performance score
        
        Returns:
            Optional[Width]: Recommended width or None
        """
        width_values = {
            Width.NARROW: 1,
            Width.STANDARD: 2,
            Width.WIDE: 3,
        }
        
        current_value = width_values[current_width]
        target_value = current_value
        
        # Go wider when chasing game to stretch defense
        if score_difference <= -1 and minute >= 65:
            target_value = 3  # Wide
        
        # Go narrower when protecting lead to stay compact
        elif score_difference >= 2 and minute >= 75:
            target_value = 1  # Narrow
        
        # Go wider if dominating possession but not creating chances
        elif possession_percentage > 60 and performance_score < 0.2 and minute >= 50:
            target_value = max(2, current_value)  # At least Standard
        
        # Only change if different
        if target_value != current_value:
            for width, value in width_values.items():
                if value == target_value:
                    return width
        
        return None
    
    def _recommend_tempo_adjustment(
        self,
        minute: int,
        score_difference: int,
        current_tempo: Tempo,
        team_stamina_average: float,
        performance_score: float,
    ) -> Optional[Tempo]:
        """
        Recommend tempo adjustment.
        
        Args:
            minute: Current match minute
            score_difference: Goal difference
            current_tempo: Current tempo
            team_stamina_average: Team stamina (0-1)
            performance_score: Performance score
        
        Returns:
            Optional[Tempo]: Recommended tempo or None
        """
        tempo_values = {
            Tempo.SLOW: 1,
            Tempo.STANDARD: 2,
            Tempo.FAST: 3,
        }
        
        current_value = tempo_values[current_tempo]
        target_value = current_value
        
        # Slow down if team is tired
        if team_stamina_average < 0.5:
            target_value = 1  # Slow
        
        # Speed up when chasing game
        elif score_difference <= -1 and minute >= 65 and team_stamina_average > 0.55:
            target_value = 3  # Fast
        
        # Slow down when protecting lead
        elif score_difference >= 2 and minute >= 75:
            target_value = 1  # Slow
        
        # Speed up if dominating but not scoring
        elif score_difference == 0 and performance_score > 0.3 and minute >= 60:
            target_value = max(2, current_value)  # At least Standard
        
        # Only change if different
        if target_value != current_value:
            for tempo, value in tempo_values.items():
                if value == target_value:
                    return tempo
        
        return None
    
    def _generate_adjustment_reason(
        self,
        minute: int,
        score_difference: int,
        performance_score: float,
        adjustments: Dict,
    ) -> str:
        """
        Generate human-readable reason for tactical adjustments.
        
        Args:
            minute: Current match minute
            score_difference: Goal difference
            performance_score: Performance score
            adjustments: Dict of adjustments
        
        Returns:
            str: Reason for adjustments
        """
        reasons = []
        
        # Score-based reasons
        if score_difference <= -2:
            reasons.append("losing badly")
        elif score_difference == -1:
            reasons.append("trailing by one goal")
        elif score_difference >= 2:
            reasons.append("winning comfortably")
        elif score_difference == 1:
            reasons.append("protecting narrow lead")
        else:
            reasons.append("looking for winner")
        
        # Performance-based reasons
        if performance_score < -0.4:
            reasons.append("being dominated")
        elif performance_score < -0.2:
            reasons.append("underperforming")
        elif performance_score > 0.4:
            reasons.append("dominating possession")
        
        # Time-based reasons
        if minute >= 80:
            reasons.append("in final stages")
        elif minute >= 70:
            reasons.append("entering final third")
        
        # Adjustment-specific reasons
        if "mentality" in adjustments:
            reasons.append(f"switching to {adjustments['mentality'].value} mentality")
        if "formation" in adjustments:
            reasons.append(f"changing to {adjustments['formation']} formation")
        if "pressing" in adjustments:
            reasons.append(f"adjusting pressing to {adjustments['pressing'].value}")
        
        return ", ".join(reasons)
    
    def identify_transfer_targets(
        self,
        club_profile: ClubProfile,
        squad_analysis: Dict[str, Dict],  # Position -> {count, avg_ca, avg_age, injured, leaving}
        available_players: List[Dict],  # List of player dicts with all attributes
        max_targets: int = 20,
        current_season_week: int = 1,
    ) -> List[Dict]:
        """
        Identify and prioritize transfer targets based on squad needs.
        
        Analyzes squad weaknesses and identifies suitable players from the
        available player pool. Returns a prioritized list of transfer targets.
        
        Args:
            club_profile: Profile of the club
            squad_analysis: Analysis of current squad by position
            available_players: List of available players to consider
            max_targets: Maximum number of targets to identify
            current_season_week: Current week of season
        
        Returns:
            List[Dict]: Prioritized list of transfer targets with bid details
        """
        transfer_targets = []
        
        # 1. ANALYZE SQUAD NEEDS BY POSITION
        position_needs = {}
        
        for position, analysis in squad_analysis.items():
            need_score = self.calculate_transfer_need_score(
                position=position,
                squad_players_in_position=analysis.get("count", 0),
                squad_average_ca_in_position=analysis.get("avg_ca", 100.0),
                club_reputation=club_profile.reputation,
                squad_age_average_in_position=analysis.get("avg_age"),
                injured_players_in_position=analysis.get("injured", 0),
                players_leaving_in_position=analysis.get("leaving", 0),
            )
            
            if need_score >= 2.0:  # Only consider positions with meaningful need
                position_needs[position] = need_score
        
        # Sort positions by need (highest first)
        sorted_positions = sorted(
            position_needs.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # 2. IDENTIFY SUITABLE PLAYERS FOR EACH NEEDED POSITION
        for position, need_score in sorted_positions:
            position_targets = []
            
            for player in available_players:
                # Check if player plays in this position
                if not self._player_can_play_position(player.get("position", ""), position):
                    continue
                
                # Check if player is already in club
                if player.get("club_id") == club_profile.club_id:
                    continue
                
                # Generate bid for this player
                bid = self.generate_transfer_bid(
                    club_profile=club_profile,
                    player_ca=player.get("ca", 100),
                    player_pa=player.get("pa", 100),
                    player_market_value=player.get("market_value", 1000000),
                    player_age=player.get("age", 25),
                    player_position=position,
                    need_score=need_score,
                    player_wage=player.get("wage", 10000),
                    player_contract_months_remaining=player.get("contract_months", 24),
                    is_transfer_window_open=self._is_transfer_window_open(current_season_week),
                    current_season_week=current_season_week,
                )
                
                if bid:
                    # Add player and bid details to targets
                    position_targets.append({
                        "player_id": player.get("id"),
                        "player_name": player.get("name", "Unknown"),
                        "player_ca": player.get("ca", 100),
                        "player_pa": player.get("pa", 100),
                        "player_age": player.get("age", 25),
                        "player_position": player.get("position", position),
                        "target_position": position,
                        "need_score": need_score,
                        "priority_score": bid["priority_score"],
                        "bid_amount": bid["bid_amount"],
                        "wage_offer": bid["wage_offer"],
                        "contract_length": bid["contract_length"],
                        "estimated_total_cost": bid["estimated_total_cost"],
                        "market_value": player.get("market_value", 1000000),
                    })
            
            # Sort position targets by priority score
            position_targets.sort(key=lambda x: x["priority_score"], reverse=True)
            
            # Add top targets for this position
            transfer_targets.extend(position_targets[:5])  # Top 5 per position
        
        # 3. SORT ALL TARGETS BY PRIORITY AND LIMIT
        transfer_targets.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return transfer_targets[:max_targets]
    
    def _player_can_play_position(self, player_positions: str, target_position: str) -> bool:
        """
        Check if player can play in target position.
        
        Args:
            player_positions: Player's positions (e.g., "ST/AM RL")
            target_position: Target position (e.g., "ST")
        
        Returns:
            bool: True if player can play position
        """
        if not player_positions:
            return False
        
        player_positions_upper = player_positions.upper()
        target_upper = target_position.upper()
        
        # Direct match
        if target_upper in player_positions_upper:
            return True
        
        # Position category matching
        position_categories = {
            "GK": ["GK"],
            "CB": ["CB", "D"],
            "LB": ["LB", "WB", "LWB"],
            "RB": ["RB", "WB", "RWB"],
            "WB": ["WB", "LB", "RB", "LWB", "RWB"],
            "DM": ["DM", "CM", "M"],
            "CM": ["CM", "DM", "AM", "M"],
            "AM": ["AM", "CM", "M", "LW", "RW", "W"],  # AM can play wide
            "LW": ["LW", "W", "AM", "LM"],  # LW can play AM
            "RW": ["RW", "W", "AM", "RM"],  # RW can play AM
            "ST": ["ST", "CF", "F"],
            "CF": ["CF", "ST", "F"],
        }
        
        target_categories = position_categories.get(target_upper, [target_upper])
        
        for category in target_categories:
            if category in player_positions_upper:
                return True
        
        return False
    
    def _is_transfer_window_open(self, current_week: int) -> bool:
        """
        Check if transfer window is currently open.
        
        Summer window: weeks 1-8
        Winter window: weeks 26-30
        
        Args:
            current_week: Current week of season (1-52)
        
        Returns:
            bool: True if transfer window is open
        """
        return (1 <= current_week <= 8) or (26 <= current_week <= 30)
    
    def calculate_budget_allocation(
        self,
        club_profile: ClubProfile,
        transfer_targets: List[Dict],
        max_signings: int = 5,
    ) -> Dict[str, any]:
        """
        Calculate optimal budget allocation across multiple transfer targets.
        
        Ensures club doesn't overspend and prioritizes most important signings.
        
        Args:
            club_profile: Profile of the club
            transfer_targets: List of identified transfer targets
            max_signings: Maximum number of signings to make
        
        Returns:
            Dict with budget allocation plan
        """
        total_budget = club_profile.transfer_budget
        total_wage_budget = club_profile.wage_budget
        
        # Sort targets by priority
        sorted_targets = sorted(
            transfer_targets,
            key=lambda x: x["priority_score"],
            reverse=True
        )
        
        allocated_targets = []
        remaining_budget = total_budget
        remaining_wage_budget = total_wage_budget
        
        for target in sorted_targets:
            if len(allocated_targets) >= max_signings:
                break
            
            # Check if we can afford this target
            if target["bid_amount"] <= remaining_budget:
                # Check wage budget
                annual_wage_cost = target["wage_offer"] * 52
                if annual_wage_cost <= remaining_wage_budget:
                    # Can afford both fee and wages
                    allocated_targets.append(target)
                    remaining_budget -= target["bid_amount"]
                    remaining_wage_budget -= annual_wage_cost
        
        return {
            "allocated_targets": allocated_targets,
            "total_transfer_spend": total_budget - remaining_budget,
            "total_wage_increase": total_wage_budget - remaining_wage_budget,
            "remaining_budget": remaining_budget,
            "remaining_wage_budget": remaining_wage_budget,
            "budget_utilization": ((total_budget - remaining_budget) / total_budget * 100) if total_budget > 0 else 0,
        }
    
    def evaluate_transfer_opportunity(
        self,
        club_profile: ClubProfile,
        player_ca: int,
        player_pa: int,
        player_age: int,
        player_market_value: int,
        player_wage: int,
        player_position: str,
        squad_need_score: float,
    ) -> Dict[str, any]:
        """
        Evaluate a transfer opportunity and provide recommendation.
        
        Provides detailed analysis of whether a transfer makes sense for the club.
        
        Args:
            club_profile: Profile of the club
            player_ca: Player's current ability
            player_pa: Player's potential ability
            player_age: Player's age
            player_market_value: Player's market value
            player_wage: Player's current wage
            player_position: Player's position
            squad_need_score: Squad need score for this position
        
        Returns:
            Dict with evaluation and recommendation
        """
        evaluation = {
            "recommended": False,
            "recommendation_strength": 0,  # 0-100
            "reasons": [],
            "concerns": [],
            "value_rating": 0,  # 0-100
            "fit_rating": 0,  # 0-100
        }
        
        target_ca = club_profile.reputation * 1.5
        
        # 1. QUALITY FIT EVALUATION
        ca_diff = player_ca - target_ca
        
        if ca_diff >= 20:
            evaluation["fit_rating"] += 40
            evaluation["reasons"].append("Significantly above club standard")
        elif ca_diff >= 10:
            evaluation["fit_rating"] += 30
            evaluation["reasons"].append("Above club standard")
        elif ca_diff >= 0:
            evaluation["fit_rating"] += 20
            evaluation["reasons"].append("Matches club standard")
        elif ca_diff >= -10:
            evaluation["fit_rating"] += 10
            evaluation["reasons"].append("Slightly below club standard")
        else:
            evaluation["fit_rating"] += 0
            evaluation["concerns"].append("Below club standard")
        
        # 2. POTENTIAL EVALUATION
        potential_gap = player_pa - player_ca
        
        if potential_gap >= 20 and player_age <= 23:
            evaluation["fit_rating"] += 30
            evaluation["reasons"].append("Exceptional potential for age")
        elif potential_gap >= 10 and player_age <= 25:
            evaluation["fit_rating"] += 20
            evaluation["reasons"].append("Good development potential")
        elif potential_gap < 5 and player_age >= 28:
            evaluation["concerns"].append("Limited development potential")
        
        # 3. AGE EVALUATION
        if player_age <= 23:
            evaluation["fit_rating"] += 15
            evaluation["reasons"].append("Young with resale value")
        elif player_age <= 27:
            evaluation["fit_rating"] += 10
            evaluation["reasons"].append("Prime age")
        elif player_age >= 32:
            evaluation["concerns"].append("Aging player with limited future")
        
        # 4. VALUE EVALUATION
        # Estimate fair bid
        bid = self.generate_transfer_bid(
            club_profile=club_profile,
            player_ca=player_ca,
            player_pa=player_pa,
            player_market_value=player_market_value,
            player_age=player_age,
            player_position=player_position,
            need_score=squad_need_score,
            player_wage=player_wage,
        )
        
        if bid:
            value_ratio = bid["bid_amount"] / player_market_value
            
            if value_ratio <= 0.8:
                evaluation["value_rating"] = 90
                evaluation["reasons"].append("Excellent value opportunity")
            elif value_ratio <= 0.95:
                evaluation["value_rating"] = 75
                evaluation["reasons"].append("Good value")
            elif value_ratio <= 1.1:
                evaluation["value_rating"] = 60
                evaluation["reasons"].append("Fair value")
            elif value_ratio <= 1.25:
                evaluation["value_rating"] = 40
                evaluation["concerns"].append("Slightly expensive")
            else:
                evaluation["value_rating"] = 20
                evaluation["concerns"].append("Expensive purchase")
        else:
            evaluation["value_rating"] = 0
            evaluation["concerns"].append("Not affordable")
            return evaluation
        
        # 5. NEED EVALUATION
        if squad_need_score >= 7.0:
            evaluation["fit_rating"] += 15
            evaluation["reasons"].append("Critical squad need")
        elif squad_need_score >= 5.0:
            evaluation["fit_rating"] += 10
            evaluation["reasons"].append("Important squad need")
        elif squad_need_score < 3.0:
            evaluation["concerns"].append("Low squad need")
        
        # 6. BUDGET IMPACT EVALUATION
        budget_percentage = (bid["bid_amount"] / club_profile.transfer_budget * 100) if club_profile.transfer_budget > 0 else 100
        
        if budget_percentage > 50:
            evaluation["concerns"].append(f"Uses {budget_percentage:.0f}% of transfer budget")
        elif budget_percentage > 30:
            evaluation["concerns"].append(f"Significant budget commitment ({budget_percentage:.0f}%)")
        
        # 7. FINAL RECOMMENDATION
        evaluation["fit_rating"] = min(100, evaluation["fit_rating"])
        overall_rating = (evaluation["fit_rating"] + evaluation["value_rating"]) / 2
        
        evaluation["recommendation_strength"] = int(overall_rating)
        
        if overall_rating >= 70 and squad_need_score >= 4.0:
            evaluation["recommended"] = True
        elif overall_rating >= 60 and squad_need_score >= 6.0:
            evaluation["recommended"] = True
        
        return evaluation
    
    def select_substitute_player(
        self,
        position_needed: str,
        available_substitutes: List[Tuple],  # (player_id, ca, position, stamina)
        current_score_difference: int,
        minute: int = 70,
        current_mentality: Optional[TacticMentality] = None,
        substitutions_remaining: int = 3,
    ) -> Optional[int]:
        """
        Enhanced substitute selection with tactical considerations.
        
        Considers:
        - Score situation (losing = attacking subs, winning = defensive subs)
        - Match timing (late game = more tactical flexibility)
        - Current mentality (attacking mentality = prefer attacking subs)
        - Player quality (CA) and fitness
        - Position compatibility
        - Tactical flexibility (versatile players preferred)
        
        Args:
            position_needed: Position category needed ('D', 'M', 'F')
            available_substitutes: List of available subs (player_id, ca, position, stamina)
            current_score_difference: Current goal difference
            minute: Current match minute
            current_mentality: Current team mentality
            substitutions_remaining: Number of substitutions remaining
        
        Returns:
            Optional[int]: Player ID to substitute on, or None if no suitable sub
        """
        if not available_substitutes:
            return None
        
        # Calculate tactical priority for each substitute
        sub_scores = []
        
        for player_id, ca, position, stamina in available_substitutes:
            score = float(ca)  # Base score is CA
            
            # 1. SCORE-BASED TACTICAL ADJUSTMENTS
            if current_score_difference < 0:  # Losing
                # Strongly prefer attacking players
                if self._position_matches_category(position, 'F'):
                    score += 20.0
                elif self._position_matches_category(position, 'M'):
                    score += 10.0  # Attacking midfielders also good
                
                # Late in game when losing, even more attacking
                if minute >= 75:
                    if self._position_matches_category(position, 'F'):
                        score += 15.0
            
            elif current_score_difference > 0:  # Winning
                # Prefer defensive players to protect lead
                if minute >= 75:
                    if self._position_matches_category(position, 'D'):
                        score += 15.0
                    elif self._position_matches_category(position, 'M'):
                        score += 8.0  # Defensive midfielders also good
                else:
                    # Earlier in game, still prefer quality
                    if self._position_matches_category(position, position_needed):
                        score += 10.0
            
            else:  # Drawing
                # Balanced approach, prefer position match
                if self._position_matches_category(position, position_needed):
                    score += 12.0
                
                # Slight preference for attacking players to find a winner
                if minute >= 70:
                    if self._position_matches_category(position, 'F'):
                        score += 5.0
            
            # 2. POSITION COMPATIBILITY
            # Bonus for matching the needed position
            if self._position_matches_category(position, position_needed):
                score += 8.0
            
            # 3. VERSATILITY BONUS
            # Players who can play multiple positions are more valuable
            position_upper = position.upper()
            position_count = position_upper.count('/') + 1  # Count positions
            if position_count >= 3:
                score += 5.0
            elif position_count >= 2:
                score += 3.0
            
            # 4. MENTALITY ALIGNMENT
            if current_mentality:
                if current_mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
                    # Attacking mentality: prefer attackers
                    if self._position_matches_category(position, 'F'):
                        score += 8.0
                    elif self._position_matches_category(position, 'M'):
                        score += 4.0
                
                elif current_mentality == TacticMentality.DEFENSIVE:
                    # Defensive mentality: prefer defenders
                    if self._position_matches_category(position, 'D'):
                        score += 8.0
                    elif self._position_matches_category(position, 'M'):
                        score += 4.0
            
            # 5. STAMINA CONSIDERATION
            # Prefer fresh players
            if stamina >= 95:
                score += 5.0
            elif stamina >= 90:
                score += 3.0
            elif stamina < 80:
                score -= 5.0  # Penalize tired subs
            
            # 6. SUBSTITUTION BUDGET MANAGEMENT
            # If this is the last sub, be more selective
            if substitutions_remaining == 1:
                # Prefer versatile players who can cover multiple positions
                if position_count >= 2:
                    score += 10.0
            
            sub_scores.append((player_id, score))
        
        # Select substitute with highest score
        if sub_scores:
            return max(sub_scores, key=lambda s: s[1])[0]
        
        return None
    
    def plan_substitution_strategy(
        self,
        minute: int,
        score_difference: int,
        substitutions_remaining: int,
        current_mentality: TacticMentality,
        squad_stamina_average: float,  # 0.0-1.0
    ) -> Dict[str, any]:
        """
        Plan overall substitution strategy for the match.
        
        Returns a strategy dict with:
        - target_minute: When to make next substitution
        - priority_positions: Which positions to prioritize
        - tactical_change: Whether to change mentality with subs
        
        Args:
            minute: Current match minute
            score_difference: Current goal difference
            substitutions_remaining: Number of subs remaining
            current_mentality: Current team mentality
            squad_stamina_average: Average stamina of starting 11
        
        Returns:
            Dict with substitution strategy
        """
        strategy = {
            "target_minute": 70,  # Default target
            "priority_positions": ["M", "F", "D"],  # Default priority order
            "tactical_change": None,  # New mentality if tactical sub needed
            "urgency": "normal",  # low, normal, high
        }
        
        # Adjust based on score
        if score_difference < -1:  # Losing by 2+
            strategy["target_minute"] = max(60, minute + 5)
            strategy["priority_positions"] = ["F", "M", "D"]  # Attack-focused
            strategy["urgency"] = "high"
            
            # Consider going more attacking
            if current_mentality not in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
                strategy["tactical_change"] = TacticMentality.ATTACKING
        
        elif score_difference == -1:  # Losing by 1
            strategy["target_minute"] = max(65, minute + 5)
            strategy["priority_positions"] = ["F", "M", "D"]
            strategy["urgency"] = "high" if minute >= 70 else "normal"
            
            if minute >= 70 and current_mentality == TacticMentality.BALANCED:
                strategy["tactical_change"] = TacticMentality.POSITIVE
        
        elif score_difference == 0:  # Drawing
            strategy["target_minute"] = 70
            strategy["priority_positions"] = ["M", "F", "D"]
            strategy["urgency"] = "normal"
        
        elif score_difference == 1:  # Winning by 1
            strategy["target_minute"] = 75
            strategy["priority_positions"] = ["M", "D", "F"]  # Slightly defensive
            strategy["urgency"] = "low"
            
            # Consider going more defensive late
            if minute >= 80 and current_mentality in [TacticMentality.ATTACKING, TacticMentality.VERY_ATTACKING]:
                strategy["tactical_change"] = TacticMentality.BALANCED
        
        else:  # Winning by 2+
            strategy["target_minute"] = 80
            strategy["priority_positions"] = ["D", "M", "F"]  # Defense-focused
            strategy["urgency"] = "low"
            
            if minute >= 75:
                strategy["tactical_change"] = TacticMentality.CAUTIOUS
        
        # Adjust for squad stamina
        if squad_stamina_average < 0.5:
            # Team is very tired, need subs earlier
            strategy["target_minute"] = max(60, strategy["target_minute"] - 10)
            strategy["urgency"] = "high"
        elif squad_stamina_average < 0.65:
            strategy["target_minute"] = max(65, strategy["target_minute"] - 5)
        
        # Adjust for substitutions remaining
        if substitutions_remaining == 3 and minute >= 60:
            # Have all subs, can be more liberal (but not when winning comfortably)
            if score_difference <= 1:
                strategy["target_minute"] = min(strategy["target_minute"], 65)
        elif substitutions_remaining == 1:
            # Last sub, be conservative
            strategy["target_minute"] = max(strategy["target_minute"], 75)
            strategy["urgency"] = "low"
        
        return strategy
    
    # ========================================================================
    # SQUAD ROTATION METHODS (Task 5.7)
    # ========================================================================
    
    def should_rotate_player(
        self,
        player_id: int,
        player_ca: int,
        player_fatigue: float,  # 0.0-1.0 (1.0 = fully rested, 0.0 = exhausted)
        player_morale: int,  # 0-100
        player_age: int,
        player_position: str,
        squad_average_ca: float,
        matches_in_last_week: int,
        matches_in_next_week: int,
        current_match_importance: int,  # 1-10
        next_match_importance: int,  # 1-10
        squad_depth_in_position: int,  # Number of players available in position
        is_key_player: bool = False,
        injury_history_count: int = 0,  # Number of injuries this season
        minutes_played_this_season: int = 0,
        season_week: int = 1,  # Current week of season (1-52)
    ) -> Dict[str, any]:
        """
        Comprehensive squad rotation decision for a single player.
        
        Implements intelligent rotation based on:
        1. Player fatigue levels (>70% triggers rotation consideration)
        2. Fixture congestion (multiple matches in short periods)
        3. Match importance (league vs cup matches)
        4. Player form and morale
        5. Injury risk management
        6. Squad depth and player availability
        
        Returns a dict with:
        - should_rest: bool - whether to rest the player
        - rest_probability: float - probability of resting (0.0-1.0)
        - reasons: List[str] - reasons for the decision
        - risk_factors: Dict - breakdown of risk factors
        
        Args:
            player_id: Player's ID
            player_ca: Player's current ability
            player_fatigue: Player's fatigue level (0.0-1.0, lower = more tired)
            player_morale: Player's morale (0-100)
            player_age: Player's age
            player_position: Player's position
            squad_average_ca: Squad's average CA
            matches_in_last_week: Number of matches played in last 7 days
            matches_in_next_week: Number of matches scheduled in next 7 days
            current_match_importance: Importance of current match (1-10)
            next_match_importance: Importance of next match (1-10)
            squad_depth_in_position: Number of available players in position
            is_key_player: Whether this is a key player
            injury_history_count: Number of injuries this season
            minutes_played_this_season: Total minutes played this season
            season_week: Current week of season (1-52)
        
        Returns:
            Dict with rotation decision and analysis
        """
        decision = {
            "should_rest": False,
            "rest_probability": 0.0,
            "reasons": [],
            "risk_factors": {
                "fatigue_risk": 0.0,
                "fixture_congestion_risk": 0.0,
                "injury_risk": 0.0,
                "morale_risk": 0.0,
                "age_risk": 0.0,
            },
            "considerations": [],
        }
        
        # Only rotate if we have squad depth
        if squad_depth_in_position < 2:
            decision["considerations"].append("Insufficient squad depth to rotate")
            return decision
        
        # Don't rotate non-key players in very important matches
        if current_match_importance >= 9 and not is_key_player:
            decision["considerations"].append("Very important match - playing best available")
            return decision
        
        # Calculate various risk factors
        rest_score = 0.0
        
        # 1. FATIGUE RISK ASSESSMENT
        fatigue_percentage = (1.0 - player_fatigue) * 100  # Convert to percentage (0-100)
        
        if fatigue_percentage >= 70:
            # Critical fatigue - strong rotation candidate
            rest_score += 40.0
            decision["risk_factors"]["fatigue_risk"] = 0.9
            decision["reasons"].append(f"High fatigue ({fatigue_percentage:.0f}%)")
        elif fatigue_percentage >= 50:
            # High fatigue - rotation candidate
            rest_score += 25.0
            decision["risk_factors"]["fatigue_risk"] = 0.6
            decision["reasons"].append(f"Elevated fatigue ({fatigue_percentage:.0f}%)")
        elif fatigue_percentage >= 35:
            # Moderate fatigue
            rest_score += 10.0
            decision["risk_factors"]["fatigue_risk"] = 0.3
            decision["considerations"].append(f"Moderate fatigue ({fatigue_percentage:.0f}%)")
        else:
            decision["risk_factors"]["fatigue_risk"] = 0.1
        
        # 2. FIXTURE CONGESTION ASSESSMENT
        total_recent_matches = matches_in_last_week + matches_in_next_week
        
        if total_recent_matches >= 4:
            # Severe fixture congestion (4+ matches in 2 weeks)
            rest_score += 30.0
            decision["risk_factors"]["fixture_congestion_risk"] = 0.9
            decision["reasons"].append(f"Severe fixture congestion ({total_recent_matches} matches in 2 weeks)")
        elif total_recent_matches >= 3:
            # High fixture congestion
            rest_score += 20.0
            decision["risk_factors"]["fixture_congestion_risk"] = 0.6
            decision["reasons"].append(f"High fixture congestion ({total_recent_matches} matches in 2 weeks)")
        elif total_recent_matches >= 2:
            # Moderate congestion
            rest_score += 8.0
            decision["risk_factors"]["fixture_congestion_risk"] = 0.3
            decision["considerations"].append(f"Moderate fixture congestion ({total_recent_matches} matches)")
        else:
            decision["risk_factors"]["fixture_congestion_risk"] = 0.1
        
        # 3. MATCH IMPORTANCE COMPARISON
        importance_diff = next_match_importance - current_match_importance
        
        if importance_diff >= 4:
            # Next match much more important - strong rest candidate
            rest_score += 25.0
            decision["reasons"].append(f"Next match much more important ({next_match_importance} vs {current_match_importance})")
        elif importance_diff >= 2:
            # Next match more important
            rest_score += 15.0
            decision["reasons"].append(f"Next match more important ({next_match_importance} vs {current_match_importance})")
        elif importance_diff >= 1:
            # Next match slightly more important
            rest_score += 5.0
            decision["considerations"].append("Next match slightly more important")
        elif importance_diff <= -3:
            # Current match much more important - don't rest
            rest_score -= 30.0
            decision["considerations"].append(f"Current match very important ({current_match_importance})")
        elif importance_diff <= -1:
            # Current match more important
            rest_score -= 15.0
            decision["considerations"].append(f"Current match more important ({current_match_importance})")
        
        # 4. INJURY RISK ASSESSMENT
        injury_risk = self.calculate_injury_risk(
            player_stamina=player_fatigue * 100,  # Convert to 0-100 scale
            match_intensity=0.7,  # Assume standard intensity
            player_age=player_age,
            player_injury_proneness=min(1.0, injury_history_count * 0.2),  # More injuries = more prone
        )
        
        decision["risk_factors"]["injury_risk"] = injury_risk
        
        if injury_risk >= 0.6:
            # High injury risk
            rest_score += 20.0
            decision["reasons"].append(f"High injury risk ({injury_risk:.1%})")
        elif injury_risk >= 0.4:
            # Moderate injury risk
            rest_score += 10.0
            decision["considerations"].append(f"Moderate injury risk ({injury_risk:.1%})")
        elif injury_risk >= 0.25:
            # Slight injury risk
            rest_score += 3.0
            decision["considerations"].append(f"Slight injury risk ({injury_risk:.1%})")
        
        # 5. AGE-BASED ROTATION
        if player_age >= 33:
            # Veteran players need more rest
            rest_score += 15.0
            decision["risk_factors"]["age_risk"] = 0.8
            decision["reasons"].append(f"Veteran player (age {player_age}) needs rest")
        elif player_age >= 30:
            # Older players need some rest
            rest_score += 8.0
            decision["risk_factors"]["age_risk"] = 0.5
            decision["considerations"].append(f"Older player (age {player_age})")
        elif player_age <= 21:
            # Young players can handle more matches but need development time
            rest_score -= 5.0
            decision["risk_factors"]["age_risk"] = 0.2
            decision["considerations"].append(f"Young player (age {player_age}) can handle workload")
        else:
            decision["risk_factors"]["age_risk"] = 0.1
        
        # 6. MORALE CONSIDERATIONS
        if player_morale < 40:
            # Low morale - might need playing time to improve
            rest_score -= 10.0
            decision["risk_factors"]["morale_risk"] = 0.7
            decision["considerations"].append(f"Low morale ({player_morale}) - needs playing time")
        elif player_morale < 60:
            # Moderate morale
            rest_score -= 3.0
            decision["risk_factors"]["morale_risk"] = 0.4
            decision["considerations"].append(f"Moderate morale ({player_morale})")
        else:
            decision["risk_factors"]["morale_risk"] = 0.1
        
        # 7. KEY PLAYER STATUS
        if is_key_player:
            # Key players are more important but also need rest
            if current_match_importance >= 8:
                # Very important match - key player should play
                rest_score -= 20.0
                decision["considerations"].append("Key player needed for important match")
            elif current_match_importance <= 4 and importance_diff >= 2:
                # Less important match with important match coming - rest key player
                rest_score += 10.0
                decision["considerations"].append("Key player - save for important match")
        else:
            # Non-key players easier to rotate
            rest_score += 5.0
            decision["considerations"].append("Squad player - easier to rotate")
        
        # 8. POSITION-SPECIFIC ROTATION
        # Forwards and attacking midfielders tire faster
        position_upper = player_position.upper()
        if any(p in position_upper for p in ['ST', 'CF', 'W', 'AM']):
            rest_score += 5.0
            decision["considerations"].append("Attacking position - higher workload")
        elif 'GK' in position_upper:
            # Goalkeepers rarely need rotation unless injured/fatigued
            rest_score -= 15.0
            decision["considerations"].append("Goalkeeper - less rotation needed")
        
        # 9. SEASON WORKLOAD ASSESSMENT
        # Calculate average minutes per week
        if season_week > 0:
            avg_minutes_per_week = minutes_played_this_season / season_week
            
            if avg_minutes_per_week >= 85:  # Playing almost every minute
                rest_score += 12.0
                decision["reasons"].append(f"Heavy season workload ({avg_minutes_per_week:.0f} min/week)")
            elif avg_minutes_per_week >= 70:
                rest_score += 6.0
                decision["considerations"].append(f"High season workload ({avg_minutes_per_week:.0f} min/week)")
        
        # 10. SQUAD DEPTH CONSIDERATION
        if squad_depth_in_position >= 4:
            # Excellent depth - easier to rotate
            rest_score += 8.0
            decision["considerations"].append(f"Good squad depth ({squad_depth_in_position} players)")
        elif squad_depth_in_position >= 3:
            # Good depth
            rest_score += 4.0
            decision["considerations"].append(f"Adequate squad depth ({squad_depth_in_position} players)")
        elif squad_depth_in_position == 2:
            # Minimal depth - be cautious
            rest_score -= 5.0
            decision["considerations"].append(f"Limited squad depth ({squad_depth_in_position} players)")
        
        # 11. CALCULATE FINAL REST PROBABILITY
        # Base probability from rest score (0-100 scale)
        base_probability = min(1.0, max(0.0, rest_score / 100.0))
        
        # Apply difficulty multiplier (harder AI rotates more intelligently)
        adjusted_probability = base_probability * self.difficulty_multiplier
        
        # Add some randomness to avoid predictability (±10%)
        final_probability = adjusted_probability + random.uniform(-0.1, 0.1)
        final_probability = min(1.0, max(0.0, final_probability))
        
        decision["rest_probability"] = final_probability
        
        # 12. MAKE FINAL DECISION
        # Use probability threshold
        threshold = 0.5  # 50% threshold for rotation
        
        # Adjust threshold based on match importance
        if current_match_importance >= 8:
            threshold = 0.7  # Higher threshold for important matches
        elif current_match_importance <= 3:
            threshold = 0.3  # Lower threshold for less important matches
        
        decision["should_rest"] = final_probability >= threshold
        
        if decision["should_rest"]:
            decision["reasons"].insert(0, f"Rotation recommended (probability: {final_probability:.1%})")
        else:
            decision["considerations"].insert(0, f"Continue playing (rest probability: {final_probability:.1%} below threshold)")
        
        return decision
    
    def plan_squad_rotation_for_week(
        self,
        squad_players: List[Dict],  # List of player dicts with all attributes
        upcoming_matches: List[Dict],  # List of match dicts with importance ratings
        current_week: int,
        squad_average_ca: float,
    ) -> Dict[str, any]:
        """
        Plan squad rotation strategy for an entire week of fixtures.
        
        Analyzes all upcoming matches and creates a rotation plan that:
        - Balances player workload across multiple matches
        - Prioritizes key players for important matches
        - Manages fatigue and injury risk
        - Ensures squad players get appropriate playing time
        - Maintains team chemistry and performance
        
        Args:
            squad_players: List of all squad players with attributes
            upcoming_matches: List of upcoming matches this week
            current_week: Current week of season
            squad_average_ca: Squad's average CA
        
        Returns:
            Dict with rotation plan for the week
        """
        rotation_plan = {
            "week": current_week,
            "total_matches": len(upcoming_matches),
            "player_assignments": {},  # player_id -> list of match indices to play
            "rest_recommendations": {},  # player_id -> list of match indices to rest
            "rotation_summary": {
                "players_rotated": 0,
                "total_rest_decisions": 0,
                "high_risk_players": [],
                "key_players_managed": [],
            },
            "match_lineups": {},  # match_index -> list of player_ids
        }
        
        if not upcoming_matches:
            return rotation_plan
        
        # Sort matches by importance
        sorted_matches = sorted(
            enumerate(upcoming_matches),
            key=lambda x: x[1].get("importance", 5),
            reverse=True
        )
        
        # Track player workload across the week
        player_workload = {p["id"]: 0 for p in squad_players}
        player_rest_count = {p["id"]: 0 for p in squad_players}
        
        # Analyze each player's rotation needs
        for player in squad_players:
            player_id = player["id"]
            rotation_plan["player_assignments"][player_id] = []
            rotation_plan["rest_recommendations"][player_id] = []
            
            # Determine if player is key player
            is_key = player.get("ca", 100) >= squad_average_ca + 10
            
            # Get player's position category
            position = player.get("position", "M")
            
            # Count squad depth in player's position
            squad_depth = sum(
                1 for p in squad_players
                if self._position_matches_category(p.get("position", ""), position[:2])
            )
            
            # Evaluate rotation for each match
            for match_idx, match in enumerate(upcoming_matches):
                # Determine next match importance (if exists)
                next_match_idx = match_idx + 1
                next_match_importance = 5  # Default
                if next_match_idx < len(upcoming_matches):
                    next_match_importance = upcoming_matches[next_match_idx].get("importance", 5)
                
                # Calculate matches played recently (simplified - use workload tracker)
                matches_in_last_week = player_workload[player_id]
                matches_in_next_week = len(upcoming_matches) - match_idx
                
                # Make rotation decision
                rotation_decision = self.should_rotate_player(
                    player_id=player_id,
                    player_ca=player.get("ca", 100),
                    player_fatigue=player.get("fatigue", 1.0),
                    player_morale=player.get("morale", 70),
                    player_age=player.get("age", 25),
                    player_position=position,
                    squad_average_ca=squad_average_ca,
                    matches_in_last_week=matches_in_last_week,
                    matches_in_next_week=matches_in_next_week,
                    current_match_importance=match.get("importance", 5),
                    next_match_importance=next_match_importance,
                    squad_depth_in_position=squad_depth,
                    is_key_player=is_key,
                    injury_history_count=player.get("injury_count", 0),
                    minutes_played_this_season=player.get("minutes_played", 0),
                    season_week=current_week,
                )
                
                if rotation_decision["should_rest"]:
                    # Rest this player for this match
                    rotation_plan["rest_recommendations"][player_id].append(match_idx)
                    player_rest_count[player_id] += 1
                    rotation_plan["rotation_summary"]["total_rest_decisions"] += 1
                    
                    if is_key:
                        rotation_plan["rotation_summary"]["key_players_managed"].append({
                            "player_id": player_id,
                            "player_name": player.get("name", "Unknown"),
                            "match_index": match_idx,
                            "reasons": rotation_decision["reasons"],
                        })
                else:
                    # Play this player in this match
                    rotation_plan["player_assignments"][player_id].append(match_idx)
                    player_workload[player_id] += 1
                
                # Track high-risk players
                if rotation_decision["risk_factors"]["injury_risk"] >= 0.6:
                    if player_id not in [p["player_id"] for p in rotation_plan["rotation_summary"]["high_risk_players"]]:
                        rotation_plan["rotation_summary"]["high_risk_players"].append({
                            "player_id": player_id,
                            "player_name": player.get("name", "Unknown"),
                            "injury_risk": rotation_decision["risk_factors"]["injury_risk"],
                            "fatigue_risk": rotation_decision["risk_factors"]["fatigue_risk"],
                        })
        
        # Count players rotated (players who rest at least once)
        rotation_plan["rotation_summary"]["players_rotated"] = sum(
            1 for rest_list in rotation_plan["rest_recommendations"].values()
            if len(rest_list) > 0
        )
        
        # Generate match lineups based on rotation plan
        for match_idx, match in enumerate(upcoming_matches):
            available_players = [
                p for p in squad_players
                if match_idx not in rotation_plan["rest_recommendations"].get(p["id"], [])
            ]
            
            # Select starting 11 from available players
            formation = match.get("formation", "4-4-2")
            squad_tuples = [
                (p["id"], p.get("ca", 100), p.get("position", "M"), p.get("fatigue", 1.0) * 100, p.get("morale", 70))
                for p in available_players
            ]
            
            starting_11, substitutes = self.select_starting_11(squad_tuples, formation)
            
            rotation_plan["match_lineups"][match_idx] = {
                "starting_11": starting_11,
                "substitutes": substitutes,
                "formation": formation,
                "match_importance": match.get("importance", 5),
            }
        
        return rotation_plan
    
    def evaluate_rotation_effectiveness(
        self,
        rotation_plan: Dict,
        match_results: List[Dict],  # Actual match results
        player_injuries: List[Dict],  # Injuries that occurred
        player_morale_changes: Dict[int, int],  # player_id -> morale change
    ) -> Dict[str, any]:
        """
        Evaluate the effectiveness of a rotation plan after matches are played.
        
        Analyzes:
        - Whether rotation prevented injuries
        - Impact on match results
        - Player morale changes
        - Fatigue management success
        
        Args:
            rotation_plan: The rotation plan that was executed
            match_results: Actual results of matches
            player_injuries: List of injuries that occurred
            player_morale_changes: Changes in player morale
        
        Returns:
            Dict with evaluation metrics
        """
        evaluation = {
            "rotation_success_rate": 0.0,
            "injuries_prevented": 0,
            "injuries_occurred": len(player_injuries),
            "morale_impact": {
                "positive_changes": 0,
                "negative_changes": 0,
                "neutral_changes": 0,
            },
            "match_performance": {
                "wins": 0,
                "draws": 0,
                "losses": 0,
            },
            "recommendations": [],
        }
        
        # Analyze match results
        for result in match_results:
            if result.get("result") == "win":
                evaluation["match_performance"]["wins"] += 1
            elif result.get("result") == "draw":
                evaluation["match_performance"]["draws"] += 1
            else:
                evaluation["match_performance"]["losses"] += 1
        
        # Analyze morale changes
        for player_id, morale_change in player_morale_changes.items():
            if morale_change > 5:
                evaluation["morale_impact"]["positive_changes"] += 1
            elif morale_change < -5:
                evaluation["morale_impact"]["negative_changes"] += 1
            else:
                evaluation["morale_impact"]["neutral_changes"] += 1
        
        # Estimate injuries prevented
        # Players who were rested and were high-risk
        high_risk_players_rested = 0
        for player_info in rotation_plan["rotation_summary"]["high_risk_players"]:
            player_id = player_info["player_id"]
            if len(rotation_plan["rest_recommendations"].get(player_id, [])) > 0:
                high_risk_players_rested += 1
        
        # Estimate prevented injuries (rough heuristic)
        evaluation["injuries_prevented"] = max(0, high_risk_players_rested - len(player_injuries))
        
        # Calculate success rate
        total_decisions = rotation_plan["rotation_summary"]["total_rest_decisions"]
        if total_decisions > 0:
            # Success = good match results + low injuries + positive morale
            success_score = 0.0
            
            # Match results factor (40%)
            total_matches = sum(evaluation["match_performance"].values())
            if total_matches > 0:
                win_rate = evaluation["match_performance"]["wins"] / total_matches
                success_score += win_rate * 0.4
            
            # Injury prevention factor (30%)
            if evaluation["injuries_occurred"] == 0:
                success_score += 0.3
            elif evaluation["injuries_occurred"] <= 1:
                success_score += 0.15
            
            # Morale factor (30%)
            total_morale_changes = sum(evaluation["morale_impact"].values())
            if total_morale_changes > 0:
                positive_rate = evaluation["morale_impact"]["positive_changes"] / total_morale_changes
                success_score += positive_rate * 0.3
            
            evaluation["rotation_success_rate"] = success_score
        
        # Generate recommendations
        if evaluation["injuries_occurred"] >= 2:
            evaluation["recommendations"].append("Increase rotation frequency to prevent injuries")
        
        if evaluation["morale_impact"]["negative_changes"] > evaluation["morale_impact"]["positive_changes"]:
            evaluation["recommendations"].append("Balance rotation with player morale - some players need more playing time")
        
        if evaluation["match_performance"]["losses"] > evaluation["match_performance"]["wins"]:
            evaluation["recommendations"].append("Reduce rotation in important matches to field strongest team")
        
        if evaluation["rotation_success_rate"] >= 0.7:
            evaluation["recommendations"].append("Rotation strategy is working well - continue current approach")
        
        return evaluation
