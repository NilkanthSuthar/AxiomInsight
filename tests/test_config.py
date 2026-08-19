"""Credential handling and tracing state."""

import pytest

from app import config


def test_missing_openai_key_raises_actionable_error(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", None)
    with pytest.raises(config.MissingCredentialError) as exc:
        config.require_openai_key()
    # The message has to tell the reader what to do, not just what failed.
    assert ".env" in str(exc.value)


def test_present_openai_key_is_returned(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-test")
    assert config.require_openai_key() == "sk-test"


@pytest.mark.parametrize(
    "tracing,key,expected",
    [
        (True, "ls-key", "enabled"),
        (True, None, "requested but LANGCHAIN_API_KEY is missing"),
        (False, "ls-key", "disabled"),
        (False, None, "disabled"),
    ],
)
def test_tracing_status(monkeypatch, tracing, key, expected):
    monkeypatch.setattr(config, "LANGCHAIN_TRACING_V2", tracing)
    monkeypatch.setattr(config, "LANGCHAIN_API_KEY", key)
    assert config.tracing_status() == expected


def test_tracing_is_off_by_default():
    """Tracing must never switch itself on: it ships data to a third party."""
    assert config.LANGCHAIN_TRACING_V2 is False
