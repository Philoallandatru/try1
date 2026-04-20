"""Tests for WebSocket real-time updates."""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from apps.portal_runner.analysis_websocket import AnalysisWebSocketManager


@pytest.fixture
def ws_manager():
    """Create a WebSocket manager instance."""
    return AnalysisWebSocketManager()


@pytest.mark.asyncio
async def test_websocket_manager_connect_disconnect():
    """Test WebSocket connection and disconnection."""
    manager = AnalysisWebSocketManager()

    # Mock WebSocket
    class MockWebSocket:
        async def accept(self):
            pass

    ws = MockWebSocket()
    analysis_id = "test-analysis-1"

    # Connect
    await manager.connect(ws, analysis_id)
    assert analysis_id in manager.active_connections
    assert ws in manager.active_connections[analysis_id]

    # Disconnect
    await manager.disconnect(ws, analysis_id)
    assert analysis_id not in manager.active_connections


@pytest.mark.asyncio
async def test_websocket_manager_send_progress():
    """Test sending progress updates."""
    manager = AnalysisWebSocketManager()

    # Mock WebSocket that captures sent messages
    messages = []

    class MockWebSocket:
        async def accept(self):
            pass

        async def send_text(self, text):
            messages.append(json.loads(text))

    ws = MockWebSocket()
    analysis_id = "test-analysis-2"

    await manager.connect(ws, analysis_id)

    # Send progress update
    await manager.send_progress(
        analysis_id=analysis_id,
        stage="evidence_collection",
        progress=0.5,
        message="Collecting Confluence evidence"
    )

    # Verify message
    assert len(messages) == 1
    msg = messages[0]
    assert msg["type"] == "progress"
    assert msg["stage"] == "evidence_collection"
    assert msg["progress"] == 0.5
    assert msg["message"] == "Collecting Confluence evidence"
    assert "timestamp" in msg


@pytest.mark.asyncio
async def test_websocket_manager_send_evidence():
    """Test sending evidence updates."""
    manager = AnalysisWebSocketManager()

    messages = []

    class MockWebSocket:
        async def accept(self):
            pass

        async def send_text(self, text):
            messages.append(json.loads(text))

    ws = MockWebSocket()
    analysis_id = "test-analysis-3"

    await manager.connect(ws, analysis_id)

    # Send evidence update
    evidence = {
        "source": "confluence",
        "document_id": "CONF-123",
        "title": "NVMe Flush Command Spec",
        "relevance_score": 0.95
    }

    await manager.send_evidence(analysis_id=analysis_id, evidence=evidence)

    # Verify message
    assert len(messages) == 1
    msg = messages[0]
    assert msg["type"] == "evidence"
    assert msg["evidence"] == evidence
    assert "timestamp" in msg


@pytest.mark.asyncio
async def test_websocket_manager_send_section():
    """Test sending section updates (for daily reports)."""
    manager = AnalysisWebSocketManager()

    messages = []

    class MockWebSocket:
        async def accept(self):
            pass

        async def send_text(self, text):
            messages.append(json.loads(text))

    ws = MockWebSocket()
    analysis_id = "test-report-1"

    await manager.connect(ws, analysis_id)

    # Send section update
    await manager.send_section(
        analysis_id=analysis_id,
        section_name="Summary",
        content="Total analyzed issues: 42"
    )

    # Verify message
    assert len(messages) == 1
    msg = messages[0]
    assert msg["type"] == "section"
    assert msg["section"] == "Summary"
    assert msg["content"] == "Total analyzed issues: 42"
    assert "timestamp" in msg


@pytest.mark.asyncio
async def test_websocket_manager_send_complete():
    """Test sending completion notification."""
    manager = AnalysisWebSocketManager()

    messages = []

    class MockWebSocket:
        async def accept(self):
            pass

        async def send_text(self, text):
            messages.append(json.loads(text))

    ws = MockWebSocket()
    analysis_id = "test-analysis-4"

    await manager.connect(ws, analysis_id)

    # Send completion
    result = {
        "issue_id": "SSD-777",
        "status": "completed",
        "citation_count": 15
    }

    await manager.send_complete(analysis_id=analysis_id, result=result)

    # Verify message
    assert len(messages) == 1
    msg = messages[0]
    assert msg["type"] == "complete"
    assert msg["result"] == result
    assert "timestamp" in msg


@pytest.mark.asyncio
async def test_websocket_manager_send_error():
    """Test sending error notification."""
    manager = AnalysisWebSocketManager()

    messages = []

    class MockWebSocket:
        async def accept(self):
            pass

        async def send_text(self, text):
            messages.append(json.loads(text))

    ws = MockWebSocket()
    analysis_id = "test-analysis-5"

    await manager.connect(ws, analysis_id)

    # Send error
    await manager.send_error(
        analysis_id=analysis_id,
        error="Failed to retrieve Jira issue: Connection timeout"
    )

    # Verify message
    assert len(messages) == 1
    msg = messages[0]
    assert msg["type"] == "error"
    assert "Connection timeout" in msg["error"]
    assert "timestamp" in msg


@pytest.mark.asyncio
async def test_websocket_manager_multiple_clients():
    """Test broadcasting to multiple connected clients."""
    manager = AnalysisWebSocketManager()

    messages1 = []
    messages2 = []

    class MockWebSocket1:
        async def accept(self):
            pass

        async def send_text(self, text):
            messages1.append(json.loads(text))

    class MockWebSocket2:
        async def accept(self):
            pass

        async def send_text(self, text):
            messages2.append(json.loads(text))

    ws1 = MockWebSocket1()
    ws2 = MockWebSocket2()
    analysis_id = "test-analysis-6"

    # Connect both clients
    await manager.connect(ws1, analysis_id)
    await manager.connect(ws2, analysis_id)

    # Send update
    await manager.send_progress(
        analysis_id=analysis_id,
        stage="llm_reasoning",
        progress=0.8,
        message="Generating analysis"
    )

    # Both clients should receive the message
    assert len(messages1) == 1
    assert len(messages2) == 1
    assert messages1[0]["type"] == "progress"
    assert messages2[0]["type"] == "progress"


@pytest.mark.asyncio
async def test_websocket_manager_disconnected_client_cleanup():
    """Test that disconnected clients are cleaned up."""
    manager = AnalysisWebSocketManager()

    class MockWebSocketFailing:
        async def accept(self):
            pass

        async def send_text(self, text):
            raise Exception("Connection closed")

    ws = MockWebSocketFailing()
    analysis_id = "test-analysis-7"

    await manager.connect(ws, analysis_id)
    assert analysis_id in manager.active_connections

    # Try to send update (should fail and clean up)
    await manager.send_progress(
        analysis_id=analysis_id,
        stage="test",
        progress=0.5
    )

    # Client should be removed
    assert analysis_id not in manager.active_connections


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
