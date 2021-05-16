from pytest import fixture


@fixture
def conftest_chain_fixture(conftest_chain_fixture):
    return conftest_chain_fixture + [5, 6]


def test_conftest_chain(conftest_chain_fixture):
    assert conftest_chain_fixture == [1, 2, 3, 4, 5, 6]
