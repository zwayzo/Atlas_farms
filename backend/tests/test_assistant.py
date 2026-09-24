import sys
import types

import pytest

from app.engine import assistant


def test_no_key_and_unknown_question(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    assert assistant.is_configured() is False
    monkeypatch.setenv('GROQ_API_KEY', 'test-only')
    with pytest.raises(ValueError, match='Unknown question_id'):
        assistant.ask_assistant('unsupported', {})


def test_grounded_answer_and_rejection_of_unknown_id(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-only')
    monkeypatch.setenv('GROQ_MODEL', 'available-test-model')
    answer = ['C02 is partial because Segment A supply is insufficient.']
    called_models = []

    class Chat:
        completions = None

        def create(self, **kwargs):
            called_models.append(kwargs['model'])
            return types.SimpleNamespace(choices=[types.SimpleNamespace(
                message=types.SimpleNamespace(content=answer[0]))])

    class Groq:
        def __init__(self, **kwargs):
            self.chat = types.SimpleNamespace(completions=Chat())

    monkeypatch.setitem(sys.modules, 'groq', types.SimpleNamespace(Groq=Groq))
    context = {'client_statuses': {'C02': {'status': 'PARTIAL'}}, 'local_residual': [], 'kpis': {}}
    assert assistant.ask_assistant('at_risk', context)['evidence_ids'] == ['C02']
    assert called_models == ['available-test-model']
    answer[0] = 'C99 is partial.'
    with pytest.raises(RuntimeError, match='UNGROUNDED_ID'):
        assistant.ask_assistant('at_risk', context)


def test_provider_failure_is_reported(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-only')
    class FailingGroq:
        def __init__(self, **kwargs):
            raise TimeoutError('request timed out')
    monkeypatch.setitem(sys.modules, 'groq', types.SimpleNamespace(Groq=FailingGroq))
    with pytest.raises(RuntimeError, match='PROVIDER_FAILURE'):
        assistant.ask_assistant('at_risk', {'client_statuses': {}})


def test_unavailable_model_has_actionable_error(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-only')
    monkeypatch.setenv('GROQ_MODEL', 'unavailable-test-model')

    class ModelNotFound(Exception):
        status_code = 404

    class Groq:
        def __init__(self, **kwargs):
            self.chat = types.SimpleNamespace(completions=self)

        def create(self, **kwargs):
            raise ModelNotFound('model_not_found')

    monkeypatch.setitem(sys.modules, 'groq', types.SimpleNamespace(Groq=Groq))
    with pytest.raises(RuntimeError, match='MODEL_UNAVAILABLE: unavailable-test-model'):
        assistant.ask_assistant('at_risk', {'client_statuses': {}})
