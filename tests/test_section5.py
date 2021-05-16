from pytest import fixture
import pytest


@fixture
def foo_fixt():
    return "foo"


def test_foo(foo_fixt):
    assert foo_fixt == "foo"


foo_var = "foo"


def test_foo_2():
    assert foo_var == "foo"


class TestBar:
    @fixture
    def bar_fixt(self):
        return "bar"

    def test_bar(self, bar_fixt):
        assert bar_fixt == "bar"

    bar_var = "bar"
    ref_bar_var = bar_var

    def test_bar_2(self):
        assert type(self).bar_var == "bar"

    @fixture
    def bar_fixt_2(self):
        return type(self).bar_var

    def test_bar_3(self, bar_fixt_2):
        assert bar_fixt_2 == "bar"


def test_conftest_fixture(global_fixture):
    assert global_fixture == "foobar"


def test_conftest_fixture2(global_fixture_2):
    assert global_fixture_2 == "foofoo"
