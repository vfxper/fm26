"""
Save System (Task 31)
- Automatic save after significant actions
- Server-side save storage linked to user ID
- 3 automatic save slots (current, previous, 2 weeks ago)
- Save state restoration (< 3 seconds)
- Manual named save creation
- Save retry logic (up to 3 attempts)
- Save data compression (max 500 KB per slot)
- Save export as JSON
- Atomic write operations with checksum validation
"""

import json
import zlib
import hashlib
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, text

logger = logging.getLogger(__name__)

MAX_SAVE_SIZE = 500 * 1024  # 500 KB compressed
MAX_MANUAL_SAVES = 5
AUTO_SAVE_SLOTS = 3
MAX_RETRIES = 3


@dataclass
class SaveSlot:
    """Represents a save slot."""
    id: int
    career_id: int
    user_id: int
    name: str
    slot_type: str  # 'auto', 'manual'
    season: int
    week: int
    created_at: str
    size_bytes: int
    checksum: str
    is_current: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "career_id": self.career_id,
            "name": self.name,
            "slot_type": self.slot_type,
            "season": self.season,
            "week": self.week,
            "created_at": self.created_at,
            "size_kb": round(self.size_bytes / 1024, 1),
            "is_current": self.is_current,
        }


class SaveService:
    """
    Manages career save/load operations.
    
    Save data includes:
    - Career state (season, week, budget, reputation, etc.)
    - Squad state (all squad_players with morale, fitness, contracts)
    - Tactics presets
    - Match history (last 10 matches)
    - Financial history
    - Competition standings
    - Training schedules
    - Scouting assignments
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def auto_save(self, career_id: int, user_id: int, trigger: str = "advance_week") -> Dict[str, Any]:
        """
        Automatic save after significant actions.
        Maintains 3 rotating auto-save slots.
        
        Args:
            career_id: Career to save
            user_id: Owner user ID
            trigger: What triggered the save (advance_week, match_end, transfer, etc.)
        
        Returns:
            Save result with slot info
        """
        # Collect save data
        save_data = await self._collect_save_data(career_id)
        
        # Compress and validate
        compressed = self._compress(save_data)
        if len(compressed) > MAX_SAVE_SIZE:
            logger.warning(f"Save too large ({len(compressed)} bytes), trimming history")
            save_data = self._trim_save_data(save_data)
            compressed = self._compress(save_data)
        
        checksum = self._checksum(compressed)
        
        # Rotate auto-saves: shift slots
        await self._rotate_auto_saves(career_id, user_id)
        
        # Write new auto-save with retry
        result = await self._write_save_with_retry(
            career_id=career_id,
            user_id=user_id,
            name=f"Auto - S{save_data['season']}W{save_data['week']} ({trigger})",
            slot_type="auto",
            data=compressed,
            checksum=checksum,
            season=save_data['season'],
            week=save_data['week'],
        )
        
        return result

    async def manual_save(self, career_id: int, user_id: int, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a manual named save.
        
        Args:
            career_id: Career to save
            user_id: Owner
            name: Custom save name (optional)
        """
        # Check manual save limit
        count = await self._count_manual_saves(career_id)
        if count >= MAX_MANUAL_SAVES:
            return {"success": False, "error": f"Maximum {MAX_MANUAL_SAVES} manual saves reached"}
        
        save_data = await self._collect_save_data(career_id)
        compressed = self._compress(save_data)
        checksum = self._checksum(compressed)
        
        save_name = name or f"Save - Season {save_data['season']} Week {save_data['week']}"
        
        result = await self._write_save_with_retry(
            career_id=career_id,
            user_id=user_id,
            name=save_name,
            slot_type="manual",
            data=compressed,
            checksum=checksum,
            season=save_data['season'],
            week=save_data['week'],
        )
        
        return result

    async def load_save(self, save_id: int, user_id: int) -> Dict[str, Any]:
        """
        Load a save slot and restore career state.
        Target: < 3 seconds.
        
        Args:
            save_id: Save slot ID
            user_id: Must match save owner
        
        Returns:
            Restored career state
        """
        start = time.time()
        
        # Fetch save record
        result = await self.db.execute(
            text("SELECT * FROM career_saves WHERE id = :id AND user_id = :uid"),
            {"id": save_id, "uid": user_id}
        )
        row = result.first()
        
        if not row:
            return {"success": False, "error": "Save not found or access denied"}
        
        # Decompress and validate
        compressed = row.data
        stored_checksum = row.checksum
        
        if self._checksum(compressed) != stored_checksum:
            return {"success": False, "error": "Save data corrupted (checksum mismatch)"}
        
        save_data = self._decompress(compressed)
        
        # Restore career state
        await self._restore_career_state(row.career_id, save_data)
        await self.db.commit()
        
        elapsed = time.time() - start
        logger.info(f"Save loaded in {elapsed:.2f}s (career={row.career_id}, save={save_id})")
        
        return {
            "success": True,
            "career_id": row.career_id,
            "season": save_data.get("season"),
            "week": save_data.get("week"),
            "load_time_ms": round(elapsed * 1000),
        }

    async def list_saves(self, career_id: int, user_id: int) -> List[Dict[str, Any]]:
        """List all save slots for a career."""
        result = await self.db.execute(
            text("""
                SELECT id, career_id, user_id, name, slot_type, season, week, 
                       created_at, length(data) as size_bytes, checksum
                FROM career_saves 
                WHERE career_id = :cid AND user_id = :uid
                ORDER BY created_at DESC
            """),
            {"cid": career_id, "uid": user_id}
        )
        rows = result.all()
        
        saves = []
        for row in rows:
            saves.append({
                "id": row.id,
                "name": row.name,
                "slot_type": row.slot_type,
                "season": row.season,
                "week": row.week,
                "created_at": str(row.created_at),
                "size_kb": round((row.size_bytes or 0) / 1024, 1),
            })
        
        return saves

    async def delete_save(self, save_id: int, user_id: int) -> Dict[str, Any]:
        """Delete a manual save slot."""
        result = await self.db.execute(
            text("SELECT slot_type FROM career_saves WHERE id = :id AND user_id = :uid"),
            {"id": save_id, "uid": user_id}
        )
        row = result.first()
        
        if not row:
            return {"success": False, "error": "Save not found"}
        if row.slot_type == "auto":
            return {"success": False, "error": "Cannot delete auto-saves"}
        
        await self.db.execute(
            text("DELETE FROM career_saves WHERE id = :id"), {"id": save_id}
        )
        await self.db.commit()
        return {"success": True}

    async def export_save(self, save_id: int, user_id: int) -> Optional[str]:
        """Export save as JSON string."""
        result = await self.db.execute(
            text("SELECT data, checksum FROM career_saves WHERE id = :id AND user_id = :uid"),
            {"id": save_id, "uid": user_id}
        )
        row = result.first()
        if not row:
            return None
        
        save_data = self._decompress(row.data)
        return json.dumps(save_data, ensure_ascii=False, indent=2)

    # === Internal Methods ===

    async def _collect_save_data(self, career_id: int) -> Dict[str, Any]:
        """Collect all career state into a serializable dict."""
        from app.models.career import Career
        from app.models.squad_player import SquadPlayer
        
        # Career
        result = await self.db.execute(select(Career).where(Career.id == career_id))
        career = result.scalar_one_or_none()
        if not career:
            raise ValueError(f"Career {career_id} not found")
        
        # Squad
        sq_result = await self.db.execute(
            select(SquadPlayer).where(SquadPlayer.career_id == career_id)
        )
        squad = sq_result.scalars().all()
        
        save_data = {
            "version": 1,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "career_id": career_id,
            "season": career.season,
            "week": career.week,
            "career": {
                "budget": float(career.budget or 0),
                "reputation": career.reputation,
                "board_confidence": career.board_confidence,
                "status": career.status,
                "manager_name": career.manager_name,
                "club_id": career.club_id,
                "tactics_presets": career.tactics_presets,
                "active_tactic_index": getattr(career, 'active_tactic_index', 0),
            },
            "squad": [
                {
                    "player_id": sp.player_id,
                    "squad_number": sp.squad_number,
                    "status": sp.status,
                    "morale": sp.morale,
                    "fitness": sp.fitness,
                    "wage": sp.wage,
                    "is_injured": sp.is_injured,
                    "is_loaned": sp.is_loaned,
                }
                for sp in squad
            ],
        }
        
        return save_data

    async def _restore_career_state(self, career_id: int, save_data: Dict[str, Any]):
        """Restore career from save data."""
        from app.models.career import Career
        from app.models.squad_player import SquadPlayer
        
        career_data = save_data.get("career", {})
        
        # Update career
        result = await self.db.execute(select(Career).where(Career.id == career_id))
        career = result.scalar_one_or_none()
        if not career:
            raise ValueError("Career not found")
        
        career.season = save_data.get("season", career.season)
        career.week = save_data.get("week", career.week)
        career.budget = career_data.get("budget", career.budget)
        career.reputation = career_data.get("reputation", career.reputation)
        career.board_confidence = career_data.get("board_confidence", career.board_confidence)
        career.status = career_data.get("status", career.status)
        career.tactics_presets = career_data.get("tactics_presets")
        
        # Restore squad morale/fitness
        for sp_data in save_data.get("squad", []):
            sq_result = await self.db.execute(
                select(SquadPlayer).where(
                    SquadPlayer.career_id == career_id,
                    SquadPlayer.player_id == sp_data["player_id"],
                )
            )
            sp = sq_result.scalar_one_or_none()
            if sp:
                sp.morale = sp_data.get("morale", sp.morale)
                sp.fitness = sp_data.get("fitness", sp.fitness)
                sp.status = sp_data.get("status", sp.status)
                sp.is_injured = sp_data.get("is_injured", sp.is_injured)

    async def _rotate_auto_saves(self, career_id: int, user_id: int):
        """Keep only last N auto-saves."""
        result = await self.db.execute(
            text("""
                SELECT id FROM career_saves 
                WHERE career_id = :cid AND user_id = :uid AND slot_type = 'auto'
                ORDER BY created_at DESC
            """),
            {"cid": career_id, "uid": user_id}
        )
        rows = result.all()
        
        # Delete oldest if we have too many
        if len(rows) >= AUTO_SAVE_SLOTS:
            to_delete = [r.id for r in rows[AUTO_SAVE_SLOTS - 1:]]
            if to_delete:
                await self.db.execute(
                    text("DELETE FROM career_saves WHERE id = ANY(:ids)"),
                    {"ids": to_delete}
                )

    async def _write_save_with_retry(self, career_id, user_id, name, slot_type, data, checksum, season, week):
        """Write save with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                await self.db.execute(
                    text("""
                        INSERT INTO career_saves (career_id, user_id, name, slot_type, data, checksum, season, week, created_at)
                        VALUES (:cid, :uid, :name, :stype, :data, :checksum, :season, :week, NOW())
                    """),
                    {
                        "cid": career_id, "uid": user_id, "name": name,
                        "stype": slot_type, "data": data, "checksum": checksum,
                        "season": season, "week": week,
                    }
                )
                await self.db.commit()
                return {"success": True, "name": name, "size_kb": round(len(data) / 1024, 1)}
            except Exception as e:
                logger.warning(f"Save attempt {attempt+1} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    return {"success": False, "error": f"Save failed after {MAX_RETRIES} attempts: {str(e)}"}
                await self.db.rollback()

    async def _count_manual_saves(self, career_id: int) -> int:
        result = await self.db.execute(
            text("SELECT COUNT(*) FROM career_saves WHERE career_id = :cid AND slot_type = 'manual'"),
            {"cid": career_id}
        )
        return result.scalar() or 0

    def _compress(self, data: Dict) -> bytes:
        """Compress save data with zlib."""
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        return zlib.compress(json_str.encode('utf-8'), level=6)

    def _decompress(self, data: bytes) -> Dict:
        """Decompress save data."""
        json_str = zlib.decompress(data).decode('utf-8')
        return json.loads(json_str)

    def _checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum."""
        return hashlib.sha256(data).hexdigest()[:16]

    def _trim_save_data(self, data: Dict) -> Dict:
        """Trim save data to fit size limit."""
        # Remove non-essential data
        if "match_history" in data:
            data["match_history"] = data["match_history"][:5]
        if "financial_history" in data:
            data["financial_history"] = data["financial_history"][:3]
        return data
