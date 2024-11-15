import pytest

from atopile.loop_soup import LoopItem, LoopSoup


def assert_loop_is_lonely(loop: LoopItem) -> None:
    """Assert that a loop is lonely"""
    assert loop.next is loop
    assert loop.prev is loop


def test_lonely_loop():
    """Test that a lonely loop is lonely"""
    loop = LoopItem(1)
    assert loop.represents == 1

    assert_loop_is_lonely(loop)

    assert len(list(loop)) == 1
    # connect to self
    LoopItem.join(loop, loop)

    assert_loop_is_lonely(loop)


def test_joining_two_loney_loops():
    """Test that joining two loops works"""
    loop1 = LoopItem(1)
    loop2 = LoopItem(2)

    assert_loop_is_lonely(loop1)
    assert_loop_is_lonely(loop2)

    LoopItem.join(loop1, loop2)

    assert loop1.next is loop2
    assert loop1.prev is loop2
    assert loop2.next is loop1
    assert loop2.prev is loop1

    assert list(loop1) == [1, 2]
    assert list(loop2) == [2, 1]


@pytest.mark.parametrize("lonely_first", [True, False])
def test_joining_lonely_with_many_loop(lonely_first: bool):
    lonely = LoopItem(1)
    assert_loop_is_lonely(lonely)

    many = LoopItem(2)
    for i in range(3, 10):
        LoopItem.join(many, LoopItem(i))

    if lonely_first:
        LoopItem.join(lonely, many)
    else:
        LoopItem.join(many, lonely)

    assert set(lonely) == set(many) == set(range(1, 10))


def test_joining_many_with_many():
    many1 = LoopItem(1)
    for i in range(2, 5):
        LoopItem.join(many1, LoopItem(i))

    many2 = LoopItem(5)
    for i in range(6, 10):
        LoopItem.join(many2, LoopItem(i))

    LoopItem.join(many1, many2)

    assert set(many1) == set(many2) == set(range(1, 10))


def test_joining_loop_onto_itself():
    itself1 = LoopItem(1)
    itself2 = LoopItem(2)
    itself3 = LoopItem(3)
    itself4 = LoopItem(4)

    LoopItem.join(itself1, itself2)
    LoopItem.join(itself2, itself3)
    LoopItem.join(itself3, itself4)

    LoopItem.join(itself1, itself3)

    assert set(itself1) == set(itself2) == set(itself3) == set(itself4)


def test_limit():
    loop = LoopItem(1)
    for i in range(2, 10):
        LoopItem.join(loop, LoopItem(i))

    with pytest.raises(RuntimeError):
        list(loop.iter_values(limit=5))


def test_loop_soup():
    soup = LoopSoup(id)
    assert len(list(soup.groups())) == 0

    for i in range(10):
        soup.add(i)

    assert len(list(soup.groups())) == 10
    for i, group in enumerate(soup.groups()):
        assert len(group) == 1
        assert group[0] == i

    for i in range(0, 10, 2):
        soup.join(i, i + 1)

    assert len(list(soup.groups())) == 5
    for i, group in enumerate(soup.groups()):
        a, b = group
        assert len(group) == 2
        assert a == i * 2
        assert b == a + 1
