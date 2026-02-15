from __future__ import annotations

import re
import sqlite3
import threading
from collections.abc import Collection
from pathlib import Path
from urllib.parse import quote

from .interfaces import (
    ComponentCandidate,
    FastLookupStore,
    NumericRange,
    ParameterQuery,
    QueryValidationError,
    SnapshotNotFoundError,
    SnapshotSchemaError,
)
from .query_normalization import (
    _QUERY_ALIASES,
    expanded_range_bounds,
    normalize_package,
)

_VALID_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FAST_TABLES = {
    "resistor": "resistor_pick",
    "capacitor": "capacitor_pick",
    "capacitor_polarized": "capacitor_polarized_pick",
    "inductor": "inductor_pick",
    "diode": "diode_pick",
    "led": "led_pick",
    "bjt": "bjt_pick",
    "mosfet": "mosfet_pick",
}
_CANDIDATE_CORE_COLUMNS = {"lcsc_id", "stock", "is_basic", "is_preferred"}
_REQUIRED_FAST_COLUMNS = {"lcsc_id", "stock", "is_basic", "is_preferred"}
_RANGE_COLUMN_BOUNDS = {
    "resistance_ohm": ("resistance_min_ohm", "resistance_max_ohm"),
    "capacitance_f": ("capacitance_min_f", "capacitance_max_f"),
    "inductance_h": ("inductance_min_h", "inductance_max_h"),
}


def _sqlite_readonly_uri(path: Path) -> str:
    resolved = str(path.resolve())
    escaped = quote(resolved, safe="/")
    return f"file:{escaped}?mode=ro&immutable=1"


def _quote_ident(identifier: str) -> str:
    if not _VALID_IDENTIFIER.fullmatch(identifier):
        raise SnapshotSchemaError(f"Unsafe SQL identifier: {identifier!r}")
    return f'"{identifier}"'


class SQLiteFastLookupStore(FastLookupStore):
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._thread_local = threading.local()
        self._cache_lock = threading.Lock()
        self._table_columns_cache: dict[str, frozenset[str]] = {}
        self._table_column_order_cache: dict[str, tuple[str, ...]] = {}
        self._order_sql_cache: dict[str, str] = {}

    def query_resistors(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self._query_table("resistor", _FAST_TABLES["resistor"], query)

    def query_capacitors(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self._query_table("capacitor", _FAST_TABLES["capacitor"], query)

    def query_capacitors_polarized(
        self, query: ParameterQuery
    ) -> list[ComponentCandidate]:
        return self._query_table(
            "capacitor_polarized",
            _FAST_TABLES["capacitor_polarized"],
            query,
        )

    def query_inductors(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self._query_table("inductor", _FAST_TABLES["inductor"], query)

    def query_diodes(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self._query_table("diode", _FAST_TABLES["diode"], query)

    def query_leds(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self._query_table("led", _FAST_TABLES["led"], query)

    def query_bjts(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self._query_table("bjt", _FAST_TABLES["bjt"], query)

    def query_mosfets(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self._query_table("mosfet", _FAST_TABLES["mosfet"], query)

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise SnapshotNotFoundError(f"fast snapshot DB not found: {self.db_path}")
        cached_path = getattr(self._thread_local, "db_path", None)
        cached_conn = getattr(self._thread_local, "conn", None)
        if cached_conn is not None and cached_path == self.db_path:
            return cached_conn
        try:
            conn = sqlite3.connect(_sqlite_readonly_uri(self.db_path), uri=True)
        except sqlite3.Error as exc:
            raise SnapshotSchemaError(f"failed to open fast DB: {exc}") from exc
        conn.execute("pragma query_only=ON")
        conn.execute("pragma foreign_keys=OFF")
        conn.execute("pragma synchronous=OFF")
        conn.execute("pragma temp_store=MEMORY")
        self._thread_local.conn = conn
        self._thread_local.db_path = self.db_path
        return conn

    def _table_columns(self, conn: sqlite3.Connection, table: str) -> frozenset[str]:
        cached = self._table_columns_cache.get(table)
        if cached is not None:
            return cached
        rows = conn.execute(f"pragma table_info({_quote_ident(table)})").fetchall()
        if not rows:
            raise SnapshotSchemaError(f"Missing required table: {table}")
        columns = frozenset(str(row[1]) for row in rows)
        column_order = tuple(str(row[1]) for row in rows)
        with self._cache_lock:
            existing = self._table_columns_cache.get(table)
            if existing is not None:
                return existing
            self._table_columns_cache[table] = columns
            self._table_column_order_cache[table] = column_order
        return columns

    def _query_table(
        self, component_type: str, table: str, query: ParameterQuery
    ) -> list[ComponentCandidate]:
        conn = self._connect()
        columns = self._table_columns(conn, table)
        missing_columns = sorted(_REQUIRED_FAST_COLUMNS.difference(columns))
        if missing_columns:
            raise SnapshotSchemaError(
                f"{table} missing required columns: {missing_columns}"
            )

        where, params = self._build_filters(
            component_type=component_type,
            query=query,
            columns=columns,
        )
        where_sql = f" where {' and '.join(where)}" if where else ""
        order_sql = self._build_order_sql(table, columns)
        sql = f"select * from {_quote_ident(table)}{where_sql}{order_sql} limit ?"
        try:
            rows = conn.execute(sql, [*params, query.limit]).fetchall()
        except sqlite3.Error as exc:
            raise SnapshotSchemaError(
                f"failed querying fast table {table}: {exc}"
            ) from exc
        column_order = self._table_column_order_cache.get(table)
        if column_order is None:
            raise SnapshotSchemaError(f"Missing column order cache for table: {table}")
        index_by_column = {name: idx for idx, name in enumerate(column_order)}
        core_indexes = {
            key: index_by_column[key]
            for key in _CANDIDATE_CORE_COLUMNS
            if key in index_by_column
        }
        pick_columns = [
            (idx, name)
            for idx, name in enumerate(column_order)
            if name not in _CANDIDATE_CORE_COLUMNS
        ]

        out: list[ComponentCandidate] = []
        for row in rows:
            pick_params = {name: row[idx] for idx, name in pick_columns}
            out.append(
                ComponentCandidate(
                    lcsc_id=int(row[core_indexes["lcsc_id"]]),
                    stock=_as_int_or_none(row[core_indexes["stock"]]),
                    is_basic=_as_bool_or_none(row[core_indexes["is_basic"]]),
                    is_preferred=_as_bool_or_none(row[core_indexes["is_preferred"]]),
                    pick_parameters=pick_params,
                )
            )
        return out

    def _build_order_sql(self, table: str, columns: Collection[str]) -> str:
        cached = self._order_sql_cache.get(table)
        if cached is not None:
            return cached
        order_terms: list[str] = []
        if "is_preferred" in columns:
            order_terms.append(f"{_quote_ident('is_preferred')} desc")
        if "is_basic" in columns:
            order_terms.append(f"{_quote_ident('is_basic')} desc")
        if "stock" in columns:
            order_terms.append(f"{_quote_ident('stock')} desc")
        order_terms.append(f"{_quote_ident('lcsc_id')} asc")
        order_sql = f" order by {', '.join(order_terms)}"
        with self._cache_lock:
            existing = self._order_sql_cache.get(table)
            if existing is not None:
                return existing
            self._order_sql_cache[table] = order_sql
        return order_sql

    def _build_filters(
        self,
        *,
        component_type: str,
        query: ParameterQuery,
        columns: Collection[str],
    ) -> tuple[list[str], list[object]]:
        where: list[str] = []
        params: list[object] = []

        if query.qty and "stock" in columns:
            where.append(f"{_quote_ident('stock')} >= ?")
            params.append(query.qty)

        if query.package is not None:
            self._require_column(columns, "package")
            normalized_package = normalize_package(component_type, query.package)
            if normalized_package is None:
                raise QueryValidationError("package cannot be empty")
            where.append(f"{_quote_ident('package')} = ?")
            params.append(normalized_package)

        for key, value in sorted(query.exact.items()):
            column = self._resolve_query_column(columns, key)
            where.append(f"{_quote_ident(column)} = ?")
            params.append(_to_sql_value(value))

        for key, numeric_range in sorted(query.ranges.items()):
            column = self._resolve_query_column(columns, key)
            lower_bound, upper_bound = expanded_range_bounds(numeric_range)
            if (
                column in _RANGE_COLUMN_BOUNDS
                and _RANGE_COLUMN_BOUNDS[column][0] in columns
                and _RANGE_COLUMN_BOUNDS[column][1] in columns
            ):
                min_col, max_col = _RANGE_COLUMN_BOUNDS[column]
                if lower_bound is not None:
                    where.append(f"{_quote_ident(min_col)} >= ?")
                    params.append(lower_bound)
                if upper_bound is not None:
                    where.append(f"{_quote_ident(max_col)} <= ?")
                    params.append(upper_bound)
                continue

            if lower_bound is not None:
                where.append(f"{_quote_ident(column)} >= ?")
                params.append(lower_bound)
            if upper_bound is not None:
                where.append(f"{_quote_ident(column)} <= ?")
                params.append(upper_bound)

        return where, params

    def _resolve_query_column(self, columns: Collection[str], raw_name: str) -> str:
        canonical = _QUERY_ALIASES.get(raw_name, raw_name)
        self._require_column(columns, canonical)
        return canonical

    def _require_column(self, columns: Collection[str], name: str) -> None:
        if name not in columns:
            raise QueryValidationError(f"Unknown filter column: {name}")


def _to_sql_value(value: object) -> object:
    if isinstance(value, bool):
        return 1 if value else 0
    return value


def _as_bool_or_none(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _as_int_or_none(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def test_sqlite_fast_lookup_store_filters_and_orders(tmp_path) -> None:
    db_path = tmp_path / "fast.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            create table resistor_pick (
                lcsc_id integer primary key,
                package text,
                resistance_ohm real,
                tolerance_pct real,
                stock integer,
                is_basic integer,
                is_preferred integer
            )
        """)
        conn.execute("""
            create table capacitor_pick (
                lcsc_id integer primary key,
                package text,
                capacitance_f real,
                voltage_v real,
                stock integer,
                is_basic integer,
                is_preferred integer
            )
        """)
        conn.executemany(
            """
            insert into resistor_pick (
                lcsc_id,
                package,
                resistance_ohm,
                tolerance_pct,
                stock,
                is_basic,
                is_preferred
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1001, "0603", 1000.0, 1.0, 25, 1, 1),
                (1002, "0603", 1100.0, 5.0, 999, 1, 0),
                (1003, "0805", 1000.0, 1.0, 1000, 0, 0),
            ],
        )

    store = SQLiteFastLookupStore(db_path)
    result = store.query_resistors(
        ParameterQuery(
            qty=10,
            limit=10,
            package="0603",
            ranges={"resistance_ohm": NumericRange(minimum=900.0, maximum=1200.0)},
        )
    )
    assert len(result) == 2
    assert result[0].lcsc_id == 1001
    assert result[1].lcsc_id == 1002


def test_sqlite_fast_lookup_store_unknown_column_raises(tmp_path) -> None:
    db_path = tmp_path / "fast.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            create table resistor_pick (
                lcsc_id integer primary key,
                stock integer,
                is_basic integer,
                is_preferred integer
            )
        """)
        conn.execute("""
            create table capacitor_pick (
                lcsc_id integer primary key,
                stock integer,
                is_basic integer,
                is_preferred integer
            )
        """)

    store = SQLiteFastLookupStore(db_path)
    try:
        store.query_resistors(ParameterQuery(exact={"resistance_ohm": 1000.0}))
    except QueryValidationError as exc:
        assert "Unknown filter column" in str(exc)
    else:
        assert False, "Expected QueryValidationError"


def test_sqlite_fast_lookup_store_missing_db_raises(tmp_path) -> None:
    store = SQLiteFastLookupStore(tmp_path / "missing-fast.sqlite")
    try:
        store.query_resistors(ParameterQuery())
    except SnapshotNotFoundError as exc:
        assert "fast snapshot DB not found" in str(exc)
    else:
        assert False, "Expected SnapshotNotFoundError"


def test_sqlite_fast_lookup_store_missing_required_column_raises(tmp_path) -> None:
    db_path = tmp_path / "fast.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("create table resistor_pick (lcsc_id integer primary key)")
        conn.execute("create table capacitor_pick (lcsc_id integer primary key)")

    store = SQLiteFastLookupStore(db_path)
    try:
        store.query_resistors(ParameterQuery())
    except SnapshotSchemaError as exc:
        assert "missing required columns" in str(exc)
    else:
        assert False, "Expected SnapshotSchemaError"


def test_sqlite_fast_lookup_store_supports_stage2_bounds_and_aliases(tmp_path) -> None:
    db_path = tmp_path / "fast.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            create table resistor_pick (
                lcsc_id integer primary key,
                package text,
                stock integer,
                is_basic integer,
                is_preferred integer,
                resistance_ohm real,
                resistance_min_ohm real,
                resistance_max_ohm real
            )
        """)
        conn.execute("""
            create table capacitor_pick (
                lcsc_id integer primary key,
                package text,
                stock integer,
                is_basic integer,
                is_preferred integer,
                capacitance_f real,
                capacitance_min_f real,
                capacitance_max_f real
            )
        """)
        conn.executemany(
            """
            insert into resistor_pick (
                lcsc_id,
                package,
                stock,
                is_basic,
                is_preferred,
                resistance_ohm,
                resistance_min_ohm,
                resistance_max_ohm
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "0402", 100, 1, 1, 10_000.0, 9_900.0, 10_100.0),
                (2, "0402", 100, 1, 0, 10_000.0, 8_000.0, 12_000.0),
            ],
        )

    store = SQLiteFastLookupStore(db_path)
    result = store.query_resistors(
        ParameterQuery(
            package="0402",
            ranges={"resistance": NumericRange(minimum=9_500.0, maximum=10_500.0)},
        )
    )
    assert [candidate.lcsc_id for candidate in result] == [1]

    result_prefixed = store.query_resistors(
        ParameterQuery(
            package="R0402",
            ranges={"resistance": NumericRange(minimum=9_500.0, maximum=10_500.0)},
        )
    )
    assert [candidate.lcsc_id for candidate in result_prefixed] == [1]

    near_edge = store.query_resistors(
        ParameterQuery(
            package="0402",
            ranges={
                "resistance": NumericRange(
                    minimum=9_900.05,
                    maximum=10_099.95,
                )
            },
        )
    )
    assert [candidate.lcsc_id for candidate in near_edge] == [1]


def test_sqlite_fast_lookup_store_supports_new_component_tables(tmp_path) -> None:
    db_path = tmp_path / "fast.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            create table inductor_pick (
                lcsc_id integer primary key,
                package text,
                stock integer,
                is_basic integer,
                is_preferred integer,
                inductance_h real,
                inductance_min_h real,
                inductance_max_h real,
                max_current_a real,
                dc_resistance_ohm real
            );
            create table mosfet_pick (
                lcsc_id integer primary key,
                package text,
                stock integer,
                is_basic integer,
                is_preferred integer,
                channel_type text,
                max_drain_source_voltage_v real,
                max_continuous_drain_current_a real,
                on_resistance_ohm real
            );
            """
        )
        conn.execute(
            """
            insert into inductor_pick values
            (1, '0805', 100, 1, 1, 1e-5, 0.9e-5, 1.1e-5, 1.5, 0.05)
            """
        )
        conn.execute(
            """
            insert into mosfet_pick values
            (2, 'SOT-23', 200, 0, 1, 'N_CHANNEL', 30.0, 2.0, 0.05)
            """
        )
        conn.commit()

    store = SQLiteFastLookupStore(db_path)
    inductor_candidates = store.query_inductors(
        ParameterQuery(
            package="L0805",
            ranges={"inductance": NumericRange(minimum=0.89e-5, maximum=1.11e-5)},
        )
    )
    mosfet_candidates = store.query_mosfets(
        ParameterQuery(
            exact={"channel_type": "N_CHANNEL"},
            ranges={
                "on_resistance": NumericRange(maximum=0.1),
                "max_drain_source_voltage": NumericRange(minimum=20.0),
            },
        )
    )
    assert [candidate.lcsc_id for candidate in inductor_candidates] == [1]
    assert [candidate.lcsc_id for candidate in mosfet_candidates] == [2]
