from sfw import assistant


def test_provider_status_reports_unconfigured_without_exposing_secrets(monkeypatch):
    monkeypatch.setattr(assistant, "ai_settings", lambda: {
        "provider": "gemini", "gemini_key": "", "gemini_model": "test-model",
        "anthropic_key": "", "anthropic_model": "", "openai_key": "", "openai_model": ""
    })
    status = assistant.ai_provider_status()
    assert status["configured"] is False
    assert status["provider"] == "Gemini"
    assert "missing" in status["message"].lower()
    assert "key" not in status


def test_provider_status_reports_ready_configuration(monkeypatch):
    monkeypatch.setattr(assistant, "ai_settings", lambda: {
        "provider": "openai", "gemini_key": "", "gemini_model": "",
        "anthropic_key": "", "anthropic_model": "", "openai_key": "secret",
        "openai_model": "test-model"
    })
    status = assistant.ai_provider_status()
    assert status["configured"] is True
    assert status["provider"] == "OpenAI"
    assert status["model"] == "test-model"
    assert "secret" not in str(status)


def test_provider_status_rejects_unknown_provider(monkeypatch):
    monkeypatch.setattr(assistant, "ai_settings", lambda: {
        "provider": "unknown", "gemini_key": "", "gemini_model": "",
        "anthropic_key": "", "anthropic_model": "", "openai_key": "", "openai_model": ""
    })
    assert assistant.ai_provider_status()["configured"] is False


def test_messages_require_latest_user_question():
    messages = [{"role": "user", "content": "Explain osmosis."}]
    assert assistant._normalise_messages(messages) == messages


def test_messages_reject_assistant_only_history():
    try:
        assistant._normalise_messages([{"role": "assistant", "content": "Hello"}])
    except ValueError as exc:
        assert "latest" in str(exc).lower()
    else:
        raise AssertionError("Assistant-only history should be rejected")


def test_messages_discard_unknown_roles_and_blank_content():
    messages = [
        {"role": "system", "content": "ignore"},
        {"role": "user", "content": "  "},
        {"role": "user", "content": "What is diffusion?"},
    ]
    assert assistant._normalise_messages(messages) == [
        {"role": "user", "content": "What is diffusion?"}
    ]


def test_science_prompt_includes_discipline_level_and_mode():
    prompt = assistant.build_science_prompt(
        "How does compost affect maize growth?",
        discipline="Agriculture",
        level="Undergraduate",
        mode="Plan an experiment",
    )
    assert "Agriculture" in prompt
    assert "Undergraduate" in prompt
    assert "testable question" in prompt
    assert "How does compost affect maize growth?" in prompt


def test_science_prompt_rejects_empty_question():
    try:
        assistant.build_science_prompt("   ")
    except ValueError as exc:
        assert "question" in str(exc).lower()
    else:
        raise AssertionError("An empty research question should be rejected")
