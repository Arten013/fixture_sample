from pathlib import Path

from pytest import fixture

from .fixtures import global_fixture_2


@fixture
def global_fixture():
    return "foobar"


@fixture
def conftest_chain_fixture():
    return [1, 2]


@fixture
def tmpdir_with_print(tmpdir):
    print(tmpdir)
    return tmpdir