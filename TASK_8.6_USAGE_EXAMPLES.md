# Task 8.6: Player Listing System - Usage Examples

## Overview
This document provides practical examples of how to use the player listing system in the Telegram Football Manager application.

## Basic Usage

### 1. Listing a Player for Sale

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.transfer_service import TransferService
from app.models.squad_player import SquadPlayer

async def list_player_for_sale(
    session: AsyncSession,
    career_id: int,
    player_id: int,
    asking_price: int
) -> dict:
    """
    List a player for sale with an asking price.
    
    Args:
        session: Database session
        career_id: ID of the career (manager's save)
        player_id: ID of the player to list
        asking_price: Asking price in currency units
    
    Returns:
        Dictionary with listing result
    """
    # Get the squad player
    result = await session.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career_id,
            SquadPlayer.player_id == player_id
        )
    )
    squad_player = result.scalar_one_or_none()
    
    if not squad_player:
        return {"success": False, "error": "Player not in squad"}
    
    # Create transfer service
    service = TransferService()
    
    # Validate listing
    is_valid, error_msg = service.validate_player_listing(squad_player, asking_price)
    if not is_valid:
        return {"success": False, "error": error_msg}
    
    # List the player
    try:
        listing_result = service.list_player_for_sale(squad_player, asking_price)
        
        # Persist to database
        await session.commit()
        
        return {
            "success": True,
            "listing": listing_result
        }
    except ValueError as e:
        await session.rollback()
        return {"success": False, "error": str(e)}
```

### 2. Unlisting a Player

```python
async def unlist_player(
    session: AsyncSession,
    career_id: int,
    player_id: int
) -> dict:
    """
    Remove a player from sale listing.
    
    Args:
        session: Database session
        career_id: ID of the career
        player_id: ID of the player to unlist
    
    Returns:
        Dictionary with unlisting result
    """
    # Get the squad player
    result = await session.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career_id,
            SquadPlayer.player_id == player_id
        )
    )
    squad_player = result.scalar_one_or_none()
    
    if not squad_player:
        return {"success": False, "error": "Player not in squad"}
    
    # Create transfer service
    service = TransferService()
    
    # Unlist the player
    unlisting_result = service.unlist_player_from_sale(squad_player)
    
    # Persist to database
    await session.commit()
    
    return {
        "success": True,
        "result": unlisting_result
    }
```

### 3. Getting All Listed Players

```python
async def get_listed_players_for_career(
    session: AsyncSession,
    career_id: int
) -> list:
    """
    Get all players currently listed for sale in a career.
    
    Args:
        session: Database session
        career_id: ID of the career
    
    Returns:
        List of dictionaries with player and listing details
    """
    # Query all squad players for this career
    result = await session.execute(
        select(SquadPlayer)
        .where(SquadPlayer.career_id == career_id)
        .where(SquadPlayer.is_listed_for_sale == True)
    )
    listed_players = result.scalars().all()
    
    # Format response with player details
    return [
        {
            "player_id": sp.player_id,
            "squad_number": sp.squad_number,
            "asking_price": sp.asking_price,
            "wage": sp.wage,
            "squad_status": sp.squad_status.value,
            "morale": sp.morale,
        }
        for sp in listed_players
    ]
```

### 4. Getting Listing Details for a Specific Player

```python
async def get_player_listing_details(
    session: AsyncSession,
    career_id: int,
    player_id: int
) -> dict:
    """
    Get listing details for a specific player.
    
    Args:
        session: Database session
        career_id: ID of the career
        player_id: ID of the player
    
    Returns:
        Dictionary with listing details or None if not listed
    """
    # Get the squad player
    result = await session.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career_id,
            SquadPlayer.player_id == player_id
        )
    )
    squad_player = result.scalar_one_or_none()
    
    if not squad_player:
        return {"success": False, "error": "Player not in squad"}
    
    # Create transfer service
    service = TransferService()
    
    # Get listing details
    details = service.get_listing_details(squad_player)
    
    if details:
        return {
            "success": True,
            "listed": True,
            "details": details
        }
    else:
        return {
            "success": True,
            "listed": False,
            "details": None
        }
```

## API Endpoint Examples

### FastAPI Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.services.transfer_service import TransferService

router = APIRouter(prefix="/api/careers/{career_id}/transfers", tags=["transfers"])


class ListPlayerRequest(BaseModel):
    """Request model for listing a player"""
    player_id: int = Field(..., description="ID of the player to list")
    asking_price: int = Field(..., ge=0, description="Asking price (must be non-negative)")


class ListPlayerResponse(BaseModel):
    """Response model for listing a player"""
    success: bool
    message: str
    listing: dict | None = None


@router.post("/list", response_model=ListPlayerResponse)
async def list_player_for_sale_endpoint(
    career_id: int,
    request: ListPlayerRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    List a player for sale with an asking price.
    
    - **career_id**: ID of the career (from path)
    - **player_id**: ID of the player to list
    - **asking_price**: Asking price for the player (must be >= 0)
    """
    # Get squad player
    result = await session.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career_id,
            SquadPlayer.player_id == request.player_id
        )
    )
    squad_player = result.scalar_one_or_none()
    
    if not squad_player:
        raise HTTPException(status_code=404, detail="Player not in squad")
    
    # Create service
    service = TransferService()
    
    # Validate
    is_valid, error_msg = service.validate_player_listing(
        squad_player, request.asking_price
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # List player
    try:
        listing_result = service.list_player_for_sale(
            squad_player, request.asking_price
        )
        await session.commit()
        
        return ListPlayerResponse(
            success=True,
            message="Player listed for sale successfully",
            listing=listing_result
        )
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/unlist/{player_id}")
async def unlist_player_endpoint(
    career_id: int,
    player_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Remove a player from sale listing.
    
    - **career_id**: ID of the career (from path)
    - **player_id**: ID of the player to unlist
    """
    # Get squad player
    result = await session.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career_id,
            SquadPlayer.player_id == player_id
        )
    )
    squad_player = result.scalar_one_or_none()
    
    if not squad_player:
        raise HTTPException(status_code=404, detail="Player not in squad")
    
    # Create service
    service = TransferService()
    
    # Unlist player
    unlisting_result = service.unlist_player_from_sale(squad_player)
    await session.commit()
    
    return {
        "success": True,
        "message": "Player removed from sale listing",
        "result": unlisting_result
    }


@router.get("/listed")
async def get_listed_players_endpoint(
    career_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Get all players currently listed for sale.
    
    - **career_id**: ID of the career (from path)
    """
    # Query listed players
    result = await session.execute(
        select(SquadPlayer)
        .where(SquadPlayer.career_id == career_id)
        .where(SquadPlayer.is_listed_for_sale == True)
    )
    listed_players = result.scalars().all()
    
    return {
        "success": True,
        "count": len(listed_players),
        "players": [
            {
                "player_id": sp.player_id,
                "squad_number": sp.squad_number,
                "asking_price": sp.asking_price,
                "wage": sp.wage,
                "squad_status": sp.squad_status.value,
                "morale": sp.morale,
            }
            for sp in listed_players
        ]
    }


@router.get("/listing/{player_id}")
async def get_listing_details_endpoint(
    career_id: int,
    player_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Get listing details for a specific player.
    
    - **career_id**: ID of the career (from path)
    - **player_id**: ID of the player
    """
    # Get squad player
    result = await session.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career_id,
            SquadPlayer.player_id == player_id
        )
    )
    squad_player = result.scalar_one_or_none()
    
    if not squad_player:
        raise HTTPException(status_code=404, detail="Player not in squad")
    
    # Create service
    service = TransferService()
    
    # Get listing details
    details = service.get_listing_details(squad_player)
    
    return {
        "success": True,
        "listed": details is not None,
        "details": details
    }
```

## Telegram Bot Handler Examples

### Bot Commands

```python
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.transfer_service import TransferService

async def list_player_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: AsyncSession
):
    """
    Handle /listplayer command.
    
    Usage: /listplayer <player_id> <asking_price>
    Example: /listplayer 123 1000000
    """
    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /listplayer <player_id> <asking_price>\n"
            "Example: /listplayer 123 1000000"
        )
        return
    
    try:
        player_id = int(context.args[0])
        asking_price = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "Invalid input. Player ID and asking price must be numbers."
        )
        return
    
    # Get user's career
    user_id = update.effective_user.id
    career = await get_user_career(session, user_id)
    
    if not career:
        await update.message.reply_text("You don't have an active career.")
        return
    
    # Get squad player
    result = await session.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career.id,
            SquadPlayer.player_id == player_id
        )
    )
    squad_player = result.scalar_one_or_none()
    
    if not squad_player:
        await update.message.reply_text("Player not found in your squad.")
        return
    
    # Create service
    service = TransferService()
    
    # Validate
    is_valid, error_msg = service.validate_player_listing(squad_player, asking_price)
    if not is_valid:
        await update.message.reply_text(f"Cannot list player: {error_msg}")
        return
    
    # List player
    try:
        listing_result = service.list_player_for_sale(squad_player, asking_price)
        await session.commit()
        
        await update.message.reply_text(
            f"✅ Player listed for sale!\n"
            f"Player ID: {listing_result['player_id']}\n"
            f"Asking Price: ${listing_result['asking_price']:,}\n"
            f"Weekly Wage: ${listing_result['wage']:,}"
        )
    except ValueError as e:
        await session.rollback()
        await update.message.reply_text(f"Error: {str(e)}")


async def unlist_player_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: AsyncSession
):
    """
    Handle /unlistplayer command.
    
    Usage: /unlistplayer <player_id>
    Example: /unlistplayer 123
    """
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /unlistplayer <player_id>\n"
            "Example: /unlistplayer 123"
        )
        return
    
    try:
        player_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid player ID. Must be a number.")
        return
    
    # Get user's career
    user_id = update.effective_user.id
    career = await get_user_career(session, user_id)
    
    if not career:
        await update.message.reply_text("You don't have an active career.")
        return
    
    # Get squad player
    result = await session.execute(
        select(SquadPlayer).where(
            SquadPlayer.career_id == career.id,
            SquadPlayer.player_id == player_id
        )
    )
    squad_player = result.scalar_one_or_none()
    
    if not squad_player:
        await update.message.reply_text("Player not found in your squad.")
        return
    
    # Create service
    service = TransferService()
    
    # Unlist player
    unlisting_result = service.unlist_player_from_sale(squad_player)
    await session.commit()
    
    await update.message.reply_text(
        f"✅ Player removed from sale listing!\n"
        f"Player ID: {unlisting_result['player_id']}"
    )


async def show_listed_players_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: AsyncSession
):
    """
    Handle /listedplayers command.
    
    Shows all players currently listed for sale.
    """
    # Get user's career
    user_id = update.effective_user.id
    career = await get_user_career(session, user_id)
    
    if not career:
        await update.message.reply_text("You don't have an active career.")
        return
    
    # Query listed players
    result = await session.execute(
        select(SquadPlayer)
        .where(SquadPlayer.career_id == career.id)
        .where(SquadPlayer.is_listed_for_sale == True)
    )
    listed_players = result.scalars().all()
    
    if not listed_players:
        await update.message.reply_text("No players currently listed for sale.")
        return
    
    # Format message
    message = "📋 Players Listed for Sale:\n\n"
    for sp in listed_players:
        message += (
            f"🔹 Player ID: {sp.player_id}\n"
            f"   Squad #: {sp.squad_number}\n"
            f"   Asking Price: ${sp.asking_price:,}\n"
            f"   Weekly Wage: ${sp.wage:,}\n"
            f"   Status: {sp.squad_status.value}\n"
            f"   Morale: {sp.morale}/100\n\n"
        )
    
    await update.message.reply_text(message)
```

## Error Handling Examples

### Handling Common Errors

```python
async def safe_list_player(
    session: AsyncSession,
    career_id: int,
    player_id: int,
    asking_price: int
) -> dict:
    """
    Safely list a player with comprehensive error handling.
    """
    try:
        # Get squad player
        result = await session.execute(
            select(SquadPlayer).where(
                SquadPlayer.career_id == career_id,
                SquadPlayer.player_id == player_id
            )
        )
        squad_player = result.scalar_one_or_none()
        
        if not squad_player:
            return {
                "success": False,
                "error_code": "PLAYER_NOT_FOUND",
                "error": "Player not in squad"
            }
        
        # Create service
        service = TransferService()
        
        # Validate
        is_valid, error_msg = service.validate_player_listing(
            squad_player, asking_price
        )
        if not is_valid:
            error_code = "INVALID_PRICE" if "negative" in error_msg.lower() else "ALREADY_LISTED"
            return {
                "success": False,
                "error_code": error_code,
                "error": error_msg
            }
        
        # List player
        listing_result = service.list_player_for_sale(squad_player, asking_price)
        await session.commit()
        
        return {
            "success": True,
            "listing": listing_result
        }
        
    except ValueError as e:
        await session.rollback()
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "error": str(e)
        }
    except Exception as e:
        await session.rollback()
        return {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error": f"An unexpected error occurred: {str(e)}"
        }
```

## Testing Examples

### Unit Test Example

```python
import pytest
from app.services.transfer_service import TransferService

def test_list_player_workflow():
    """Test complete listing workflow"""
    service = TransferService()
    
    # Create mock player
    class MockPlayer:
        def __init__(self):
            self.player_id = 1
            self.wage = 5000
            self.is_listed_for_sale = False
            self.asking_price = None
        
        def list_for_sale(self, price):
            if price < 0:
                raise ValueError("Asking price cannot be negative")
            self.is_listed_for_sale = True
            self.asking_price = price
        
        def unlist_from_sale(self):
            self.is_listed_for_sale = False
            self.asking_price = None
    
    player = MockPlayer()
    
    # List player
    result = service.list_player_for_sale(player, 1000000)
    assert result["listed"] is True
    assert player.is_listed_for_sale is True
    
    # Unlist player
    result = service.unlist_player_from_sale(player)
    assert result["listed"] is False
    assert player.is_listed_for_sale is False
```

## Summary

This document provides comprehensive examples of how to use the player listing system in various contexts:

1. **Database Operations** - Direct SQLAlchemy usage
2. **API Endpoints** - FastAPI REST endpoints
3. **Bot Handlers** - Telegram bot command handlers
4. **Error Handling** - Comprehensive error handling patterns
5. **Testing** - Unit test examples

All examples follow best practices and demonstrate proper error handling, validation, and database transaction management.
