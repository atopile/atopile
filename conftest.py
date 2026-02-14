import pytest


def _clear_node_type_caches() -> None:
    """Best-effort cleanup for global FabLL type registries between tests."""
    try:
        from faebryk.core.node import Node
    except Exception:
        # Some tests may not have faebryk importable/initialized yet.
        return

    for cls in list(Node._seen_types.values()):
        if hasattr(cls, "_type_cache"):
            cls._type_cache.clear()
    Node._seen_types.clear()


@pytest.fixture(autouse=True)
def clear_node_type_caches_global():
    """
    Keep test isolation for both `test/**` and co-located `src/**` tests.

    Node type registration is process-global; without this, sequential tests in the
    same worker can collide on repeated local class names.
    """
    _clear_node_type_caches()
    yield
    _clear_node_type_caches()
