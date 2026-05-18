"""
Unit tests for Celery task queue configuration
"""

import pytest
from unittest.mock import patch, MagicMock
from celery import Celery
from kombu import Queue

from app.core.celery import celery_app, get_celery_app, BaseTask


class TestCeleryConfiguration:
    """Test Celery application configuration"""
    
    def test_celery_app_instance(self):
        """Test that celery_app is a Celery instance"""
        assert isinstance(celery_app, Celery)
        assert celery_app.main == "telegram_football_manager"
    
    def test_celery_broker_url(self):
        """Test that Celery uses correct broker URL from settings"""
        with patch("app.core.celery.settings") as mock_settings:
            mock_settings.CELERY_BROKER_URL = "redis://localhost:6379/1"
            
            # Verify broker URL is set correctly
            assert "redis://localhost:6379" in celery_app.conf.broker_url
    
    def test_celery_result_backend(self):
        """Test that Celery uses correct result backend from settings"""
        with patch("app.core.celery.settings") as mock_settings:
            mock_settings.CELERY_RESULT_BACKEND = "redis://localhost:6379/2"
            
            # Verify result backend is set correctly
            assert "redis://localhost:6379" in celery_app.conf.result_backend
    
    def test_celery_task_serializer(self):
        """Test that Celery uses JSON serialization"""
        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content
        assert celery_app.conf.result_serializer == "json"
    
    def test_celery_timezone(self):
        """Test that Celery uses UTC timezone"""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True
    
    def test_celery_result_expires(self):
        """Test that task results expire after 1 hour"""
        assert celery_app.conf.result_expires == 3600
    
    def test_celery_worker_settings(self):
        """Test Celery worker configuration"""
        assert celery_app.conf.worker_prefetch_multiplier == 4
        assert celery_app.conf.worker_max_tasks_per_child == 1000
        assert celery_app.conf.worker_disable_rate_limits is False
    
    def test_celery_task_time_limits(self):
        """Test task time limits"""
        assert celery_app.conf.task_time_limit == 300  # 5 minutes
        assert celery_app.conf.task_soft_time_limit == 240  # 4 minutes
    
    def test_celery_task_acks_late(self):
        """Test that tasks are acknowledged after execution"""
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.task_reject_on_worker_lost is True


class TestCeleryTaskRouting:
    """Test Celery task routing configuration"""
    
    def test_match_simulation_routing(self):
        """Test that match simulation tasks route to matches queue"""
        routes = celery_app.conf.task_routes
        assert "app.tasks.match_simulation.*" in routes
        assert routes["app.tasks.match_simulation.*"]["queue"] == "matches"
    
    def test_weekly_updates_routing(self):
        """Test that weekly update tasks route to updates queue"""
        routes = celery_app.conf.task_routes
        assert "app.tasks.weekly_updates.*" in routes
        assert routes["app.tasks.weekly_updates.*"]["queue"] == "updates"
    
    def test_ai_manager_routing(self):
        """Test that AI manager tasks route to ai queue"""
        routes = celery_app.conf.task_routes
        assert "app.tasks.ai_manager.*" in routes
        assert routes["app.tasks.ai_manager.*"]["queue"] == "ai"


class TestCeleryQueues:
    """Test Celery queue configuration"""
    
    def test_queue_definitions(self):
        """Test that all required queues are defined"""
        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]
        
        assert "matches" in queue_names
        assert "updates" in queue_names
        assert "ai" in queue_names
        assert "default" in queue_names
    
    def test_queue_priorities(self):
        """Test that queues have correct priorities"""
        queues = {q.name: q for q in celery_app.conf.task_queues}
        
        assert queues["matches"].priority == 10  # Highest priority
        assert queues["updates"].priority == 5
        assert queues["ai"].priority == 3
        assert queues["default"].priority == 1  # Lowest priority
    
    def test_queue_exchanges(self):
        """Test that queues have correct exchanges"""
        queues = {q.name: q for q in celery_app.conf.task_queues}
        
        assert queues["matches"].exchange.name == "matches"
        assert queues["updates"].exchange.name == "updates"
        assert queues["ai"].exchange.name == "ai"
        assert queues["default"].exchange.name == "default"


class TestCeleryBeatSchedule:
    """Test Celery Beat periodic task schedule"""
    
    def test_weekly_update_schedule(self):
        """Test that weekly update is scheduled for Monday midnight"""
        schedule = celery_app.conf.beat_schedule
        
        assert "weekly-update" in schedule
        weekly_task = schedule["weekly-update"]
        
        assert weekly_task["task"] == "app.tasks.weekly_updates.process_weekly_update"
        assert weekly_task["schedule"].day_of_week == 1  # Monday
        assert weekly_task["schedule"].hour == 0
        assert weekly_task["schedule"].minute == 0
    
    def test_cleanup_schedule(self):
        """Test that cleanup task is scheduled daily at 2 AM"""
        schedule = celery_app.conf.beat_schedule
        
        assert "cleanup-expired-results" in schedule
        cleanup_task = schedule["cleanup-expired-results"]
        
        assert cleanup_task["task"] == "app.tasks.maintenance.cleanup_expired_results"
        assert cleanup_task["schedule"].hour == 2
        assert cleanup_task["schedule"].minute == 0


class TestBaseTask:
    """Test BaseTask class configuration"""
    
    def test_base_task_autoretry(self):
        """Test that BaseTask has autoretry configured"""
        assert BaseTask.autoretry_for == (Exception,)
        assert BaseTask.retry_kwargs == {"max_retries": 3}
    
    def test_base_task_retry_backoff(self):
        """Test that BaseTask has retry backoff configured"""
        assert BaseTask.retry_backoff is True
        assert BaseTask.retry_backoff_max == 600  # 10 minutes
        assert BaseTask.retry_jitter is True
    
    def test_base_task_on_failure(self):
        """Test BaseTask on_failure callback"""
        task = BaseTask()
        task.name = "test_task"
        
        # Mock the super().on_failure call
        with patch.object(BaseTask.__bases__[0], "on_failure"):
            # Should not raise exception
            task.on_failure(
                exc=Exception("Test error"),
                task_id="test-id",
                args=(),
                kwargs={},
                einfo=None,
            )
    
    def test_base_task_on_retry(self):
        """Test BaseTask on_retry callback"""
        task = BaseTask()
        task.name = "test_task"
        
        # Mock the super().on_retry call
        with patch.object(BaseTask.__bases__[0], "on_retry"):
            # Should not raise exception
            task.on_retry(
                exc=Exception("Test error"),
                task_id="test-id",
                args=(),
                kwargs={},
                einfo=None,
            )
    
    def test_base_task_on_success(self):
        """Test BaseTask on_success callback"""
        task = BaseTask()
        task.name = "test_task"
        
        # Mock the super().on_success call
        with patch.object(BaseTask.__bases__[0], "on_success"):
            # Should not raise exception
            task.on_success(
                retval="success",
                task_id="test-id",
                args=(),
                kwargs={},
            )


class TestGetCeleryApp:
    """Test get_celery_app function"""
    
    def test_get_celery_app_returns_instance(self):
        """Test that get_celery_app returns Celery instance"""
        app = get_celery_app()
        
        assert isinstance(app, Celery)
        assert app is celery_app
    
    def test_get_celery_app_singleton(self):
        """Test that get_celery_app returns same instance"""
        app1 = get_celery_app()
        app2 = get_celery_app()
        
        assert app1 is app2


class TestCeleryTaskIncludes:
    """Test that Celery includes all task modules"""
    
    def test_task_modules_included(self):
        """Test that all task modules are included in Celery config"""
        includes = celery_app.conf.include
        
        assert "app.tasks.match_simulation" in includes
        assert "app.tasks.weekly_updates" in includes
        assert "app.tasks.ai_manager" in includes


class TestCeleryBrokerSettings:
    """Test Celery broker connection settings"""
    
    def test_broker_connection_retry(self):
        """Test that broker connection retry is enabled"""
        assert celery_app.conf.broker_connection_retry_on_startup is True
        assert celery_app.conf.broker_connection_retry is True
        assert celery_app.conf.broker_connection_max_retries == 10


class TestCeleryTaskDefaultClass:
    """Test that Celery uses BaseTask as default task class"""
    
    def test_default_task_class(self):
        """Test that celery_app.Task is set to BaseTask"""
        assert celery_app.Task is BaseTask


class TestCeleryConfiguration_Integration:
    """Integration tests for Celery configuration"""
    
    def test_celery_app_can_send_task(self):
        """Test that Celery app can send tasks (mock)"""
        with patch.object(celery_app, "send_task") as mock_send:
            mock_send.return_value = MagicMock(id="test-task-id")
            
            result = celery_app.send_task(
                "app.tasks.match_simulation.simulate_match",
                args=[1, 2, 3, 4],
            )
            
            assert result.id == "test-task-id"
            mock_send.assert_called_once()
    
    def test_celery_app_configuration_complete(self):
        """Test that all required configuration is present"""
        conf = celery_app.conf
        
        # Check all critical configuration keys
        assert conf.broker_url is not None
        assert conf.result_backend is not None
        assert conf.task_serializer is not None
        assert conf.result_serializer is not None
        assert conf.timezone is not None
        assert conf.task_routes is not None
        assert conf.task_queues is not None
        assert conf.beat_schedule is not None


class TestCeleryResultBackendSettings:
    """Test Celery result backend settings"""
    
    def test_result_backend_transport_options(self):
        """Test result backend transport options"""
        transport_opts = celery_app.conf.result_backend_transport_options
        
        assert "visibility_timeout" in transport_opts
        assert transport_opts["visibility_timeout"] == 3600
