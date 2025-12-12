import types
import sys

import numpy as np
import pytest

import app.search_utils as su


def test_generate_embedding_mocked():
    emb = su.generate_embedding("hello world")
    assert emb == [0.1, 0.2, 0.3]

    empty = su.generate_embedding("")
    assert empty is None


def test_get_model_lazy_singleton(monkeypatch):
    """
    Ensure get_model uses a singleton and does NOT try to load the real SentenceTransformer.
    """
    # Reset internal model reference
    su._model = None

    # Create dummy module with DummyTransformer
    calls = {"count": 0}

    class DummyTransformer:
        def __init__(self, name):
            calls["count"] += 1
            self.name = name

        def encode(self, text):
            return np.array([0.1, 0.2, 0.3])

    dummy_module = types.SimpleNamespace(SentenceTransformer=DummyTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", dummy_module)

    m1 = su.get_model()
    m2 = su.get_model()

    assert m1 is m2
    assert calls["count"] == 1  # constructed only once


def test_cosine_similarity_various():
    v1 = [1, 0, 0]
    v2 = [1, 0, 0]
    v3 = [0, 1, 0]

    assert abs(su.cosine_similarity(v1, v2) - 1.0) < 1e-6
    assert abs(su.cosine_similarity(v1, v3)) < 1e-6
    assert su.cosine_similarity(None, v2) == 0.0
    assert su.cosine_similarity(v1, None) == 0.0
    assert su.cosine_similarity([0, 0, 0], [1, 2, 3]) == 0.0
