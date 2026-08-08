from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from pcr_scheduler.health import HealthServer
from pcr_scheduler.state import HeartbeatState


def test_health_server_reports_liveness_and_readiness() -> None:
    state = HeartbeatState(enabled=False, shadow_mode=True)
    server = HealthServer("127.0.0.1", 0, state)
    server.start()
    host, port = server.address
    try:
        with urlopen(f"http://{host}:{port}/live", timeout=2) as response:
            assert response.status == 200

        with pytest.raises(HTTPError) as not_ready:
            urlopen(f"http://{host}:{port}/ready", timeout=2)
        assert not_ready.value.code == 503

        state.update(status="disabled", ready=True)
        with urlopen(f"http://{host}:{port}/health", timeout=2) as response:
            payload = json.load(response)
        assert payload["status"] == "disabled"
        assert payload["canonical_write_capable"] is False
    finally:
        server.close()
