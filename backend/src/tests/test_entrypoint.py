from types import SimpleNamespace
from typing import Any

import pytest

import app
from app import settings


@pytest.mark.parametrize(
    ("environment", "expected_reload_dirs"),
    [("local", ["src/app/"]), ("prod", None)],
)
def test_main_configures_reload_only_for_local_environment(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    expected_reload_dirs: list[str] | None,
) -> None:
    captured: dict[str, Any] = {}
    config = SimpleNamespace(
        env=environment,
        api=SimpleNamespace(
            host="127.0.0.1",
            port=8000,
            forwarded_allow_ips=["127.0.0.1"],
        ),
    )

    def run(*args: Any, **kwargs: Any) -> None:
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(settings, "get_config", lambda: config)
    monkeypatch.setattr(app.uvicorn, "run", run)

    app.main()

    assert captured["args"] == ("app.application:get_production_app",)
    assert captured["kwargs"]["reload"] is (environment == "local")
    assert captured["kwargs"]["reload_dirs"] == expected_reload_dirs
