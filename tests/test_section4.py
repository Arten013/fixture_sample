from pytest import fixture
import pytest


# テスト間の意図しない依存関係
@fixture(scope="session")
def ids():
    return [3, 1, 4]


def test_ids_sort(ids):
    ids.sort()
    assert ids == [1, 3, 4]


@pytest.mark.xfail(strict=True, reason="immutable fixture is reused.")
def test_ids_pop(ids):
    ids.pop()
    assert ids == [3, 1]


# 広いfixtureスコープから狭いfixtureスコープは呼べないという例
@fixture
def foo():
    ...

@fixture(scope="session")
def foo_session(foo):
    ...

@pytest.mark.xfail(strict=True, reason="function scope fixture is called by session scope fixture.")
def test_scope_contradict(foo_session):
    ...