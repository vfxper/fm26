"""
Commentary Generator - Match commentary generation system

This module implements the CommentaryGenerator class which generates dynamic
match commentary for all event types with multiple variations.

Key Features:
- 5+ distinct commentary lines per event type
- Support for Russian and English languages
- Player and team name substitution
- Match context awareness (score, minute)
- Event-specific details
"""

import random
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.models.match_event import EventType, TeamSide


@dataclass
class CommentaryContext:
    """Context information for commentary generation"""
    event_type: EventType
    team: TeamSide
    player_name: str
    target_player_name: Optional[str] = None
    team_name: str = ""
    opponent_name: str = ""
    minute: int = 0
    home_score: int = 0
    away_score: int = 0
    success: bool = True
    metadata: Optional[Dict] = None


class CommentaryGenerator:
    """
    Generates dynamic match commentary for all event types.
    
    Provides at least 5 distinct commentary variations per event type
    with support for multiple languages (Russian and English).
    """
    
    def __init__(self, language: str = "en"):
        """
        Initialize commentary generator.
        
        Args:
            language: Language code ("en" for English, "ru" for Russian)
        """
        self.language = language
        self._commentary_templates = self._initialize_templates()
    
    def generate_commentary(self, context: CommentaryContext) -> str:
        """
        Generate commentary for a match event.
        
        Args:
            context: Commentary context with event details
        
        Returns:
            str: Generated commentary text
        """
        templates = self._commentary_templates.get(self.language, {}).get(
            context.event_type, []
        )
        
        if not templates:
            # Fallback to English if language not found
            templates = self._commentary_templates.get("en", {}).get(
                context.event_type, []
            )
        
        if not templates:
            return f"{context.player_name} - {context.event_type}"
        
        # Select random template
        template = random.choice(templates)
        
        # Substitute variables
        commentary = self._substitute_variables(template, context)
        
        return commentary
    
    def _substitute_variables(self, template: str, context: CommentaryContext) -> str:
        """
        Substitute variables in commentary template.
        
        Args:
            template: Commentary template with placeholders
            context: Commentary context
        
        Returns:
            str: Commentary with substituted values
        """
        substitutions = {
            "{player}": context.player_name,
            "{target_player}": context.target_player_name or "teammate",
            "{team}": context.team_name,
            "{opponent}": context.opponent_name,
            "{minute}": str(context.minute),
            "{home_score}": str(context.home_score),
            "{away_score}": str(context.away_score),
        }
        
        result = template
        for placeholder, value in substitutions.items():
            result = result.replace(placeholder, value)
        
        return result
    
    def _initialize_templates(self) -> Dict[str, Dict[EventType, List[str]]]:
        """
        Initialize commentary templates for all event types and languages.
        
        Returns:
            Dict mapping language -> event_type -> list of templates
        """
        return {
            "en": self._get_english_templates(),
            "ru": self._get_russian_templates(),
        }
    
    def _get_english_templates(self) -> Dict[EventType, List[str]]:
        """Get English commentary templates"""
        return {
            EventType.PASS: [
                "{player} plays it to {target_player}.",
                "{player} finds {target_player} with a pass.",
                "Nice ball from {player} to {target_player}.",
                "{player} threads it through to {target_player}.",
                "{player} switches play to {target_player}.",
                "{player} looks up and picks out {target_player}.",
                "Simple pass from {player} to {target_player}.",
            ],
            
            EventType.SHOT: [
                "{player} shoots! The ball flies wide.",
                "{player} tries his luck from distance!",
                "Shot from {player}! Saved by the goalkeeper!",
                "{player} unleashes a powerful strike!",
                "{player} goes for goal but it's off target.",
                "Effort from {player} but it doesn't trouble the keeper.",
                "{player} takes aim and fires!",
            ],
            
            EventType.GOAL: [
                "GOAL! {player} scores for {team}!",
                "It's in! {player} finds the back of the net!",
                "What a finish by {player}! {team} take the lead!",
                "{player} makes no mistake! Goal for {team}!",
                "Brilliant! {player} scores a fantastic goal!",
                "{player} slots it home! {home_score}-{away_score}!",
                "Clinical finish from {player}! That's a goal!",
            ],
            
            EventType.TACKLE: [
                "{player} wins the ball with a strong tackle.",
                "Good defending from {player}, he wins it cleanly.",
                "{player} times his tackle perfectly.",
                "{player} dispossesses {target_player}.",
                "Excellent tackle by {player}!",
                "{player} reads the danger and makes the tackle.",
                "{player} steps in and wins possession.",
            ],
            
            EventType.FOUL: [
                "Foul by {player}! The referee blows his whistle.",
                "{player} brings down {target_player}. Free kick.",
                "That's a foul from {player}.",
                "{player} commits a foul on {target_player}.",
                "The referee stops play. Foul by {player}.",
                "{player} goes through {target_player}. Foul given.",
                "Clumsy challenge from {player}. Free kick awarded.",
            ],
            
            EventType.YELLOW_CARD: [
                "Yellow card for {player}! He'll have to be careful now.",
                "{player} goes into the book.",
                "The referee shows {player} a yellow card.",
                "{player} is cautioned by the referee.",
                "That's a booking for {player}.",
                "Yellow card! {player} will miss the next match if he gets another.",
                "{player} receives a yellow card for that challenge.",
            ],
            
            EventType.RED_CARD: [
                "RED CARD! {player} is sent off!",
                "{player} sees red! {team} are down to 10 men!",
                "Straight red card for {player}! He has to go!",
                "The referee shows {player} a red card! He's off!",
                "{player} is dismissed! What a moment!",
                "Red card! {player} leaves his team with 10 men!",
                "{player} is sent off! {team} in trouble now!",
            ],
            
            EventType.CORNER: [
                "Corner kick for {team}.",
                "{player} wins a corner for his team.",
                "Corner to {team}. {player} will take it.",
                "The ball goes out for a corner. {team} have a chance here.",
                "Corner kick. {player} prepares to deliver.",
                "{team} have a corner. Can they make it count?",
                "Corner to {team}. Dangerous opportunity.",
            ],
            
            EventType.FREE_KICK: [
                "Free kick to {team} in a dangerous position.",
                "{player} stands over the free kick.",
                "Free kick for {team}. {player} will take it.",
                "{team} have a free kick. Good opportunity here.",
                "Free kick awarded to {team}. {player} lines it up.",
                "{player} prepares to take the free kick.",
                "Promising free kick for {team}.",
            ],
            
            EventType.PENALTY: [
                "PENALTY! The referee points to the spot!",
                "Penalty to {team}! Big moment in the match!",
                "It's a penalty! {player} will take it.",
                "Penalty kick! {team} have a golden opportunity!",
                "The referee awards a penalty to {team}!",
                "Spot kick! {player} steps up to take it.",
                "Penalty! This could be crucial!",
            ],
            
            EventType.SAVE: [
                "Great save by {player}!",
                "{player} denies the striker with a brilliant save!",
                "What a stop from {player}!",
                "{player} gets down well to make the save.",
                "Superb goalkeeping from {player}!",
                "{player} keeps it out! Excellent save!",
                "{player} reacts quickly to make the save.",
            ],
            
            EventType.SUBSTITUTION: [
                "Substitution for {team}. {player} comes on.",
                "{team} make a change. {player} enters the game.",
                "{player} is brought on by {team}.",
                "Fresh legs for {team}. {player} comes on.",
                "{team} make a substitution. {player} is on.",
                "{player} replaces {target_player} for {team}.",
                "Tactical change from {team}. {player} comes on.",
            ],
            
            EventType.INJURY: [
                "{player} is down injured. The physio is on.",
                "Concern for {player}. He's receiving treatment.",
                "{player} needs medical attention.",
                "The game stops as {player} is injured.",
                "{player} is hurt. The medical team rush on.",
                "Injury to {player}. This doesn't look good.",
                "{player} is down. The physio is checking him.",
            ],
            
            EventType.OFFSIDE: [
                "Offside! {player} was too eager.",
                "The flag is up. {player} was offside.",
                "{player} strayed offside. Good call from the linesman.",
                "Offside against {player}.",
                "{player} was in an offside position.",
                "The assistant referee flags for offside. {player} was off.",
                "Offside. {player} mistimed his run.",
            ],
            
            EventType.BLOCK: [
                "{player} blocks the shot! Brave defending!",
                "Blocked by {player}! He throws his body in the way!",
                "{player} gets in the way and blocks it.",
                "Important block from {player}!",
                "{player} denies the shot with a block.",
                "Crucial intervention from {player}! Blocked!",
                "{player} puts his body on the line to block that.",
            ],
            
            EventType.INTERCEPTION: [
                "{player} reads it well and intercepts.",
                "Good anticipation from {player}. He cuts it out.",
                "{player} intercepts the pass.",
                "Excellent reading of the game by {player}.",
                "{player} steps in and intercepts.",
                "{player} sniffs out the danger and intercepts.",
                "Smart play from {player}. He intercepts the ball.",
            ],
            
            EventType.CLEARANCE: [
                "{player} clears the danger.",
                "{player} hoofs it away under pressure.",
                "Clearance from {player}. Safety first.",
                "{player} gets it away. {team} clear their lines.",
                "{player} deals with the danger and clears.",
                "No nonsense from {player}. He clears it.",
                "{player} boots it clear.",
            ],
            
            EventType.CROSS: [
                "{player} whips in a cross!",
                "Cross from {player} into the box!",
                "{player} delivers from the wing!",
                "{player} sends it into the danger area!",
                "Dangerous cross from {player}!",
                "{player} looks up and crosses!",
                "{player} swings it in!",
            ],
            
            EventType.DRIBBLE: [
                "{player} takes on his man!",
                "{player} dribbles past {target_player}!",
                "Great skill from {player}!",
                "{player} beats his marker with ease!",
                "{player} shows quick feet!",
                "{player} dances past the defender!",
                "Brilliant dribbling from {player}!",
            ],
            
            EventType.HEADER: [
                "{player} wins the header!",
                "Header from {player}!",
                "{player} gets up well to head it!",
                "Good header by {player}!",
                "{player} attacks the ball with his head!",
                "{player} rises highest to head it!",
                "Powerful header from {player}!",
            ],
            
            EventType.THROW_IN: [
                "Throw-in to {team}.",
                "{player} will take the throw-in.",
                "Throw-in for {team}.",
                "{team} have a throw-in.",
                "{player} prepares to take the throw.",
                "Throw-in awarded to {team}.",
                "{player} takes the throw-in.",
            ],
            
            EventType.GOAL_KICK: [
                "Goal kick to {team}.",
                "{player} will take the goal kick.",
                "Goal kick for {team}.",
                "{team} have a goal kick.",
                "{player} prepares to take the goal kick.",
                "Goal kick awarded to {team}.",
                "{player} takes the goal kick.",
            ],
        }
    
    def _get_russian_templates(self) -> Dict[EventType, List[str]]:
        """Get Russian commentary templates"""
        return {
            EventType.PASS: [
                "{player} отдаёт пас {target_player}.",
                "{player} находит {target_player} передачей.",
                "Хороший пас от {player} к {target_player}.",
                "{player} прорезает оборону, пас на {target_player}.",
                "{player} переводит игру на {target_player}.",
                "{player} смотрит вперёд и выбирает {target_player}.",
                "Простой пас от {player} к {target_player}.",
            ],
            
            EventType.SHOT: [
                "{player} бьёт! Мяч летит мимо ворот.",
                "{player} пробует издалека!",
                "Удар от {player}! Вратарь спасает!",
                "{player} наносит мощный удар!",
                "{player} бьёт по воротам, но мимо.",
                "Попытка {player}, но вратарь не в опасности.",
                "{player} целится и бьёт!",
            ],
            
            EventType.GOAL: [
                "ГОЛ! {player} забивает за {team}!",
                "Мяч в воротах! {player} поражает цель!",
                "Какой финиш от {player}! {team} выходят вперёд!",
                "{player} не ошибается! Гол для {team}!",
                "Блестяще! {player} забивает фантастический гол!",
                "{player} отправляет мяч в сетку! {home_score}-{away_score}!",
                "Клинический удар от {player}! Это гол!",
            ],
            
            EventType.TACKLE: [
                "{player} отбирает мяч сильным подкатом.",
                "Хорошая защита от {player}, он выигрывает мяч чисто.",
                "{player} идеально рассчитывает подкат.",
                "{player} отбирает мяч у {target_player}.",
                "Отличный подкат от {player}!",
                "{player} читает опасность и делает подкат.",
                "{player} вступает в борьбу и выигрывает мяч.",
            ],
            
            EventType.FOUL: [
                "Фол от {player}! Судья свистит.",
                "{player} сбивает {target_player}. Штрафной.",
                "Это фол от {player}.",
                "{player} фолит на {target_player}.",
                "Судья останавливает игру. Фол от {player}.",
                "{player} проходит через {target_player}. Фол назначен.",
                "Неуклюжая попытка от {player}. Штрафной назначен.",
            ],
            
            EventType.YELLOW_CARD: [
                "Жёлтая карточка для {player}! Теперь он должен быть осторожен.",
                "{player} получает предупреждение.",
                "Судья показывает {player} жёлтую карточку.",
                "{player} предупреждён судьёй.",
                "Это предупреждение для {player}.",
                "Жёлтая карточка! {player} пропустит следующий матч при повторном нарушении.",
                "{player} получает жёлтую карточку за этот подкат.",
            ],
            
            EventType.RED_CARD: [
                "КРАСНАЯ КАРТОЧКА! {player} удалён!",
                "{player} видит красную! {team} остаются в меньшинстве!",
                "Прямая красная карточка для {player}! Он должен уйти!",
                "Судья показывает {player} красную карточку! Он удалён!",
                "{player} дисквалифицирован! Какой момент!",
                "Красная карточка! {player} оставляет команду вдесятером!",
                "{player} удалён! {team} в беде!",
            ],
            
            EventType.CORNER: [
                "Угловой для {team}.",
                "{player} выигрывает угловой для своей команды.",
                "Угловой в пользу {team}. {player} будет исполнять.",
                "Мяч уходит на угловой. У {team} есть шанс.",
                "Угловой. {player} готовится подать.",
                "{team} получают угловой. Смогут ли они использовать?",
                "Угловой для {team}. Опасная возможность.",
            ],
            
            EventType.FREE_KICK: [
                "Штрафной для {team} в опасной позиции.",
                "{player} стоит над штрафным.",
                "Штрафной для {team}. {player} будет исполнять.",
                "{team} получают штрафной. Хорошая возможность.",
                "Штрафной назначен {team}. {player} готовится.",
                "{player} готовится исполнить штрафной.",
                "Перспективный штрафной для {team}.",
            ],
            
            EventType.PENALTY: [
                "ПЕНАЛЬТИ! Судья указывает на точку!",
                "Пенальти для {team}! Важный момент в матче!",
                "Это пенальти! {player} будет исполнять.",
                "Одиннадцатиметровый! У {team} золотая возможность!",
                "Судья назначает пенальти в пользу {team}!",
                "Удар с точки! {player} выходит исполнять.",
                "Пенальти! Это может быть решающим!",
            ],
            
            EventType.SAVE: [
                "Отличный сейв от {player}!",
                "{player} отражает удар блестящим сейвом!",
                "Какая остановка от {player}!",
                "{player} хорошо ложится и делает сейв.",
                "Превосходная работа вратаря от {player}!",
                "{player} не пропускает! Отличный сейв!",
                "{player} быстро реагирует и делает сейв.",
            ],
            
            EventType.SUBSTITUTION: [
                "Замена в {team}. {player} выходит на поле.",
                "{team} делают замену. {player} входит в игру.",
                "{player} выпущен {team}.",
                "Свежие силы для {team}. {player} выходит.",
                "{team} делают замену. {player} на поле.",
                "{player} заменяет {target_player} в {team}.",
                "Тактическая замена от {team}. {player} выходит.",
            ],
            
            EventType.INJURY: [
                "{player} лежит травмированный. Врач выходит.",
                "Беспокойство за {player}. Он получает лечение.",
                "{player} нуждается в медицинской помощи.",
                "Игра останавливается, так как {player} травмирован.",
                "{player} травмирован. Медицинская команда спешит.",
                "Травма {player}. Это выглядит нехорошо.",
                "{player} лежит. Врач проверяет его.",
            ],
            
            EventType.OFFSIDE: [
                "Офсайд! {player} был слишком нетерпелив.",
                "Флаг поднят. {player} был в офсайде.",
                "{player} оказался в офсайде. Правильное решение лайнсмена.",
                "Офсайд против {player}.",
                "{player} был в положении офсайда.",
                "Помощник судьи фиксирует офсайд. {player} был вне игры.",
                "Офсайд. {player} не рассчитал время выхода.",
            ],
            
            EventType.BLOCK: [
                "{player} блокирует удар! Храбрая защита!",
                "Заблокировано {player}! Он бросает тело на пути!",
                "{player} встаёт на пути и блокирует.",
                "Важный блок от {player}!",
                "{player} отражает удар блоком.",
                "Решающее вмешательство от {player}! Заблокировано!",
                "{player} жертвует телом, чтобы заблокировать это.",
            ],
            
            EventType.INTERCEPTION: [
                "{player} хорошо читает и перехватывает.",
                "Хорошее предвидение от {player}. Он перерезает.",
                "{player} перехватывает пас.",
                "Отличное чтение игры от {player}.",
                "{player} вступает и перехватывает.",
                "{player} чувствует опасность и перехватывает.",
                "Умная игра от {player}. Он перехватывает мяч.",
            ],
            
            EventType.CLEARANCE: [
                "{player} устраняет опасность.",
                "{player} выбивает под давлением.",
                "Вынос от {player}. Безопасность прежде всего.",
                "{player} убирает. {team} очищают линии.",
                "{player} справляется с опасностью и выносит.",
                "Без церемоний от {player}. Он выносит.",
                "{player} выбивает подальше.",
            ],
            
            EventType.CROSS: [
                "{player} навешивает!",
                "Навес от {player} в штрафную!",
                "{player} подаёт с фланга!",
                "{player} посылает в опасную зону!",
                "Опасный навес от {player}!",
                "{player} смотрит вперёд и навешивает!",
                "{player} закручивает!",
            ],
            
            EventType.DRIBBLE: [
                "{player} обыгрывает соперника!",
                "{player} проходит мимо {target_player}!",
                "Отличная техника от {player}!",
                "{player} легко обходит защитника!",
                "{player} показывает быстрые ноги!",
                "{player} танцует мимо защитника!",
                "Блестящий дриблинг от {player}!",
            ],
            
            EventType.HEADER: [
                "{player} выигрывает верховую!",
                "Удар головой от {player}!",
                "{player} хорошо прыгает и бьёт головой!",
                "Хороший удар головой от {player}!",
                "{player} атакует мяч головой!",
                "{player} выше всех и бьёт головой!",
                "Мощный удар головой от {player}!",
            ],
            
            EventType.THROW_IN: [
                "Вбрасывание для {team}.",
                "{player} будет вбрасывать.",
                "Вбрасывание в пользу {team}.",
                "{team} получают вбрасывание.",
                "{player} готовится вбросить.",
                "Вбрасывание назначено {team}.",
                "{player} вбрасывает.",
            ],
            
            EventType.GOAL_KICK: [
                "Удар от ворот для {team}.",
                "{player} будет бить от ворот.",
                "Удар от ворот в пользу {team}.",
                "{team} получают удар от ворот.",
                "{player} готовится бить от ворот.",
                "Удар от ворот назначен {team}.",
                "{player} бьёт от ворот.",
            ],
        }


def generate_commentary_for_event(
    event_type: EventType,
    team: TeamSide,
    player_name: str,
    team_name: str = "",
    opponent_name: str = "",
    target_player_name: Optional[str] = None,
    minute: int = 0,
    home_score: int = 0,
    away_score: int = 0,
    success: bool = True,
    metadata: Optional[Dict] = None,
    language: str = "en"
) -> str:
    """
    Convenience function to generate commentary for an event.
    
    Args:
        event_type: Type of event
        team: Team that performed the event
        player_name: Name of the player
        team_name: Name of the team
        opponent_name: Name of the opponent team
        target_player_name: Name of the target player (optional)
        minute: Match minute
        home_score: Home team score
        away_score: Away team score
        success: Whether the event was successful
        metadata: Additional event metadata
        language: Language code ("en" or "ru")
    
    Returns:
        str: Generated commentary text
    """
    generator = CommentaryGenerator(language=language)
    context = CommentaryContext(
        event_type=event_type,
        team=team,
        player_name=player_name,
        target_player_name=target_player_name,
        team_name=team_name,
        opponent_name=opponent_name,
        minute=minute,
        home_score=home_score,
        away_score=away_score,
        success=success,
        metadata=metadata
    )
    return generator.generate_commentary(context)
