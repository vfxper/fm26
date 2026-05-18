"""
Unit Tests for Telegram Bot
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.bot.handlers import (
    start_command,
    help_command,
    play_command,
    stats_command,
    button_callback,
    setup_handlers,
)
from app.bot.bot import TelegramBot, get_bot
from app.core.config import settings


class TestBotHandlers:
    """Test bot command handlers"""
    
    @pytest.fixture
    def mock_update(self):
        """Create mock Update object"""
        update = MagicMock(spec=Update)
        update.effective_user = User(
            id=12345,
            first_name="Test",
            is_bot=False,
            username="testuser"
        )
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create mock Context object"""
        return MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    @pytest.mark.asyncio
    async def test_start_command(self, mock_update, mock_context):
        """Test /start command handler"""
        await start_command(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        
        # Verify reply contains welcome text
        call_args = mock_update.message.reply_text.call_args
        assert "Welcome" in call_args[0][0]
        
        # Verify reply has keyboard markup
        assert "reply_markup" in call_args[1]
        assert isinstance(call_args[1]["reply_markup"], InlineKeyboardMarkup)
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_update, mock_context):
        """Test /help command handler"""
        await help_command(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        
        # Verify reply contains help text
        call_args = mock_update.message.reply_text.call_args
        assert "Help" in call_args[0][0]
        assert "/start" in call_args[0][0]
        assert "/play" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_play_command(self, mock_update, mock_context):
        """Test /play command handler"""
        await play_command(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        
        # Verify reply has Web App button
        call_args = mock_update.message.reply_text.call_args
        assert "reply_markup" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_stats_command(self, mock_update, mock_context):
        """Test /stats command handler"""
        await stats_command(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        
        # Verify reply contains stats text
        call_args = mock_update.message.reply_text.call_args
        assert "Statistics" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_button_callback_help(self, mock_context):
        """Test help button callback"""
        # Create mock callback query
        mock_update = MagicMock(spec=Update)
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.data = "help"
        mock_update.effective_user = User(
            id=12345,
            first_name="Test",
            is_bot=False,
            username="testuser"
        )
        
        await button_callback(mock_update, mock_context)
        
        # Verify callback was answered
        mock_update.callback_query.answer.assert_called_once()
        
        # Verify message was edited
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        assert "Help" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_button_callback_stats(self, mock_context):
        """Test stats button callback"""
        # Create mock callback query
        mock_update = MagicMock(spec=Update)
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.data = "stats"
        mock_update.effective_user = User(
            id=12345,
            first_name="Test",
            is_bot=False,
            username="testuser"
        )
        
        await button_callback(mock_update, mock_context)
        
        # Verify callback was answered
        mock_update.callback_query.answer.assert_called_once()
        
        # Verify message was edited
        mock_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_update.callback_query.edit_message_text.call_args
        assert "Statistics" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_button_callback_back_to_menu(self, mock_context):
        """Test back to menu button callback"""
        # Create mock callback query
        mock_update = MagicMock(spec=Update)
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.data = "back_to_menu"
        mock_update.effective_user = User(
            id=12345,
            first_name="Test",
            is_bot=False,
            username="testuser"
        )
        
        await button_callback(mock_update, mock_context)
        
        # Verify callback was answered
        mock_update.callback_query.answer.assert_called_once()
        
        # Verify message was edited
        mock_update.callback_query.edit_message_text.assert_called_once()


class TestTelegramBot:
    """Test TelegramBot class"""
    
    @pytest.mark.asyncio
    async def test_bot_initialization_without_token(self):
        """Test bot initialization fails without token"""
        with patch.object(settings, 'TELEGRAM_BOT_TOKEN', None):
            with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN is not configured"):
                TelegramBot()
    
    @pytest.mark.asyncio
    async def test_bot_initialization_with_token(self):
        """Test bot initialization succeeds with token"""
        with patch.object(settings, 'TELEGRAM_BOT_TOKEN', 'test_token_123'):
            bot = TelegramBot()
            assert bot.token == 'test_token_123'
            assert bot.application is None
            assert not bot._initialized
    
    @pytest.mark.asyncio
    async def test_get_bot_singleton(self):
        """Test get_bot returns singleton instance"""
        with patch.object(settings, 'TELEGRAM_BOT_TOKEN', 'test_token_123'):
            # Clear any existing instance
            import app.bot.bot as bot_module
            bot_module._bot_instance = None
            
            bot1 = get_bot()
            bot2 = get_bot()
            
            assert bot1 is bot2
    
    @pytest.mark.asyncio
    async def test_bot_initialize(self):
        """Test bot application initialization"""
        with patch.object(settings, 'TELEGRAM_BOT_TOKEN', 'test_token_123'):
            bot = TelegramBot()
            
            with patch('app.bot.bot.ApplicationBuilder') as mock_builder:
                mock_app = MagicMock()
                mock_builder.return_value.token.return_value.build.return_value = mock_app
                
                app = await bot.initialize()
                
                assert app is mock_app
                assert bot.application is mock_app
                assert bot._initialized
    
    @pytest.mark.asyncio
    async def test_bot_initialize_idempotent(self):
        """Test bot initialization is idempotent"""
        with patch.object(settings, 'TELEGRAM_BOT_TOKEN', 'test_token_123'):
            bot = TelegramBot()
            
            with patch('app.bot.bot.ApplicationBuilder') as mock_builder:
                mock_app = MagicMock()
                mock_builder.return_value.token.return_value.build.return_value = mock_app
                
                app1 = await bot.initialize()
                app2 = await bot.initialize()
                
                assert app1 is app2
                # Builder should only be called once
                assert mock_builder.call_count == 1
    
    @pytest.mark.asyncio
    async def test_setup_webhook_without_url(self):
        """Test webhook setup fails gracefully without URL"""
        with patch.object(settings, 'TELEGRAM_BOT_TOKEN', 'test_token_123'):
            with patch.object(settings, 'TELEGRAM_WEBHOOK_URL', None):
                bot = TelegramBot()
                
                with patch('app.bot.bot.ApplicationBuilder') as mock_builder:
                    mock_app = MagicMock()
                    mock_builder.return_value.token.return_value.build.return_value = mock_app
                    
                    await bot.initialize()
                    result = await bot.setup_webhook()
                    
                    assert result is False
    
    @pytest.mark.asyncio
    async def test_setup_webhook_with_url(self):
        """Test webhook setup succeeds with URL"""
        with patch.object(settings, 'TELEGRAM_BOT_TOKEN', 'test_token_123'):
            with patch.object(settings, 'TELEGRAM_WEBHOOK_URL', 'https://example.com'):
                bot = TelegramBot()
                
                with patch('app.bot.bot.ApplicationBuilder') as mock_builder:
                    mock_app = MagicMock()
                    mock_bot = MagicMock()
                    mock_bot.set_webhook = AsyncMock()
                    mock_bot.get_webhook_info = AsyncMock()
                    mock_bot.get_webhook_info.return_value.url = 'https://example.com/webhook/test_token_123'
                    mock_bot.get_webhook_info.return_value.pending_update_count = 0
                    mock_app.bot = mock_bot
                    mock_builder.return_value.token.return_value.build.return_value = mock_app
                    
                    await bot.initialize()
                    result = await bot.setup_webhook()
                    
                    assert result is True
                    mock_bot.set_webhook.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_webhook(self):
        """Test webhook removal"""
        with patch.object(settings, 'TELEGRAM_BOT_TOKEN', 'test_token_123'):
            bot = TelegramBot()
            
            with patch('app.bot.bot.ApplicationBuilder') as mock_builder:
                mock_app = MagicMock()
                mock_bot = MagicMock()
                mock_bot.delete_webhook = AsyncMock()
                mock_app.bot = mock_bot
                mock_builder.return_value.token.return_value.build.return_value = mock_app
                
                await bot.initialize()
                result = await bot.remove_webhook()
                
                assert result is True
                mock_bot.delete_webhook.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_bot_info(self):
        """Test getting bot information"""
        with patch.object(settings, 'TELEGRAM_BOT_TOKEN', 'test_token_123'):
            bot = TelegramBot()
            
            with patch('app.bot.bot.ApplicationBuilder') as mock_builder:
                mock_app = MagicMock()
                mock_bot = MagicMock()
                
                # Mock bot.get_me()
                mock_bot_info = MagicMock()
                mock_bot_info.id = 123456789
                mock_bot_info.username = "test_bot"
                mock_bot_info.first_name = "Test Bot"
                mock_bot_info.can_join_groups = True
                mock_bot_info.can_read_all_group_messages = False
                mock_bot_info.supports_inline_queries = False
                mock_bot.get_me = AsyncMock(return_value=mock_bot_info)
                
                # Mock bot.get_webhook_info()
                mock_webhook_info = MagicMock()
                mock_webhook_info.url = None
                mock_webhook_info.pending_update_count = 0
                mock_bot.get_webhook_info = AsyncMock(return_value=mock_webhook_info)
                
                mock_app.bot = mock_bot
                mock_builder.return_value.token.return_value.build.return_value = mock_app
                
                await bot.initialize()
                info = await bot.get_bot_info()
                
                assert info["id"] == 123456789
                assert info["username"] == "test_bot"
                assert info["first_name"] == "Test Bot"
                assert info["webhook_url"] is None
                assert info["webhook_pending_updates"] == 0


class TestHandlerSetup:
    """Test handler setup"""
    
    def test_setup_handlers(self):
        """Test handlers are registered correctly"""
        mock_app = MagicMock()
        mock_app.add_handler = MagicMock()
        mock_app.add_error_handler = MagicMock()
        
        setup_handlers(mock_app)
        
        # Verify handlers were added
        # 4 command handlers + 1 callback handler
        assert mock_app.add_handler.call_count == 5
        
        # Verify error handler was added
        mock_app.add_error_handler.assert_called_once()
