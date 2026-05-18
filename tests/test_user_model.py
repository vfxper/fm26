"""
Unit Tests for User Model
"""

import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User


class TestUserModel:
    """Test suite for User model"""
    
    @pytest.mark.asyncio
    async def test_create_user_with_all_fields(self, test_db_session):
        """Test creating a user with all fields populated"""
        # Arrange
        user = User(
            telegram_user_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            language_code="en"
        )
        
        # Act
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        # Assert
        assert user.id is not None
        assert user.telegram_user_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.language_code == "en"
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.last_login_at is None
    
    @pytest.mark.asyncio
    async def test_create_user_with_minimal_fields(self, test_db_session):
        """Test creating a user with only required fields"""
        # Arrange
        user = User(telegram_user_id=987654321)
        
        # Act
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        # Assert
        assert user.id is not None
        assert user.telegram_user_id == 987654321
        assert user.username is None
        assert user.first_name is None
        assert user.last_name is None
        assert user.language_code == "en"  # Default value
        assert user.created_at is not None
        assert user.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_telegram_user_id_unique_constraint(self, test_db_session):
        """Test that telegram_user_id must be unique"""
        # Arrange
        user1 = User(telegram_user_id=111111111, username="user1")
        user2 = User(telegram_user_id=111111111, username="user2")
        
        # Act & Assert
        test_db_session.add(user1)
        await test_db_session.commit()
        
        test_db_session.add(user2)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_telegram_user_id_not_null(self, test_db_session):
        """Test that telegram_user_id cannot be null"""
        # Arrange
        user = User(username="testuser")
        
        # Act & Assert
        test_db_session.add(user)
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    @pytest.mark.asyncio
    async def test_telegram_user_id_supports_large_values(self, test_db_session):
        """Test that telegram_user_id supports large bigint values"""
        # Arrange - Telegram user IDs can be very large
        large_telegram_id = 9223372036854775807  # Max bigint value
        user = User(telegram_user_id=large_telegram_id)
        
        # Act
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        # Assert
        assert user.telegram_user_id == large_telegram_id
    
    @pytest.mark.asyncio
    async def test_update_user_fields(self, test_db_session):
        """Test updating user fields"""
        # Arrange
        user = User(
            telegram_user_id=222222222,
            username="oldusername",
            first_name="Old",
            language_code="en"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        original_updated_at = user.updated_at
        
        # Act
        user.username = "newusername"
        user.first_name = "New"
        user.language_code = "ru"
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        # Assert
        assert user.username == "newusername"
        assert user.first_name == "New"
        assert user.language_code == "ru"
        # Note: updated_at auto-update depends on database trigger/onupdate
    
    @pytest.mark.asyncio
    async def test_update_last_login_at(self, test_db_session):
        """Test updating last_login_at timestamp"""
        # Arrange
        user = User(telegram_user_id=333333333)
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        assert user.last_login_at is None
        
        # Act
        login_time = datetime.utcnow()
        user.last_login_at = login_time
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        # Assert
        assert user.last_login_at is not None
        assert abs((user.last_login_at - login_time).total_seconds()) < 1
    
    @pytest.mark.asyncio
    async def test_query_user_by_telegram_user_id(self, test_db_session):
        """Test querying user by telegram_user_id (indexed field)"""
        # Arrange
        user = User(
            telegram_user_id=444444444,
            username="querytest",
            first_name="Query"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Act
        result = await test_db_session.execute(
            select(User).where(User.telegram_user_id == 444444444)
        )
        found_user = result.scalar_one_or_none()
        
        # Assert
        assert found_user is not None
        assert found_user.telegram_user_id == 444444444
        assert found_user.username == "querytest"
    
    @pytest.mark.asyncio
    async def test_query_user_by_username(self, test_db_session):
        """Test querying user by username (indexed field)"""
        # Arrange
        user = User(
            telegram_user_id=555555555,
            username="uniqueusername"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Act
        result = await test_db_session.execute(
            select(User).where(User.username == "uniqueusername")
        )
        found_user = result.scalar_one_or_none()
        
        # Assert
        assert found_user is not None
        assert found_user.username == "uniqueusername"
    
    @pytest.mark.asyncio
    async def test_user_repr(self, test_db_session):
        """Test User __repr__ method"""
        # Arrange
        user = User(
            telegram_user_id=666666666,
            username="reprtest",
            first_name="Repr"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        # Act
        repr_str = repr(user)
        
        # Assert
        assert "User" in repr_str
        assert "666666666" in repr_str
        assert "reprtest" in repr_str
        assert "Repr" in repr_str
    
    @pytest.mark.asyncio
    async def test_user_to_dict(self, test_db_session):
        """Test User to_dict method"""
        # Arrange
        user = User(
            telegram_user_id=777777777,
            username="dicttest",
            first_name="Dict",
            last_name="Test",
            language_code="ru"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        # Act
        user_dict = user.to_dict()
        
        # Assert
        assert isinstance(user_dict, dict)
        assert user_dict["telegram_user_id"] == 777777777
        assert user_dict["username"] == "dicttest"
        assert user_dict["first_name"] == "Dict"
        assert user_dict["last_name"] == "Test"
        assert user_dict["language_code"] == "ru"
        assert "created_at" in user_dict
        assert "updated_at" in user_dict
        assert user_dict["last_login_at"] is None
    
    @pytest.mark.asyncio
    async def test_multiple_users_creation(self, test_db_session):
        """Test creating multiple users"""
        # Arrange
        users = [
            User(telegram_user_id=1000001, username="user1"),
            User(telegram_user_id=1000002, username="user2"),
            User(telegram_user_id=1000003, username="user3"),
        ]
        
        # Act
        for user in users:
            test_db_session.add(user)
        await test_db_session.commit()
        
        # Assert
        result = await test_db_session.execute(select(User))
        all_users = result.scalars().all()
        assert len(all_users) >= 3
    
    @pytest.mark.asyncio
    async def test_user_with_special_characters_in_name(self, test_db_session):
        """Test user with special characters in name fields"""
        # Arrange
        user = User(
            telegram_user_id=888888888,
            username="user_with_underscore",
            first_name="Иван",  # Cyrillic
            last_name="O'Brien"  # Apostrophe
        )
        
        # Act
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        # Assert
        assert user.first_name == "Иван"
        assert user.last_name == "O'Brien"
    
    @pytest.mark.asyncio
    async def test_user_language_code_variations(self, test_db_session):
        """Test different language codes"""
        # Arrange & Act
        users = [
            User(telegram_user_id=2000001, language_code="en"),
            User(telegram_user_id=2000002, language_code="ru"),
            User(telegram_user_id=2000003, language_code="es"),
            User(telegram_user_id=2000004, language_code="zh"),
        ]
        
        for user in users:
            test_db_session.add(user)
        await test_db_session.commit()
        
        # Assert
        result = await test_db_session.execute(
            select(User).where(User.language_code == "ru")
        )
        ru_user = result.scalar_one_or_none()
        assert ru_user is not None
        assert ru_user.language_code == "ru"
    
    @pytest.mark.asyncio
    async def test_delete_user(self, test_db_session):
        """Test deleting a user"""
        # Arrange
        user = User(telegram_user_id=999999999, username="deleteme")
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        
        user_id = user.id
        
        # Act
        await test_db_session.delete(user)
        await test_db_session.commit()
        
        # Assert
        result = await test_db_session.execute(
            select(User).where(User.id == user_id)
        )
        deleted_user = result.scalar_one_or_none()
        assert deleted_user is None
