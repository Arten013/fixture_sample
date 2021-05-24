from pytest import fixture

# fixtureスコープがfunction
@fixture
def foo():
    print("start")
    yield
    print("end")


def test_1(foo):
    print("test1")


def test_2(foo):
    print("test2")


# fixtureスコープがsession
@fixture(scope="session")
def foo_session():
    print("start")
    yield
    print("end")


def test_1_session(foo_session):
    print(f"test1 (id={id(foo_session)})")


def test_2_session(foo_session):
    print(f"test2 (id={id(foo_session)})")
