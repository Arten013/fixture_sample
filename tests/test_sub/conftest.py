from pytest import fixture


@fixture
def conftest_chain_fixture(conftest_chain_fixture):
    return conftest_chain_fixture + [3, 4]
