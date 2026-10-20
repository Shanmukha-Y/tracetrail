"""Collection policy checks use dummy collector metadata, not nested tests."""

from types import SimpleNamespace

import pytest

import conftest as budget


def test_collection_budget_rejects_51_even_after_deselection():
    config = SimpleNamespace(stash=pytest.Stash())
    session = SimpleNamespace(config=config, items=[])
    budget.pytest_sessionstart(session)
    assert config.stash[budget.COLLECTED_CASES] == 0
    # Previously collected metadata survives a later empty selected-item list.
    config.stash[budget.COLLECTED_CASES] = 50
    budget.pytest_itemcollected(SimpleNamespace(config=config))
    assert config.stash[budget.COLLECTED_CASES] == 51
    with pytest.raises(pytest.UsageError, match="Collected 51 test cases"):
        budget.pytest_collection_finish(session)
