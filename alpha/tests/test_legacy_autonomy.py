"""Exercise the retained router against the working Emergent chat API contract.

No provider credentials or network calls are needed. The SDK double models the
async UserMessage/string contract used by backend/server.py.
"""
import asyncio
import importlib.util
from pathlib import Path
import sys
import types


def test_legacy_autonomy_uses_async_story_chat_contract(monkeypatch):
    calls = {}

    class UserMessage:
        def __init__(self, text):
            self.text = text

    class LlmChat:
        def __init__(self, **kwargs):
            calls.update(kwargs)

        def with_model(self, provider, model):
            calls["model"] = (provider, model)
            return self

        async def send_message(self, message):
            assert isinstance(message, UserMessage)
            assert "soil" in message.text
            return "Let's compare the soil samples before deciding."

    module = types.ModuleType("emergentintegrations.llm.chat")
    module.LlmChat = LlmChat
    module.UserMessage = UserMessage
    monkeypatch.setitem(sys.modules, "emergentintegrations.llm.chat", module)
    monkeypatch.setenv("EMERGENT_LLM_KEY", "test-only-not-a-key")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    path = Path(__file__).resolve().parents[2] / "backend/ai_autonomy_router.py"
    spec = importlib.util.spec_from_file_location("legacy_autonomy_contract", path)
    router = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(router)
    result = asyncio.run(router.generate_npc_message(
        {"npc_id": "mira", "name": "Mira", "personality": {"curious": .9}},
        {"topic": "soil"}, [{"speaker": "Player", "content": "Compare soil?"}],
    ))
    assert result == "Let's compare the soil samples before deciding."
    assert calls["api_key"] == "test-only-not-a-key"
