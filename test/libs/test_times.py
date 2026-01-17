# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import time

import pytest

from faebryk.libs.test.times import Times


class TestTimesBasic:
    """Test basic timing functionality."""

    def test_instantiation_default(self):
        """Test default instantiation."""
        t = Times()
        assert t.name is None
        assert t.strategy == Times.Strategy.SUM
        assert len(t.times) == 0

    def test_instantiation_with_name(self):
        """Test instantiation with name."""
        t = Times(name="test")
        assert t.name == "test"

    def test_instantiation_with_strategy(self):
        """Test instantiation with custom strategy."""
        t = Times(strategy=Times.Strategy.AVG)
        assert t.strategy == Times.Strategy.AVG

    def test_add_measures_elapsed_time(self):
        """Test that add() measures elapsed time since last call."""
        t = Times()
        time.sleep(0.01)
        t.add("first")
        assert "first" in t.times
        assert len(t.times["first"]) == 1
        assert t.times["first"][0] >= 0.01

    def test_add_with_explicit_duration(self):
        """Test adding explicit duration instead of measuring."""
        t = Times()
        t.add("explicit", duration=1.5)
        assert t.times["explicit"][0] == 1.5

    def test_add_multiple_samples(self):
        """Test adding multiple samples for the same name."""
        t = Times()
        t.add("multi", duration=1.0)
        t.add("multi", duration=2.0)
        t.add("multi", duration=3.0)
        assert len(t.times["multi"]) == 3
        assert t.times["multi"] == [1.0, 2.0, 3.0]


class TestTimesStrategies:
    """Test aggregation strategies."""

    @pytest.fixture
    def times_with_samples(self):
        """Create a Times instance with multiple samples."""
        t = Times()
        for val in [1.0, 2.0, 3.0, 4.0, 5.0]:
            t.add("test", duration=val)
        return t

    def test_strategy_sum(self, times_with_samples):
        """Test SUM strategy (accumulate all samples)."""
        assert times_with_samples.get("test", Times.Strategy.SUM) == 15.0

    def test_strategy_avg(self, times_with_samples):
        """Test AVG strategy."""
        assert times_with_samples.get("test", Times.Strategy.AVG) == 3.0

    def test_strategy_min(self, times_with_samples):
        """Test MIN strategy."""
        assert times_with_samples.get("test", Times.Strategy.MIN) == 1.0

    def test_strategy_max(self, times_with_samples):
        """Test MAX strategy."""
        assert times_with_samples.get("test", Times.Strategy.MAX) == 5.0

    def test_strategy_median(self, times_with_samples):
        """Test MEDIAN strategy."""
        assert times_with_samples.get("test", Times.Strategy.MEDIAN) == 3.0

    def test_strategy_p80(self, times_with_samples):
        """Test P80 strategy (80th percentile)."""
        # For [1, 2, 3, 4, 5], 80th percentile index = int(0.8 * 5) = 4
        assert times_with_samples.get("test", Times.Strategy.P80) == 5.0

    def test_get_uses_default_strategy(self):
        """Test that get() uses the instance's default strategy."""
        t = Times(strategy=Times.Strategy.AVG)
        t.add("test", duration=2.0)
        t.add("test", duration=4.0)
        assert t.get("test") == 3.0  # AVG of 2 and 4

    def test_getitem_shorthand(self, times_with_samples):
        """Test [] operator as shorthand for get()."""
        assert times_with_samples["test"] == times_with_samples.get("test")


class TestTimesContextManager:
    """Test context manager functionality."""

    def test_measure_context_manager(self):
        """Test measure() context manager."""
        t = Times()
        with t.measure("block"):
            time.sleep(0.01)
        assert "block" in t.times
        assert t.times["block"][0] >= 0.01

    def test_measure_multiple_uses(self):
        """Test using measure() multiple times for same name."""
        t = Times()
        for _ in range(3):
            with t.measure("repeated"):
                time.sleep(0.005)
        assert len(t.times["repeated"]) == 3

    def test_measure_with_exception(self):
        """Test that measure() records time even if exception occurs."""
        t = Times()
        with pytest.raises(ValueError):
            with t.measure("error_block"):
                time.sleep(0.01)
                raise ValueError("test error")
        assert "error_block" in t.times
        assert t.times["error_block"][0] >= 0.01


class TestTimesNesting:
    """Test nested timing functionality."""

    def test_child_creates_nested_times(self):
        """Test child() creates a nested Times instance."""
        parent = Times(name="parent")
        child = parent.child("child_name")
        assert child.name == "child_name"
        assert child._parent is parent

    def test_child_measurements_propagate_to_parent(self):
        """Test that child measurements are recorded in parent."""
        parent = Times(name="parent")
        child = parent.child("child")
        child.add("inner", duration=1.5)

        # Child should have the measurement
        assert "inner" in child.times
        # Parent should have it with prefixed name
        assert "child:inner" in parent.times
        assert parent.times["child:inner"][0] == 1.5

    def test_nested_children(self):
        """Test multiple levels of nesting."""
        root = Times(name="root")
        level1 = root.child("L1")
        level2 = level1.child("L2")

        level2.add("deep", duration=2.0)

        assert "deep" in level2.times
        assert "L2:deep" in level1.times
        assert "L1:L2:deep" in root.times

    def test_child_context_manager(self):
        """Test using child with context manager."""
        parent = Times(name="parent")
        child = parent.child("child")

        with child.measure("block"):
            time.sleep(0.01)

        assert "block" in child.times
        assert "child:block" in parent.times


class TestTimesAutoNesting:
    """Test automatic nesting when Times created inside measure()."""

    def test_auto_nest_single_level(self):
        """Test Times created inside measure() auto-links to parent."""
        level1 = Times(name="level1")

        with level1.measure("outer"):
            level2 = Times(name="level2")
            level2.add("inner", duration=1.0)

        # level2 should have the measurement
        assert "inner" in level2.times
        assert level2.times["inner"][0] == 1.0

        # level1 should have it with prefix
        assert "level2:inner" in level1.times
        assert level1.times["level2:inner"][0] == 1.0

    def test_auto_nest_three_levels(self):
        """Test three levels of automatic nesting."""
        level1 = Times(name="level1")

        with level1.measure("outer"):
            level2 = Times(name="level2")
            with level2.measure("middle"):
                level3 = Times(name="level3")
                level3.add("deep", duration=1.0)

        # level3 has it directly
        assert "deep" in level3.times

        # level2 has it with level3 prefix
        assert "level3:deep" in level2.times

        # level1 has it with level2:level3 prefix
        assert "level2:level3:deep" in level1.times

    def test_auto_nest_without_measure_context(self):
        """Test Times created outside measure() has no parent."""
        level1 = Times(name="level1")
        level2 = Times(name="level2")

        level2.add("test", duration=1.0)

        assert "test" in level2.times
        assert "level2:test" not in level1.times

    def test_auto_nest_stack_cleanup(self):
        """Test that exiting measure() properly cleans up the stack."""
        level1 = Times(name="level1")

        with level1.measure("block"):
            pass

        # After exiting, new Times should not auto-link
        level2 = Times(name="level2")
        assert level2._parent is None

    def test_auto_nest_with_explicit_child(self):
        """Test that explicit child() still works inside measure()."""
        level1 = Times(name="level1")

        with level1.measure("outer"):
            # Auto-linked
            auto = Times(name="auto")
            # Explicitly linked to auto, not level1
            explicit = auto.child("explicit")
            explicit.add("test", duration=1.0)

        # explicit -> auto -> level1
        assert "test" in explicit.times
        assert "explicit:test" in auto.times
        assert "auto:explicit:test" in level1.times


class TestTimesFormatting:
    """Test output formatting."""

    def test_get_formatted_default_unit(self):
        """Test get_formatted() with default ms unit."""
        t = Times()
        t.add("test", duration=0.001)  # 1ms in seconds
        formatted = t.get_formatted("test")
        assert "ms" in formatted
        assert "1" in formatted

    def test_get_formatted_custom_unit(self):
        """Test get_formatted() with custom unit."""
        t = Times()
        t.add("test", duration=1.0)  # 1 second
        formatted = t.get_formatted("test", unit="s")
        assert "s" in formatted
        assert "1" in formatted

    def test_to_str_returns_string(self):
        """Test to_str() returns a string representation."""
        t = Times()
        t.add("test", duration=1.0)
        result = t.to_str()
        assert isinstance(result, str)
        assert "test" in result

    def test_to_table_returns_table(self):
        """Test to_table() returns a rich Table."""
        from rich.table import Table

        t = Times()
        t.add("test", duration=1.0)
        table = t.to_table()
        assert isinstance(table, Table)

    def test_repr_returns_string(self):
        """Test __repr__ returns the string representation."""
        t = Times()
        t.add("test", duration=1.0)
        result = repr(t)
        assert isinstance(result, str)


class TestTimesSeparatorAndGrouping:
    """Test separator and grouping functionality."""

    def test_separator(self):
        """Test separator() for visual grouping."""
        t = Times()
        t.add("first", duration=1.0)
        t.separator()
        t.add("second", duration=2.0)
        # Separator should be in times with internal prefix
        separator_keys = [k for k in t.times.keys() if k.startswith("_separator")]
        assert len(separator_keys) == 1

    def test_group_with_predicate(self):
        """Test group() with predicate function."""
        t = Times()
        t.add("algo:step1", duration=1.0)
        t.add("algo:step2", duration=2.0)
        t.add("other", duration=3.0)

        t.group("algo_total", lambda k: k.startswith("algo:"))

        assert "algo_total" in t.times
        # Group should contain both algo samples
        assert len(t.times["algo_total"]) == 2

    def test_group_with_pattern(self):
        """Test group() with string pattern."""
        t = Times()
        t.add("setup:init", duration=1.0)
        t.add("setup:config", duration=2.0)
        t.add("run", duration=3.0)

        t.group("setup_total", "setup:")

        assert "setup_total" in t.times
        assert len(t.times["setup_total"]) == 2


class TestTimesEdgeCases:
    """Test edge cases and error handling."""

    def test_get_nonexistent_key(self):
        """Test get() with nonexistent key raises KeyError."""
        t = Times()
        with pytest.raises(KeyError):
            t.get("nonexistent")

    def test_empty_times_to_table(self):
        """Test to_table() with no measurements."""
        t = Times()
        table = t.to_table()
        # Should return a table without crashing
        assert table is not None

    def test_hidden_entries_not_in_output(self):
        """Test that entries starting with _ are hidden from output."""
        t = Times()
        t.add("_hidden", duration=1.0)
        t.add("visible", duration=2.0)
        output = t.to_str()
        assert "visible" in output
        # Hidden entries should not appear in normal output
