"""Count every collected case, including parameters and later deselections."""

import pytest

MAX_TEST_CASES = 50
COLLECTED_CASES = pytest.StashKey[int]()


def pytest_sessionstart(session):
    session.config.stash[COLLECTED_CASES] = 0


def pytest_itemcollected(item):
    item.config.stash[COLLECTED_CASES] += 1


def pytest_collection_finish(session):
    count = session.config.stash[COLLECTED_CASES]
    if count > MAX_TEST_CASES:
        raise pytest.UsageError(
            f"Collected {count} test cases; TraceTrail's limit is {MAX_TEST_CASES}. "
            "Replace lower-priority cases instead of hiding or disabling tests. "
            "Parameterized and deselected cases count toward the limit."
        )
