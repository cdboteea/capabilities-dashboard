"""Tests for Alert Engine API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
from datetime import datetime

from src.main import app
from src.models.alert_models import AlertType, AlertPriority, AlertChannel


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_alert_manager():
    """Mock alert manager fixture."""
    with patch('src.main.alert_manager') as mock:
        mock_manager = AsyncMock()
        mock.return_value = mock_manager
        yield mock_manager


@pytest.fixture
def mock_database():
    """Mock database fixture."""
    with patch('src.main.database') as mock:
        mock_db = AsyncMock()
        mock.return_value = mock_db
        yield mock_db


def test_health_check(client, mock_database):
    """Test health check endpoint."""
    mock_database.pool.acquire.return_value.__aenter__.return_value.fetchval.return_value = 1
    
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "alert_engine"


def test_create_alert(client, mock_alert_manager):
    """Test alert creation endpoint."""
    mock_alert_manager.create_alert.return_value = "test-alert-id"
    
    alert_data = {
        "alert_type": "price_change",
        "priority": "high",
        "title": "Test Alert",
        "message": "This is a test alert",
        "asset_symbol": "AAPL"
    }
    
    response = client.post("/alerts", json=alert_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["alert_id"] == "test-alert-id"
    assert data["status"] == "created"


def test_create_alert_validation_error(client):
    """Test alert creation with validation error."""
    alert_data = {
        "alert_type": "invalid_type",
        "priority": "high",
        "title": "",  # Empty title should fail
        "message": "Test message"
    }
    
    response = client.post("/alerts", json=alert_data)
    assert response.status_code == 422  # Validation error


def test_get_alerts(client, mock_database):
    """Test get alerts endpoint."""
    mock_alerts = [
        {
            "alert_id": "test-1",
            "alert_type": "price_change",
            "priority": "high",
            "title": "Test Alert 1",
            "message": "Test message 1",
            "created_at": datetime.utcnow()
        }
    ]
    
    mock_database.get_alerts.return_value = mock_alerts
    
    response = client.get("/alerts?user_id=test-user")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["alert_id"] == "test-1"


def test_create_condition(client, mock_database):
    """Test create alert condition endpoint."""
    mock_database.store_condition.return_value = "test-condition-id"
    
    condition_data = {
        "asset_symbol": "AAPL",
        "condition_type": "price_change",
        "threshold_value": 150.0,
        "comparison_operator": "greater_than"
    }
    
    response = client.post("/conditions?user_id=test-user", json=condition_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["condition_id"] == "test-condition-id"
    assert data["status"] == "created"


def test_get_preferences(client, mock_database):
    """Test get user preferences endpoint."""
    from src.models.alert_models import NotificationPreferences
    
    mock_prefs = NotificationPreferences(
        user_id="test-user",
        email_enabled=True,
        sms_enabled=False,
        email_address="test@example.com"
    )
    
    mock_database.get_user_preferences.return_value = mock_prefs
    
    response = client.get("/preferences/test-user")
    assert response.status_code == 200
    
    data = response.json()
    assert data["user_id"] == "test-user"
    assert data["email_enabled"] is True


def test_update_preferences(client, mock_database):
    """Test update user preferences endpoint."""
    from src.models.alert_models import NotificationPreferences
    
    mock_prefs = NotificationPreferences(user_id="test-user")
    mock_database.get_user_preferences.return_value = mock_prefs
    mock_database.update_user_preferences.return_value = None
    
    update_data = {
        "email_enabled": False,
        "sms_enabled": True,
        "phone_number": "+1234567890"
    }
    
    response = client.put("/preferences/test-user", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "updated"


def test_get_delivery_status(client, mock_database):
    """Test get delivery status endpoint."""
    from src.models.alert_models import AlertDelivery, AlertChannel, AlertStatus
    
    mock_delivery = AlertDelivery(
        delivery_id="test-delivery-id",
        alert_id="test-alert-id",
        user_id="test-user",
        channel=AlertChannel.EMAIL,
        recipient="test@example.com",
        content="Test content",
        status=AlertStatus.SENT
    )
    
    mock_database.get_delivery_status.return_value = mock_delivery
    
    response = client.get("/deliveries/test-delivery-id")
    assert response.status_code == 200
    
    data = response.json()
    assert data["delivery_id"] == "test-delivery-id"
    assert data["status"] == "sent"


def test_get_metrics(client, mock_database):
    """Test get metrics endpoint."""
    from src.models.alert_models import AlertMetrics
    
    mock_metrics = [
        AlertMetrics(
            alerts_created=10,
            alerts_sent=8,
            alerts_failed=2,
            email_sent=5,
            sms_sent=3
        )
    ]
    
    mock_database.get_metrics.return_value = mock_metrics
    
    response = client.get("/metrics?hours=24")
    assert response.status_code == 200
    
    data = response.json()
    assert "summary" in data
    assert data["summary"]["total_alerts_created"] == 10
    assert data["summary"]["total_alerts_sent"] == 8


def test_test_email(client, mock_alert_manager):
    """Test email testing endpoint."""
    mock_alert_manager.email_service.test_connection.return_value = True
    mock_alert_manager.email_service.send_alert_email.return_value = True
    
    response = client.post("/test/email?email=test@example.com")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"


def test_test_webhook(client, mock_alert_manager):
    """Test webhook testing endpoint."""
    mock_alert_manager.webhook_service.test_webhook_url.return_value = True
    
    response = client.post("/test/webhook?url=https://example.com/webhook")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"


def test_get_service_status(client, mock_alert_manager):
    """Test service status endpoint."""
    # Mock queue sizes
    mock_alert_manager.processing_queues = {
        AlertPriority.CRITICAL: AsyncMock(),
        AlertPriority.HIGH: AsyncMock(),
        AlertPriority.MEDIUM: AsyncMock(),
        AlertPriority.LOW: AsyncMock()
    }
    
    for queue in mock_alert_manager.processing_queues.values():
        queue.qsize.return_value = 0
    
    mock_alert_manager.worker_tasks = []
    mock_alert_manager.scheduler.running = True
    
    response = client.get("/status")
    assert response.status_code == 200
    
    data = response.json()
    assert data["service"] == "alert_engine"
    assert data["status"] == "running"
    assert "queue_sizes" in data


def test_delete_condition(client, mock_database):
    """Test delete condition endpoint."""
    mock_database.delete_condition.return_value = True
    
    response = client.delete("/conditions/test-condition-id?user_id=test-user")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "deleted"


def test_delete_condition_not_found(client, mock_database):
    """Test delete non-existent condition."""
    mock_database.delete_condition.return_value = False
    
    response = client.delete("/conditions/nonexistent?user_id=test-user")
    assert response.status_code == 404


def test_get_alert_not_found(client, mock_database):
    """Test get non-existent alert."""
    mock_database.get_alerts.return_value = []
    
    response = client.get("/alerts/nonexistent")
    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__]) 