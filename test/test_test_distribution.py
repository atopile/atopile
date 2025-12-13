import os
import random

import pytest


class Unserializable:
    def __init__(self):
        self.value = random.randint(0, 100)
        self.pid = os.getpid()

    def __repr__(self):
        return f"Unserializable({self.value}, {self.pid})"


examples = [Unserializable() for _ in range(10)]


@pytest.mark.parametrize("example", examples)
def test_test_distribution(example):
    print(examples)
    print(example.value)
    print(example.pid)
    assert example.value is not None
