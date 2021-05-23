from pytest import fixture
import pytest

# recursive dependency error の例
@fixture
def cycle_1(cycle_3):
    return cycle_3

@fixture
def cycle_2(cycle_1):
    return cycle_1

@fixture
def cycle_3(cycle_2):
    return cycle_2

@pytest.mark.xfail(reason="cyclic fixture dependency", strict=True)
def test_cycle_fixt(cycle_3):
    ...

@pytest.fixture
def recursive_fixture(recursive_fixture):
    ...

@pytest.mark.xfail(reason="recursive fixture dependency", strict=True)
def test_recursive_fixture(cycle_3):
    ...

# predefinedなfixtureを上書き
def test_predefined_fixture_update(tmpdir_with_print):
    ...

@fixture
def foo_fixture():
    return [1, 2, 3]


def test_foo(foo_fixture):
    assert foo_fixture == [1, 2, 3]


class TestFoo:
    @fixture
    def foo_fixture(self, foo_fixture):
        return foo_fixture + [4, 5]

    def test_foo(self, foo_fixture):
        assert foo_fixture == [1, 2, 3, 4, 5]


@fixture
def conftest_chain_fixture(conftest_chain_fixture):
    return conftest_chain_fixture + [3, 4]


def test_conftest_chain(conftest_chain_fixture):
    assert conftest_chain_fixture == [1, 2, 3, 4]


class TestBase():
    EXPECTED = [1, 2]

    @fixture
    def inherit_fixture(self):
        return [1, 2]

    def test_inherit_fixture(self, inherit_fixture):
        assert inherit_fixture == self.EXPECTED

@pytest.mark.xfail(reason="inherit_fixture of child class is overwritten.", strict=True)
class TestInherit(TestBase):
    EXPECTED = [1, 2, 3, 4]

    @fixture
    def inherit_fixture(self, inherit_fixture):
        return inherit_fixture + [3, 4]

@fixture
def inherit_fixture_work():
    return [1, 2]

class TestBaseWork():
    EXPECTED = [1, 2]

    def test_inherit_fixture(self, inherit_fixture_work):
        assert inherit_fixture_work == self.EXPECTED

class TestInheritWork(TestBaseWork):
    EXPECTED = [1, 2, 3, 4]

    @fixture
    def inherit_fixture_work(self, inherit_fixture_work):
        return inherit_fixture_work + [3, 4]


@fixture
def l():
    print("fofofof")
    return []


@pytest.mark.parametrize(
    "v",
    [1, 2, 3]
)
def test_l(v, l):
    l.append(v)
    print(l)
    assert l == [v]