from pytest import fixture
import pytest


@fixture(scope="session")
def ids():
    return [3, 1, 4]


def test_ids_sort(ids):
    ids.sort()
    assert ids == [1, 3, 4]


@pytest.mark.xfail()
def test_ids_pop(ids):
    ids.pop()
    assert ids == [3, 1]
