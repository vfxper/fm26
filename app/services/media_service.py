"""
Media Service - Press conferences, media events, and reputation management.

This module implements the media interaction system for the football manager game:
- Pre-match and post-match press conferences (16.1)
- Multiple-choice response system with 3+ options (16.2)
- Morale and reputation impact calculation (16.3)
- Media pressure event simulation (16.4)
- Media reputation score management (1-100) (16.5)
- Player interview event generation (16.6)
- Board scrutiny triggers when reputation < 30 (16.7)
- News feed display (16.8)
- Press conference localization (Russian/English) (16.9)
- Rival manager comment system (16.10)
"""

import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career import Career
from app.models.media_event import MediaEvent, MediaEventType, MediaEventStatus

logger = logging.getLogger(__name__)


# --- Press Conference Templates (16.9 Localization) ---

PRESS_CONFERENCE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "pre_match": {
        "questions": {
            "en": [
                "How do you rate your chances in the upcoming match?",
                "What's your game plan for tomorrow's fixture?",
                "Are there any injury concerns ahead of the match?",
                "How important is this match for the season?",
                "What do you expect from the opposition?",
            ],
            "ru": [
                "Как вы оцениваете шансы в предстоящем матче?",
                "Какой план на завтрашнюю игру?",
                "Есть ли проблемы с травмами перед матчем?",
                "Насколько важен этот матч для сезона?",
                "Чего вы ожидаете от соперника?",
            ],
        },
        "responses": {
            "confident": {
                "en": "We're fully prepared and confident we can win.",
                "ru": "Мы полностью готовы и уверены в победе.",
                "morale_impact": 3,
                "reputation_impact": 1,
                "tone": "confident",
            },
            "cautious": {
                "en": "We respect the opposition but believe in our quality.",
                "ru": "Мы уважаем соперника, но верим в свои силы.",
                "morale_impact": 1,
                "reputation_impact": 0,
                "tone": "cautious",
            },
            "deflective": {
                "en": "I'd rather focus on our own preparation than predictions.",
                "ru": "Я предпочитаю сосредоточиться на подготовке, а не на прогнозах.",
                "morale_impact": 0,
                "reputation_impact": -1,
                "tone": "deflective",
            },
            "aggressive": {
                "en": "We're going out there to dominate from the first minute.",
                "ru": "Мы выйдем доминировать с первой минуты.",
                "morale_impact": 4,
                "reputation_impact": 2,
                "tone": "aggressive",
            },
        },
    },
    "post_match_win": {
        "questions": {
            "en": [
                "How pleased are you with today's result?",
                "What was the key to your success today?",
                "Any standout performers you'd like to highlight?",
                "Where does this result leave you in the title race?",
            ],
            "ru": [
                "Насколько вы довольны сегодняшним результатом?",
                "Что стало ключом к успеху сегодня?",
                "Кого бы вы выделили из игроков?",
                "Как этот результат влияет на борьбу за титул?",
            ],
        },
        "responses": {
            "humble": {
                "en": "The players deserve all the credit. They executed the plan perfectly.",
                "ru": "Игроки заслуживают всех похвал. Они идеально выполнили план.",
                "morale_impact": 3,
                "reputation_impact": 2,
                "tone": "humble",
            },
            "proud": {
                "en": "This is what we've been working towards. A fantastic performance.",
                "ru": "Это то, к чему мы стремились. Фантастическое выступление.",
                "morale_impact": 4,
                "reputation_impact": 1,
                "tone": "proud",
            },
            "demanding": {
                "en": "Good result, but there's still room for improvement.",
                "ru": "Хороший результат, но есть ещё над чем работать.",
                "morale_impact": 1,
                "reputation_impact": 1,
                "tone": "demanding",
            },
        },
    },
    "post_match_loss": {
        "questions": {
            "en": [
                "What went wrong today?",
                "Are you concerned about the team's form?",
                "Do you feel your position is under threat?",
                "What changes will you make going forward?",
            ],
            "ru": [
                "Что пошло не так сегодня?",
                "Вас беспокоит форма команды?",
                "Чувствуете ли вы угрозу своей позиции?",
                "Какие изменения вы внесёте в будущем?",
            ],
        },
        "responses": {
            "defiant": {
                "en": "We'll bounce back. I have full faith in this squad.",
                "ru": "Мы вернёмся. Я полностью верю в эту команду.",
                "morale_impact": 2,
                "reputation_impact": 1,
                "tone": "defiant",
            },
            "apologetic": {
                "en": "The fans deserve better. I take full responsibility.",
                "ru": "Болельщики заслуживают лучшего. Я беру ответственность на себя.",
                "morale_impact": -1,
                "reputation_impact": 2,
                "tone": "apologetic",
            },
            "blaming": {
                "en": "The referee's decisions didn't help us today.",
                "ru": "Решения арбитра не помогли нам сегодня.",
                "morale_impact": 0,
                "reputation_impact": -3,
                "tone": "blaming",
            },
            "analytical": {
                "en": "We need to analyze what went wrong and fix it in training.",
                "ru": "Нам нужно проанализировать ошибки и исправить их на тренировках.",
                "morale_impact": 1,
                "reputation_impact": 0,
                "tone": "analytical",
            },
        },
    },
    "post_match_draw": {
        "questions": {
            "en": [
                "Are you satisfied with a point today?",
                "Did the team do enough to win?",
                "How do you assess the overall performance?",
            ],
            "ru": [
                "Вы довольны одним очком сегодня?",
                "Команда сделала достаточно для победы?",
                "Как вы оцениваете общую игру?",
            ],
        },
        "responses": {
            "positive": {
                "en": "A point away from home is always valuable.",
                "ru": "Очко на выезде всегда ценно.",
                "morale_impact": 1,
                "reputation_impact": 0,
                "tone": "positive",
            },
            "frustrated": {
                "en": "We should have won that. Two points dropped.",
                "ru": "Мы должны были выиграть. Потеряли два очка.",
                "morale_impact": -1,
                "reputation_impact": 0,
                "tone": "frustrated",
            },
            "pragmatic": {
                "en": "It's a fair result given how the game played out.",
                "ru": "Справедливый результат, учитывая ход игры.",
                "morale_impact": 0,
                "reputation_impact": 1,
                "tone": "pragmatic",
            },
        },
    },
}


# --- Player Interview Templates (16.6) ---

PLAYER_INTERVIEW_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "happy_player": {
        "questions": {
            "en": [
                "Your player spoke positively about the club. How do you respond?",
                "A player praised your management style in an interview.",
            ],
            "ru": [
                "Ваш игрок положительно отозвался о клубе. Как вы ответите?",
                "Игрок похвалил ваш стиль управления в интервью.",
            ],
        },
        "responses": {
            "grateful": {
                "en": "It's great to hear. We have a fantastic group here.",
                "ru": "Приятно слышать. У нас отличная группа.",
                "morale_impact": 2,
                "reputation_impact": 1,
                "tone": "grateful",
            },
            "deflect": {
                "en": "The focus should be on the team, not individuals.",
                "ru": "Фокус должен быть на команде, а не на отдельных игроках.",
                "morale_impact": 0,
                "reputation_impact": 0,
                "tone": "deflect",
            },
            "praise_back": {
                "en": "He's been outstanding. A true professional.",
                "ru": "Он был великолепен. Настоящий профессионал.",
                "morale_impact": 4,
                "reputation_impact": 1,
                "tone": "praise_back",
            },
        },
    },
    "unhappy_player": {
        "questions": {
            "en": [
                "A player has expressed frustration about lack of playing time.",
                "Your player told the media he wants to leave the club.",
            ],
            "ru": [
                "Игрок выразил недовольство нехваткой игрового времени.",
                "Ваш игрок заявил СМИ, что хочет покинуть клуб.",
            ],
        },
        "responses": {
            "firm": {
                "en": "Squad matters are handled internally, not through the press.",
                "ru": "Вопросы состава решаются внутри команды, а не через прессу.",
                "morale_impact": -2,
                "reputation_impact": 2,
                "tone": "firm",
            },
            "sympathetic": {
                "en": "I understand his frustration. We'll find a solution.",
                "ru": "Я понимаю его разочарование. Мы найдём решение.",
                "morale_impact": 1,
                "reputation_impact": 0,
                "tone": "sympathetic",
            },
            "dismissive": {
                "en": "He needs to earn his place like everyone else.",
                "ru": "Он должен заслужить место, как и все остальные.",
                "morale_impact": -3,
                "reputation_impact": -1,
                "tone": "dismissive",
            },
        },
    },
    "transfer_rumour": {
        "questions": {
            "en": [
                "There are rumours linking your star player with a move. Comment?",
                "A player's agent has been speaking to other clubs publicly.",
            ],
            "ru": [
                "Ходят слухи о переходе вашего ключевого игрока. Комментарий?",
                "Агент игрока публично общался с другими клубами.",
            ],
        },
        "responses": {
            "deny": {
                "en": "There's nothing in it. He's committed to this club.",
                "ru": "Ничего подобного. Он предан клубу.",
                "morale_impact": 1,
                "reputation_impact": 0,
                "tone": "deny",
            },
            "open": {
                "en": "Every player has a price. We'll see what happens.",
                "ru": "У каждого игрока есть цена. Посмотрим, что будет.",
                "morale_impact": -2,
                "reputation_impact": 1,
                "tone": "open",
            },
            "angry": {
                "en": "Agents should keep their mouths shut. It's disrespectful.",
                "ru": "Агенты должны молчать. Это неуважение.",
                "morale_impact": 0,
                "reputation_impact": -2,
                "tone": "angry",
            },
        },
    },
}


# --- Rival Manager Comment Templates (16.10) ---

RIVAL_COMMENT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "pre_match_taunt": {
        "comments": {
            "en": [
                "Their manager thinks they can compete with us? Let's see on the pitch.",
                "I've studied their tactics. I'm not impressed.",
                "We're the better team. Simple as that.",
            ],
            "ru": [
                "Их тренер думает, что может с нами конкурировать? Посмотрим на поле.",
                "Я изучил их тактику. Не впечатлён.",
                "Мы лучшая команда. Всё просто.",
            ],
        },
        "responses": {
            "ignore": {
                "en": "I don't waste time on mind games. We focus on ourselves.",
                "ru": "Я не трачу время на психологические игры. Мы сосредоточены на себе.",
                "morale_impact": 1,
                "reputation_impact": 1,
                "tone": "ignore",
            },
            "fire_back": {
                "en": "Talk is cheap. We'll let our football do the talking.",
                "ru": "Слова ничего не стоят. Наш футбол скажет всё сам.",
                "morale_impact": 3,
                "reputation_impact": 0,
                "tone": "fire_back",
            },
            "agree": {
                "en": "They're a strong side. It'll be a tough game for both teams.",
                "ru": "Они сильная команда. Будет тяжёлая игра для обеих сторон.",
                "morale_impact": -1,
                "reputation_impact": -1,
                "tone": "agree",
            },
        },
    },
    "post_match_gloat": {
        "comments": {
            "en": [
                "We showed today who the real contenders are.",
                "I told you we'd win. They weren't ready for us.",
            ],
            "ru": [
                "Мы показали сегодня, кто настоящие претенденты.",
                "Я говорил, что мы победим. Они не были готовы.",
            ],
        },
        "responses": {
            "gracious": {
                "en": "Credit to them today. We'll learn from this.",
                "ru": "Отдаю им должное. Мы извлечём уроки.",
                "morale_impact": 0,
                "reputation_impact": 2,
                "tone": "gracious",
            },
            "defiant": {
                "en": "One result doesn't define a season. We'll meet again.",
                "ru": "Один результат не определяет сезон. Мы ещё встретимся.",
                "morale_impact": 2,
                "reputation_impact": 1,
                "tone": "defiant",
            },
            "bitter": {
                "en": "Easy to talk when the decisions go your way.",
                "ru": "Легко говорить, когда решения в вашу пользу.",
                "morale_impact": -1,
                "reputation_impact": -2,
                "tone": "bitter",
            },
        },
    },
}


# --- Media Pressure Templates (16.4) ---

MEDIA_PRESSURE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "losing_streak": {
        "questions": {
            "en": [
                "Your team has lost {losses} in a row. Is your job safe?",
                "Fans are calling for change after {losses} consecutive defeats.",
            ],
            "ru": [
                "Ваша команда проиграла {losses} подряд. Ваша работа в безопасности?",
                "Болельщики требуют перемен после {losses} поражений подряд.",
            ],
        },
        "responses": {
            "defiant": {
                "en": "I'm the right man for this job. Results will come.",
                "ru": "Я подходящий человек для этой работы. Результаты придут.",
                "morale_impact": 2,
                "reputation_impact": 1,
                "tone": "defiant",
            },
            "humble": {
                "en": "I understand the frustration. We're working hard to turn it around.",
                "ru": "Я понимаю разочарование. Мы усердно работаем над исправлением.",
                "morale_impact": 1,
                "reputation_impact": 2,
                "tone": "humble",
            },
            "deflect": {
                "en": "The table doesn't lie, but there's a long way to go.",
                "ru": "Таблица не врёт, но впереди ещё долгий путь.",
                "morale_impact": 0,
                "reputation_impact": -1,
                "tone": "deflect",
            },
        },
    },
    "relegation_battle": {
        "questions": {
            "en": [
                "Your team is in the relegation zone. What's your message to the fans?",
                "Can you save this club from relegation?",
            ],
            "ru": [
                "Ваша команда в зоне вылета. Что скажете болельщикам?",
                "Сможете ли вы спасти клуб от вылета?",
            ],
        },
        "responses": {
            "fighting": {
                "en": "We will fight until the very last day. I guarantee it.",
                "ru": "Мы будем бороться до последнего дня. Гарантирую.",
                "morale_impact": 3,
                "reputation_impact": 1,
                "tone": "fighting",
            },
            "realistic": {
                "en": "It's a difficult situation, but mathematically we can still survive.",
                "ru": "Ситуация сложная, но математически мы ещё можем спастись.",
                "morale_impact": 0,
                "reputation_impact": 0,
                "tone": "realistic",
            },
            "blame_squad": {
                "en": "Some players need to look at themselves. Not everyone is pulling their weight.",
                "ru": "Некоторым игрокам нужно посмотреть на себя. Не все выкладываются.",
                "morale_impact": -4,
                "reputation_impact": -2,
                "tone": "blame_squad",
            },
        },
    },
}



# --- Board Scrutiny Messages (16.7) ---

BOARD_SCRUTINY_MESSAGES: Dict[str, List[str]] = {
    "en": [
        "The board is concerned about the club's public image.",
        "Board members have expressed displeasure with recent media coverage.",
        "Your media reputation is damaging the club. The board demands improvement.",
        "Sponsors are unhappy with the negative press. The board is watching closely.",
    ],
    "ru": [
        "Совет директоров обеспокоен публичным имиджем клуба.",
        "Члены совета выразили недовольство последним освещением в СМИ.",
        "Ваша медийная репутация вредит клубу. Совет требует улучшений.",
        "Спонсоры недовольны негативной прессой. Совет внимательно следит.",
    ],
}


class MediaServiceError(Exception):
    """Base exception for media service errors."""
    pass


class ConferenceNotFoundError(MediaServiceError):
    """Raised when a press conference event is not found."""
    pass


class CareerNotFoundError(MediaServiceError):
    """Raised when a career is not found."""
    pass


class InvalidResponseError(MediaServiceError):
    """Raised when an invalid response choice is made."""
    pass


class MediaService:
    """
    Service for managing media interactions in the football manager game.

    Handles press conferences, player interviews, media pressure events,
    reputation management, board scrutiny, news feeds, and rival comments.

    Example:
        >>> service = MediaService(session)
        >>> conference = await service.generate_press_conference(
        ...     career_id=1, match_id=5, conference_type="pre_match"
        ... )
        >>> result = await service.respond_to_press_conference(
        ...     career_id=1, conference_id=conference["id"], choice_index=0
        ... )
    """

    # Board scrutiny threshold
    BOARD_SCRUTINY_THRESHOLD = 30

    def __init__(self, session: AsyncSession):
        """
        Initialize the media service.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    # --- 16.1: Pre-match and Post-match Press Conferences ---

    async def generate_press_conference(
        self,
        career_id: int,
        match_id: Optional[int] = None,
        conference_type: str = "pre_match",
        match_result: Optional[str] = None,
        locale: str = "en",
    ) -> Dict[str, Any]:
        """
        Generate a press conference event with multiple response options.

        Args:
            career_id: ID of the career
            match_id: Optional match ID for match-related conferences
            conference_type: Type of conference ('pre_match', 'post_match')
            match_result: Match result for post-match ('win', 'loss', 'draw')
            locale: Language locale ('en' or 'ru')

        Returns:
            Dict with conference details including question and response options

        Raises:
            CareerNotFoundError: If career doesn't exist
            MediaServiceError: If invalid conference type
        """
        career = await self._get_career(career_id)
        if not career:
            raise CareerNotFoundError(f"Career {career_id} not found")

        # Determine template key
        if conference_type == "pre_match":
            template_key = "pre_match"
            event_type = MediaEventType.PRE_MATCH_CONFERENCE
        elif conference_type == "post_match":
            if match_result == "win":
                template_key = "post_match_win"
            elif match_result == "loss":
                template_key = "post_match_loss"
            else:
                template_key = "post_match_draw"
            event_type = MediaEventType.POST_MATCH_CONFERENCE
        else:
            raise MediaServiceError(f"Invalid conference type: {conference_type}")

        template = PRESS_CONFERENCE_TEMPLATES[template_key]
        questions = template["questions"].get(locale, template["questions"]["en"])
        question = random.choice(questions)

        # Build response options (3+ options guaranteed by templates)
        responses = template["responses"]
        response_options = []
        for key, resp_data in responses.items():
            response_options.append({
                "key": key,
                "text": resp_data.get(locale, resp_data["en"]),
                "tone": resp_data["tone"],
                "morale_impact": resp_data["morale_impact"],
                "reputation_impact": resp_data["reputation_impact"],
            })

        # Create the media event
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(hours=24)

        event = MediaEvent(
            career_id=career_id,
            match_id=match_id,
            event_type=event_type,
            event_question=question,
            response_options=json.dumps(response_options),
            event_status=MediaEventStatus.PENDING,
            reputation_impact=0,
            board_confidence_impact=0,
            event_date=now,
            expiry_date=expiry,
            event_context=json.dumps({
                "conference_type": conference_type,
                "match_result": match_result,
                "locale": locale,
            }),
        )

        self.session.add(event)
        await self.session.flush()

        logger.info(
            f"Generated {conference_type} press conference for career {career_id}, "
            f"event_id={event.id}"
        )

        return {
            "id": event.id,
            "type": conference_type,
            "event_type": event_type.value,
            "question": question,
            "response_options": response_options,
            "expiry_date": expiry.isoformat(),
            "locale": locale,
        }

    # --- 16.2: Multiple-choice Response System ---

    async def respond_to_press_conference(
        self,
        career_id: int,
        conference_id: int,
        choice_index: int,
    ) -> Dict[str, Any]:
        """
        Process the manager's response to a press conference.

        Args:
            career_id: ID of the career
            conference_id: ID of the media event (press conference)
            choice_index: Index of the chosen response (0-based)

        Returns:
            Dict with impact results (morale change, reputation change)

        Raises:
            ConferenceNotFoundError: If conference not found
            InvalidResponseError: If choice_index is out of range
            MediaServiceError: If conference already responded or expired
        """
        # Fetch the event
        result = await self.session.execute(
            select(MediaEvent).where(
                MediaEvent.id == conference_id,
                MediaEvent.career_id == career_id,
            )
        )
        event = result.scalar_one_or_none()

        if not event:
            raise ConferenceNotFoundError(
                f"Conference {conference_id} not found for career {career_id}"
            )

        if event.event_status == MediaEventStatus.RESPONDED:
            raise MediaServiceError("Conference already responded to")

        if event.event_status == MediaEventStatus.EXPIRED:
            raise MediaServiceError("Conference has expired")

        # Parse response options
        options = json.loads(event.response_options)
        if choice_index < 0 or choice_index >= len(options):
            raise InvalidResponseError(
                f"Invalid choice index {choice_index}. "
                f"Must be 0-{len(options) - 1}"
            )

        chosen = options[choice_index]

        # Calculate impact
        impact = self.calculate_response_impact(
            response_type=chosen["tone"],
            context={
                "event_type": event.event_type.value,
                "morale_impact": chosen["morale_impact"],
                "reputation_impact": chosen["reputation_impact"],
            },
        )

        # Update the event
        now = datetime.now(timezone.utc)
        event.selected_response = choice_index
        event.response_date = now
        event.event_status = MediaEventStatus.RESPONDED
        event.reputation_impact = max(-10, min(10, impact["reputation_change"]))
        event.board_confidence_impact = max(-10, min(10, impact.get("board_confidence_change", 0)))
        event.morale_impact = json.dumps({"team_morale_change": impact["morale_change"]})

        # Update career reputation
        career = await self._get_career(career_id)
        if career:
            await self.update_media_reputation(career_id, impact["reputation_change"])

        await self.session.flush()

        logger.info(
            f"Career {career_id} responded to conference {conference_id} "
            f"with choice {choice_index} (tone={chosen['tone']})"
        )

        return {
            "conference_id": conference_id,
            "chosen_response": chosen,
            "impact": impact,
        }

    # --- 16.3: Morale and Reputation Impact Calculation ---

    def calculate_response_impact(
        self,
        response_type: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate the morale and reputation impact of a media response.

        The impact is based on:
        - Base morale/reputation values from the response template
        - Context modifiers (event type, current form, etc.)

        Args:
            response_type: The tone/type of the response
            context: Additional context for impact calculation

        Returns:
            Dict with morale_change, reputation_change, board_confidence_change
        """
        base_morale = context.get("morale_impact", 0)
        base_reputation = context.get("reputation_impact", 0)

        # Context modifiers
        event_type = context.get("event_type", "")
        modifier = 1.0

        # Post-match loss responses have amplified negative effects
        if event_type == MediaEventType.POST_MATCH_CONFERENCE.value:
            if response_type in ("blaming", "bitter", "blame_squad"):
                modifier = 1.5
            elif response_type in ("apologetic", "gracious"):
                modifier = 1.2

        # Media pressure responses have amplified effects
        if event_type == MediaEventType.MEDIA_PRESSURE.value:
            modifier = 1.3

        morale_change = int(base_morale * modifier)
        reputation_change = int(base_reputation * modifier)

        # Board confidence is influenced by reputation changes
        board_confidence_change = 0
        if reputation_change >= 2:
            board_confidence_change = 1
        elif reputation_change <= -2:
            board_confidence_change = -1

        return {
            "morale_change": morale_change,
            "reputation_change": reputation_change,
            "board_confidence_change": board_confidence_change,
            "response_type": response_type,
            "modifier": modifier,
        }

    # --- 16.4: Media Pressure Event Simulation ---

    async def simulate_media_pressure(
        self,
        career_id: int,
        season: int,
        week: int,
        locale: str = "en",
    ) -> Optional[Dict[str, Any]]:
        """
        Simulate media pressure events based on career results and form.

        Pressure events are generated when:
        - Team is on a losing streak (3+ losses)
        - Team is in relegation zone
        - Manager reputation is low

        Args:
            career_id: ID of the career
            season: Current season number
            week: Current week number
            locale: Language locale

        Returns:
            Dict with pressure event details, or None if no pressure generated
        """
        career = await self._get_career(career_id)
        if not career:
            raise CareerNotFoundError(f"Career {career_id} not found")

        # Determine if pressure event should be generated
        pressure_type = None
        context_data: Dict[str, Any] = {}

        # Check losing streak (based on recent losses)
        total_matches = career.get_total_matches()
        if total_matches > 0:
            loss_ratio = career.matches_lost / total_matches
            if loss_ratio > 0.6 and total_matches >= 5:
                pressure_type = "losing_streak"
                context_data["losses"] = career.matches_lost

        # Check low reputation
        if career.manager_reputation < 30:
            pressure_type = "relegation_battle"

        # Random chance of pressure event (10% per week if no specific trigger)
        if pressure_type is None and random.random() < 0.10:
            pressure_type = random.choice(["losing_streak", "relegation_battle"])
            context_data["losses"] = random.randint(3, 5)

        if pressure_type is None:
            return None

        # Generate the pressure event
        template = MEDIA_PRESSURE_TEMPLATES[pressure_type]
        questions = template["questions"].get(locale, template["questions"]["en"])
        question = random.choice(questions)

        # Format question with context
        if "{losses}" in question:
            question = question.format(losses=context_data.get("losses", 3))

        # Build response options
        responses = template["responses"]
        response_options = []
        for key, resp_data in responses.items():
            text = resp_data.get(locale, resp_data["en"])
            response_options.append({
                "key": key,
                "text": text,
                "tone": resp_data["tone"],
                "morale_impact": resp_data["morale_impact"],
                "reputation_impact": resp_data["reputation_impact"],
            })

        # Create media event
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(hours=48)

        event = MediaEvent(
            career_id=career_id,
            event_type=MediaEventType.MEDIA_PRESSURE,
            event_question=question,
            response_options=json.dumps(response_options),
            event_status=MediaEventStatus.PENDING,
            reputation_impact=0,
            board_confidence_impact=0,
            event_date=now,
            expiry_date=expiry,
            event_context=json.dumps({
                "pressure_type": pressure_type,
                "season": season,
                "week": week,
                "locale": locale,
                **context_data,
            }),
        )

        self.session.add(event)
        await self.session.flush()

        logger.info(
            f"Generated media pressure event ({pressure_type}) for career {career_id}"
        )

        return {
            "id": event.id,
            "pressure_type": pressure_type,
            "question": question,
            "response_options": response_options,
            "expiry_date": expiry.isoformat(),
        }


    # --- 16.5: Media Reputation Score (1-100) ---

    async def get_media_reputation(self, career_id: int) -> int:
        """
        Get the current media reputation score for a career.

        Args:
            career_id: ID of the career

        Returns:
            int: Current reputation score (1-100)

        Raises:
            CareerNotFoundError: If career doesn't exist
        """
        career = await self._get_career(career_id)
        if not career:
            raise CareerNotFoundError(f"Career {career_id} not found")
        return career.manager_reputation

    async def update_media_reputation(
        self, career_id: int, change: int
    ) -> Dict[str, Any]:
        """
        Update the media reputation score for a career.

        The score is clamped to the range 1-100.

        Args:
            career_id: ID of the career
            change: Amount to change reputation by (positive or negative)

        Returns:
            Dict with old_reputation, new_reputation, change_applied

        Raises:
            CareerNotFoundError: If career doesn't exist
        """
        career = await self._get_career(career_id)
        if not career:
            raise CareerNotFoundError(f"Career {career_id} not found")

        old_reputation = career.manager_reputation
        new_reputation = max(1, min(100, old_reputation + change))
        career.manager_reputation = new_reputation

        await self.session.flush()

        logger.info(
            f"Career {career_id} reputation: {old_reputation} -> {new_reputation} "
            f"(change={change})"
        )

        return {
            "old_reputation": old_reputation,
            "new_reputation": new_reputation,
            "change_applied": new_reputation - old_reputation,
        }

    # --- 16.6: Player Interview Event Generation ---

    async def generate_player_interview(
        self,
        career_id: int,
        player_id: int,
        interview_type: Optional[str] = None,
        locale: str = "en",
    ) -> Dict[str, Any]:
        """
        Generate a player interview event requiring manager response.

        Args:
            career_id: ID of the career
            player_id: ID of the player being interviewed
            interview_type: Type of interview ('happy_player', 'unhappy_player',
                          'transfer_rumour'). Random if not specified.
            locale: Language locale

        Returns:
            Dict with interview event details

        Raises:
            CareerNotFoundError: If career doesn't exist
        """
        career = await self._get_career(career_id)
        if not career:
            raise CareerNotFoundError(f"Career {career_id} not found")

        # Select interview type
        if interview_type is None:
            interview_type = random.choice(list(PLAYER_INTERVIEW_TEMPLATES.keys()))

        if interview_type not in PLAYER_INTERVIEW_TEMPLATES:
            raise MediaServiceError(f"Invalid interview type: {interview_type}")

        template = PLAYER_INTERVIEW_TEMPLATES[interview_type]
        questions = template["questions"].get(locale, template["questions"]["en"])
        question = random.choice(questions)

        # Build response options
        responses = template["responses"]
        response_options = []
        for key, resp_data in responses.items():
            response_options.append({
                "key": key,
                "text": resp_data.get(locale, resp_data["en"]),
                "tone": resp_data["tone"],
                "morale_impact": resp_data["morale_impact"],
                "reputation_impact": resp_data["reputation_impact"],
            })

        # Create media event
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(hours=48)

        event = MediaEvent(
            career_id=career_id,
            event_type=MediaEventType.PLAYER_INTERVIEW,
            event_question=question,
            response_options=json.dumps(response_options),
            event_status=MediaEventStatus.PENDING,
            reputation_impact=0,
            board_confidence_impact=0,
            related_player_id=player_id,
            event_date=now,
            expiry_date=expiry,
            event_context=json.dumps({
                "interview_type": interview_type,
                "player_id": player_id,
                "locale": locale,
            }),
        )

        self.session.add(event)
        await self.session.flush()

        logger.info(
            f"Generated player interview ({interview_type}) for career {career_id}, "
            f"player {player_id}"
        )

        return {
            "id": event.id,
            "interview_type": interview_type,
            "player_id": player_id,
            "question": question,
            "response_options": response_options,
            "expiry_date": expiry.isoformat(),
        }

    # --- 16.7: Board Scrutiny Triggers ---

    async def check_board_scrutiny(
        self,
        career_id: int,
        locale: str = "en",
    ) -> Optional[Dict[str, Any]]:
        """
        Check if board scrutiny should be triggered based on reputation.

        Board scrutiny is triggered when manager_reputation < 30.

        Args:
            career_id: ID of the career
            locale: Language locale

        Returns:
            Dict with scrutiny warning details, or None if no scrutiny triggered
        """
        career = await self._get_career(career_id)
        if not career:
            raise CareerNotFoundError(f"Career {career_id} not found")

        if career.manager_reputation >= self.BOARD_SCRUTINY_THRESHOLD:
            return None

        # Board scrutiny triggered
        messages = BOARD_SCRUTINY_MESSAGES.get(locale, BOARD_SCRUTINY_MESSAGES["en"])
        message = random.choice(messages)

        # Determine severity
        reputation = career.manager_reputation
        if reputation < 10:
            severity = "critical"
            board_impact = -3
        elif reputation < 20:
            severity = "severe"
            board_impact = -2
        else:
            severity = "warning"
            board_impact = -1

        # Apply board confidence impact
        old_confidence = career.board_confidence
        new_confidence = max(1, career.board_confidence + board_impact)
        career.board_confidence = new_confidence

        await self.session.flush()

        logger.warning(
            f"Board scrutiny triggered for career {career_id}: "
            f"reputation={reputation}, severity={severity}"
        )

        return {
            "triggered": True,
            "severity": severity,
            "message": message,
            "reputation": reputation,
            "board_confidence_change": board_impact,
            "old_board_confidence": old_confidence,
            "new_board_confidence": new_confidence,
        }

    # --- 16.8: News Feed Display ---

    async def get_news_feed(
        self,
        career_id: int,
        limit: int = 20,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get the news feed for a career (recent media events).

        Args:
            career_id: ID of the career
            limit: Maximum number of events to return (default 20)
            event_type: Optional filter by event type

        Returns:
            List of media event dicts ordered by date (newest first)
        """
        query = (
            select(MediaEvent)
            .where(MediaEvent.career_id == career_id)
            .order_by(desc(MediaEvent.event_date))
            .limit(limit)
        )

        if event_type:
            try:
                type_enum = MediaEventType(event_type)
                query = query.where(MediaEvent.event_type == type_enum)
            except ValueError:
                pass  # Ignore invalid event type filter

        result = await self.session.execute(query)
        events = result.scalars().all()

        feed = []
        for event in events:
            options = json.loads(event.response_options) if event.response_options else []
            feed.append({
                "id": event.id,
                "event_type": event.event_type.value,
                "question": event.event_question,
                "status": event.event_status.value,
                "selected_response": event.selected_response,
                "response_options": options,
                "reputation_impact": event.reputation_impact,
                "board_confidence_impact": event.board_confidence_impact,
                "event_date": event.event_date.isoformat() if event.event_date else None,
                "response_date": (
                    event.response_date.isoformat() if event.response_date else None
                ),
                "related_player_id": event.related_player_id,
                "related_club_id": event.related_club_id,
            })

        return feed

    # --- 16.10: Rival Manager Comment System ---

    async def generate_rival_manager_comment(
        self,
        career_id: int,
        match_id: Optional[int] = None,
        comment_type: Optional[str] = None,
        rival_club_id: Optional[int] = None,
        locale: str = "en",
    ) -> Dict[str, Any]:
        """
        Generate a rival manager comment event.

        Args:
            career_id: ID of the career
            match_id: Optional match ID
            comment_type: Type of comment ('pre_match_taunt', 'post_match_gloat').
                         Random if not specified.
            rival_club_id: Optional rival club ID
            locale: Language locale

        Returns:
            Dict with rival comment event details
        """
        career = await self._get_career(career_id)
        if not career:
            raise CareerNotFoundError(f"Career {career_id} not found")

        if comment_type is None:
            comment_type = random.choice(list(RIVAL_COMMENT_TEMPLATES.keys()))

        if comment_type not in RIVAL_COMMENT_TEMPLATES:
            raise MediaServiceError(f"Invalid comment type: {comment_type}")

        template = RIVAL_COMMENT_TEMPLATES[comment_type]
        comments = template["comments"].get(locale, template["comments"]["en"])
        rival_comment = random.choice(comments)

        # Build response options
        responses = template["responses"]
        response_options = []
        for key, resp_data in responses.items():
            response_options.append({
                "key": key,
                "text": resp_data.get(locale, resp_data["en"]),
                "tone": resp_data["tone"],
                "morale_impact": resp_data["morale_impact"],
                "reputation_impact": resp_data["reputation_impact"],
            })

        # Create media event
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(hours=72)

        event = MediaEvent(
            career_id=career_id,
            match_id=match_id,
            event_type=MediaEventType.RIVAL_COMMENT,
            event_question=rival_comment,
            response_options=json.dumps(response_options),
            event_status=MediaEventStatus.PENDING,
            reputation_impact=0,
            board_confidence_impact=0,
            related_club_id=rival_club_id,
            event_date=now,
            expiry_date=expiry,
            event_context=json.dumps({
                "comment_type": comment_type,
                "rival_club_id": rival_club_id,
                "locale": locale,
            }),
        )

        self.session.add(event)
        await self.session.flush()

        logger.info(
            f"Generated rival comment ({comment_type}) for career {career_id}"
        )

        return {
            "id": event.id,
            "comment_type": comment_type,
            "rival_comment": rival_comment,
            "response_options": response_options,
            "rival_club_id": rival_club_id,
            "expiry_date": expiry.isoformat(),
        }

    # --- Private Helpers ---

    async def _get_career(self, career_id: int) -> Optional[Career]:
        """Fetch a career by ID."""
        result = await self.session.execute(
            select(Career).where(Career.id == career_id)
        )
        return result.scalar_one_or_none()
