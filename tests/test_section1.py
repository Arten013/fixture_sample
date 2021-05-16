from unittest.mock import patch
import random

import pytest
from pytest import fixture

from mymodule import ObjectWithDB


# fixtureの例


@fixture
def values():
    return [2, 1, 3]


@fixture
def sorted_values():
    return [1, 2, 3]


def test_sorted(values, sorted_values):
    assert sorted(values) == sorted_values


# 値を返さないfixture


@fixture
def set_seed():
    random.seed(0)


@pytest.mark.usefixtures("set_seed")
def test_fix_seed():
    rand1 = random.random()
    random.seed(0)
    rand2 = random.random()
    assert rand1 == rand2


# Callableを返すfixture


@fixture
def seed_setter():
    return lambda: random.seed(0)


def test_fix_seed_2(seed_setter):
    seed_setter()
    rand1 = random.random()
    seed_setter()
    rand2 = random.random()
    assert rand1 == rand2


# patchを適用するfixture


@fixture
def ignore_db_connection():
    with patch("mymodule.ObjectWithDB.connect"):
        yield


@pytest.mark.usefixtures("ignore_db_connection")
def test_db():
    ObjectWithDB().connect()


@fixture
@pytest.mark.usefixtures("set_seed")
def random_value():
    return random.random()


@pytest.mark.xfail(reason="set_seed not applied to fixture", strict=True)
def test_rand_fail(random_value, seed_setter):
    seed_setter()
    assert random_value == random.random()
