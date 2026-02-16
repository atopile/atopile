from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import threading
from collections.abc import Sequence
from pathlib import Path

from .fast_lookup_sqlite import _quote_ident
from .interfaces import (
    BatchQueryValidationError,
    ComponentCandidate,
    FastLookupStore,
    ParameterQuery,
    QueryValidationError,
    SnapshotNotFoundError,
    SnapshotSchemaError,
)
from .query_normalization import (
    _QUERY_ALIASES,
    expanded_range_bounds_for_column,
    normalize_exact_filter_value,
    normalize_package,
)

_ZIG_SERVER_SOURCE = Path(__file__).with_name("zig_lookup_server.zig")
_ENGINE_CACHE_DIR = "zig_fast_lookup"
_DATASET_SCHEMA_VERSION = "v3"
_FAST_TABLE_SUFFIX = "_pick"
_REQUIRED_FAST_COLUMNS = {"lcsc_id", "package", "stock", "is_basic", "is_preferred"}
_RANGE_BOUNDS = {
    "resistance_ohm": ("resistance_min_ohm", "resistance_max_ohm"),
    "capacitance_f": ("capacitance_min_f", "capacitance_max_f"),
    "inductance_h": ("inductance_min_h", "inductance_max_h"),
    "frequency_hz": ("frequency_min_hz", "frequency_max_hz"),
}


class ZigFastLookupStore(FastLookupStore):
    def __init__(
        self,
        db_path: Path,
        *,
        cache_root: Path,
        zig_bin: str | None = None,
    ):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise SnapshotNotFoundError(f"fast snapshot DB not found: {self.db_path}")

        self.cache_root = Path(cache_root)
        self.zig_bin = zig_bin or os.getenv("ATOPILE_COMPONENTS_ZIG_BIN") or "zig"
        self._proc_lock = threading.Lock()
        self._supported_component_types: frozenset[str] = frozenset()
        self._process = self._start_engine()

    def __del__(self) -> None:
        self.close()

    def close(self) -> None:
        process = getattr(self, "_process", None)
        if process is None:
            return
        try:
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
            process.terminate()
            process.wait(timeout=1.0)
        except Exception:
            pass
        self._process = None

    def query_component(
        self, component_type: str, query: ParameterQuery
    ) -> list[ComponentCandidate]:
        if component_type not in self._supported_component_types:
            raise QueryValidationError(
                f"Unsupported component_type for zig fast lookup: {component_type}"
            )
        payload = self._build_payload(component_type, query)
        return self._query(payload)

    def query_components_batch(
        self, queries: Sequence[tuple[str, ParameterQuery]]
    ) -> list[list[ComponentCandidate]]:
        payloads: list[dict[str, object]] = []
        for component_type, query in queries:
            if component_type not in self._supported_component_types:
                raise QueryValidationError(
                    f"Unsupported component_type for zig fast lookup: {component_type}"
                )
            payloads.append(self._build_payload(component_type, query))

        parsed = self._send_request({"queries": payloads})
        if not parsed.get("ok", False):
            error = parsed.get("error", "unknown error")
            error_type = parsed.get("error_type", "internal")
            if error_type == "validation":
                raise QueryValidationError(str(error))
            raise SnapshotSchemaError(str(error))

        raw_results = parsed.get("results", [])
        if not isinstance(raw_results, list):
            raise SnapshotSchemaError("zig batch response missing results array")
        if len(raw_results) != len(payloads):
            raise SnapshotSchemaError("zig batch response results length mismatch")

        out: list[list[ComponentCandidate]] = []
        errors: list[str | None] = []
        for raw_result in raw_results:
            if not isinstance(raw_result, dict):
                raise SnapshotSchemaError("zig batch response item must be object")
            if not raw_result.get("ok", False):
                error = str(raw_result.get("error", "invalid query filters"))
                error_type = str(raw_result.get("error_type", "validation"))
                if error_type != "validation":
                    raise SnapshotSchemaError(error)
                errors.append(error)
                out.append([])
                continue
            candidates_raw = raw_result.get("candidates", [])
            out.append(self._parse_candidates(candidates_raw))
            errors.append(None)

        if any(error is not None for error in errors):
            raise BatchQueryValidationError(errors)
        return out

    def query_resistors(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self.query_component("resistor", query)

    def query_capacitors(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self.query_component("capacitor", query)

    def query_capacitors_polarized(
        self, query: ParameterQuery
    ) -> list[ComponentCandidate]:
        return self.query_component("capacitor_polarized", query)

    def query_inductors(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self.query_component("inductor", query)

    def query_diodes(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self.query_component("diode", query)

    def query_leds(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self.query_component("led", query)

    def query_bjts(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self.query_component("bjt", query)

    def query_mosfets(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self.query_component("mosfet", query)

    def query_crystals(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self.query_component("crystal", query)

    def query_ferrite_beads(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self.query_component("ferrite_bead", query)

    def query_ldos(self, query: ParameterQuery) -> list[ComponentCandidate]:
        return self.query_component("ldo", query)

    def _build_payload(
        self, component_type: str, query: ParameterQuery
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "component_type": component_type,
            "qty": query.qty,
            "limit": query.limit,
        }
        if query.package is not None:
            package = normalize_package(component_type, query.package)
            if package is None:
                raise QueryValidationError("package cannot be empty")
            payload["package"] = package

        exact_filters: list[dict[str, object]] = []
        for key, value in sorted(query.exact.items()):
            field = _QUERY_ALIASES.get(key, key)
            value = normalize_exact_filter_value(field, value)
            if isinstance(value, bool):
                exact_filters.append(
                    {"field": field, "number_value": 1.0 if value else 0.0}
                )
                continue
            if isinstance(value, (int, float)):
                exact_filters.append({"field": field, "number_value": float(value)})
                continue
            if isinstance(value, str):
                exact_filters.append({"field": field, "string_value": value})
                continue
            raise QueryValidationError(
                f"Unsupported exact filter type for {field}: {type(value).__name__}"
            )

        range_filters: list[dict[str, object]] = []
        for key, numeric_range in sorted(query.ranges.items()):
            field = _QUERY_ALIASES.get(key, key)
            lower_bound, upper_bound = expanded_range_bounds_for_column(
                field,
                numeric_range,
            )
            range_filters.append(
                {
                    "field": field,
                    "minimum": lower_bound,
                    "maximum": upper_bound,
                }
            )

        if exact_filters:
            payload["exact_filters"] = exact_filters
        if range_filters:
            payload["range_filters"] = range_filters
        return payload

    def _query(self, payload: dict[str, object]) -> list[ComponentCandidate]:
        parsed = self._send_request(payload)
        if not parsed.get("ok", False):
            error = parsed.get("error", "unknown error")
            error_type = parsed.get("error_type", "internal")
            if error_type == "validation":
                raise QueryValidationError(str(error))
            raise SnapshotSchemaError(str(error))
        return self._parse_candidates(parsed.get("candidates", []))

    def _send_request(self, payload: dict[str, object]) -> dict[str, object]:
        process = self._process
        if process is None or process.poll() is not None:
            raise SnapshotSchemaError("zig lookup process not running")
        wire = json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n"
        with self._proc_lock:
            stdin = process.stdin
            stdout = process.stdout
            if stdin is None or stdout is None:
                raise SnapshotSchemaError("zig lookup process missing stdio handles")
            try:
                stdin.write(wire)
                stdin.flush()
            except OSError as exc:
                raise SnapshotSchemaError(
                    f"failed to write request to zig lookup process: {exc}"
                ) from exc
            response_line = stdout.readline()
        if not response_line:
            stderr_msg = ""
            if process.stderr:
                stderr_msg = process.stderr.read()
            raise SnapshotSchemaError(
                "zig lookup process exited unexpectedly"
                + (f": {stderr_msg.strip()}" if stderr_msg else "")
            )
        try:
            parsed = json.loads(response_line)
        except json.JSONDecodeError as exc:
            raise SnapshotSchemaError(
                f"invalid response from zig lookup process: {exc}"
            ) from exc
        if not isinstance(parsed, dict):
            raise SnapshotSchemaError("zig lookup response must be object")
        return parsed

    def _parse_candidates(self, candidates_raw: object) -> list[ComponentCandidate]:
        if not isinstance(candidates_raw, list):
            raise SnapshotSchemaError("zig lookup response candidates must be list")
        out: list[ComponentCandidate] = []
        for item in candidates_raw:
            if not isinstance(item, dict):
                raise SnapshotSchemaError(
                    "zig lookup response candidate must be object"
                )
            out.append(
                ComponentCandidate(
                    lcsc_id=int(item["lcsc_id"]),
                    stock=_as_int_or_none(item.get("stock")),
                    is_basic=_as_bool_or_none(item.get("is_basic")),
                    is_preferred=_as_bool_or_none(item.get("is_preferred")),
                    pick_parameters={
                        key: value
                        for key, value in item.items()
                        if key not in {"lcsc_id", "stock", "is_basic", "is_preferred"}
                    },
                )
            )
        return out

    def _start_engine(self) -> subprocess.Popen[str]:
        artifact_root = self.cache_root / "serve" / _ENGINE_CACHE_DIR
        artifact_root.mkdir(parents=True, exist_ok=True)

        binary_path = self._ensure_binary(artifact_root)
        schema_path, supported = self._ensure_dataset(artifact_root)
        self._supported_component_types = frozenset(supported)
        cmd = [str(binary_path), "--schema", str(schema_path)]
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            raise SnapshotSchemaError(
                f"failed to start zig lookup process: {exc}"
            ) from exc
        return process

    def _ensure_binary(self, artifact_root: Path) -> Path:
        if not _ZIG_SERVER_SOURCE.exists():
            raise SnapshotSchemaError(f"zig source not found: {_ZIG_SERVER_SOURCE}")
        source_stat = _ZIG_SERVER_SOURCE.stat()
        source_fingerprint = _hash_text(
            f"{_ZIG_SERVER_SOURCE.resolve()}:{source_stat.st_mtime_ns}:{source_stat.st_size}"
        )
        binary_dir = artifact_root / f"bin-{source_fingerprint}"
        binary_dir.mkdir(parents=True, exist_ok=True)
        binary_path = binary_dir / "zig_lookup_server"
        if binary_path.exists():
            return binary_path
        cmd = [
            self.zig_bin,
            "build-exe",
            str(_ZIG_SERVER_SOURCE),
            "-O",
            "ReleaseFast",
            f"-femit-bin={binary_path}",
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            raise SnapshotSchemaError(
                f"failed launching zig compiler '{self.zig_bin}': {exc}"
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace")
            raise SnapshotSchemaError(
                f"failed compiling zig lookup server: {stderr.strip()}"
            ) from exc
        return binary_path

    def _ensure_dataset(self, artifact_root: Path) -> tuple[Path, list[str]]:
        db_stat = self.db_path.stat()
        source_stat = _ZIG_SERVER_SOURCE.stat()
        db_fingerprint = _hash_text(
            f"{_DATASET_SCHEMA_VERSION}:"
            f"{self.db_path.resolve()}:{db_stat.st_mtime_ns}:{db_stat.st_size}:"
            f"{_ZIG_SERVER_SOURCE.resolve()}:{source_stat.st_mtime_ns}:{source_stat.st_size}"
        )
        dataset_dir = artifact_root / f"data-{db_fingerprint}"
        schema_path = dataset_dir / "schema.json"
        if schema_path.exists():
            parsed = json.loads(schema_path.read_text(encoding="utf-8"))
            supported = [str(item["component_type"]) for item in parsed["components"]]
            return schema_path, supported

        dataset_dir.mkdir(parents=True, exist_ok=True)
        components: list[dict[str, object]] = []
        with sqlite3.connect(self.db_path) as conn:
            for component_type, table_name in _discover_fast_tables(conn):
                columns = _table_columns(conn, table_name)
                if not columns:
                    continue
                column_names = {column["name"] for column in columns}
                missing_columns = sorted(
                    _REQUIRED_FAST_COLUMNS.difference(column_names)
                )
                if missing_columns:
                    raise SnapshotSchemaError(
                        f"{table_name} missing required columns: {missing_columns}"
                    )
                out_path = dataset_dir / f"{component_type}.tsv"
                _export_table_to_tsv(
                    conn=conn,
                    table_name=table_name,
                    column_names=[column["name"] for column in columns],
                    out_path=out_path,
                )
                range_bounds = [
                    {
                        "field": field,
                        "min_field": min_col,
                        "max_field": max_col,
                    }
                    for field, (min_col, max_col) in _RANGE_BOUNDS.items()
                    if {field, min_col, max_col}.issubset(column_names)
                ]
                components.append(
                    {
                        "component_type": component_type,
                        "tsv": str(out_path),
                        "columns": columns,
                        "range_bounds": range_bounds,
                    }
                )

        if not components:
            raise SnapshotSchemaError(
                f"no fast lookup tables found in snapshot: {self.db_path}"
            )

        schema_payload = {"components": components}
        schema_path.write_text(
            json.dumps(schema_payload, ensure_ascii=True, separators=(",", ":")),
            encoding="utf-8",
        )
        supported = [str(component["component_type"]) for component in components]
        return schema_path, supported


def _discover_fast_tables(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name LIKE '%_pick'
        ORDER BY name
        """
    ).fetchall()
    out: list[tuple[str, str]] = []
    for row in rows:
        table_name = str(row[0])
        if not table_name.endswith(_FAST_TABLE_SUFFIX):
            continue
        component_type = table_name[: -len(_FAST_TABLE_SUFFIX)]
        if not component_type:
            continue
        out.append((component_type, table_name))
    return out


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[dict[str, str]]:
    rows = conn.execute(f"PRAGMA table_info({_quote_ident(table_name)})").fetchall()
    out: list[dict[str, str]] = []
    for row in rows:
        name = str(row[1])
        declared = str(row[2] or "")
        out.append(
            {
                "name": name,
                "kind": _sqlite_column_kind(name, declared),
            }
        )
    return out


def _sqlite_column_kind(column_name: str, declared_type: str) -> str:
    upper_declared = declared_type.upper()
    if column_name in {"lcsc_id", "stock", "is_basic", "is_preferred"}:
        return "int"
    if "INT" in upper_declared:
        return "int"
    if any(token in upper_declared for token in ("REAL", "FLOA", "DOUB", "NUM")):
        return "real"
    return "text"


def _export_table_to_tsv(
    *,
    conn: sqlite3.Connection,
    table_name: str,
    column_names: list[str],
    out_path: Path,
    chunk_size: int = 20_000,
) -> None:
    quoted_columns = ", ".join(_quote_ident(name) for name in column_names)
    query = f"SELECT {quoted_columns} FROM {_quote_ident(table_name)}"
    cursor = conn.execute(query)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        while True:
            chunk = cursor.fetchmany(chunk_size)
            if not chunk:
                break
            for row in chunk:
                fields = [_format_tsv_field(value) for value in row]
                handle.write("\t".join(fields))
                handle.write("\n")


def _format_tsv_field(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return format(value, ".17g")
    out = str(value)
    return out.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _as_bool_or_none(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _as_int_or_none(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _create_minimal_fast_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE resistor_pick (
                lcsc_id INTEGER PRIMARY KEY,
                package TEXT,
                stock INTEGER,
                is_basic INTEGER,
                is_preferred INTEGER,
                resistance_ohm REAL,
                resistance_min_ohm REAL,
                resistance_max_ohm REAL,
                tolerance_pct REAL,
                max_power_w REAL,
                max_voltage_v REAL,
                tempco_ppm REAL
            );
            CREATE TABLE capacitor_pick (
                lcsc_id INTEGER PRIMARY KEY,
                package TEXT,
                stock INTEGER,
                is_basic INTEGER,
                is_preferred INTEGER,
                capacitance_f REAL,
                capacitance_min_f REAL,
                capacitance_max_f REAL,
                tolerance_pct REAL,
                max_voltage_v REAL,
                tempco_code TEXT
            );
            """
        )
        conn.commit()


def test_zig_lookup_store_missing_db_raises(tmp_path) -> None:
    try:
        ZigFastLookupStore(tmp_path / "missing-fast.sqlite", cache_root=tmp_path)
    except SnapshotNotFoundError as exc:
        assert "fast snapshot DB not found" in str(exc)
    else:
        assert False, "Expected SnapshotNotFoundError"


def test_zig_lookup_store_unsupported_exact_type_raises(tmp_path) -> None:
    if shutil.which("zig") is None:
        return

    db_path = tmp_path / "fast.sqlite"
    _create_minimal_fast_db(db_path)
    store = ZigFastLookupStore(db_path, cache_root=tmp_path)
    try:
        store.query_resistors(ParameterQuery(exact={"foo": ["bar"]}))
    except QueryValidationError as exc:
        assert "Unsupported exact filter type" in str(exc)
    else:
        assert False, "Expected QueryValidationError"
    finally:
        store.close()


def test_zig_lookup_store_supports_dynamic_component_tables(tmp_path) -> None:
    if shutil.which("zig") is None:
        return

    db_path = tmp_path / "fast.sqlite"
    _create_minimal_fast_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE diode_pick (
                lcsc_id INTEGER PRIMARY KEY,
                package TEXT,
                stock INTEGER,
                is_basic INTEGER,
                is_preferred INTEGER,
                forward_voltage_v REAL,
                reverse_working_voltage_v REAL,
                max_current_a REAL,
                reverse_leakage_current_a REAL
            );
            """
        )
        conn.execute(
            """
            INSERT INTO diode_pick (
                lcsc_id,
                package,
                stock,
                is_basic,
                is_preferred,
                forward_voltage_v,
                reverse_working_voltage_v,
                max_current_a,
                reverse_leakage_current_a
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (12345, "SOD-123", 42, 1, 0, 0.72, 60.0, 1.0, 1e-6),
        )
        conn.commit()

    store = ZigFastLookupStore(db_path, cache_root=tmp_path)
    try:
        candidates = store.query_diodes(ParameterQuery(limit=5, qty=1))
        assert len(candidates) == 1
        assert candidates[0].lcsc_id == 12345
        assert candidates[0].pick_parameters["forward_voltage_v"] == 0.72
    finally:
        store.close()


def test_zig_lookup_store_query_component_supports_unknown_pick_table(tmp_path) -> None:
    if shutil.which("zig") is None:
        return

    db_path = tmp_path / "fast.sqlite"
    _create_minimal_fast_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE tvs_diode_pick (
                lcsc_id INTEGER PRIMARY KEY,
                package TEXT,
                stock INTEGER,
                is_basic INTEGER,
                is_preferred INTEGER,
                standoff_voltage_v REAL,
                clamp_voltage_v REAL,
                polarity TEXT
            );
            """
        )
        conn.execute(
            """
            INSERT INTO tvs_diode_pick (
                lcsc_id,
                package,
                stock,
                is_basic,
                is_preferred,
                standoff_voltage_v,
                clamp_voltage_v,
                polarity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (98765, "SOD-323", 120, 0, 1, 5.0, 9.2, "UNIDIRECTIONAL"),
        )
        conn.commit()

    store = ZigFastLookupStore(db_path, cache_root=tmp_path)
    try:
        candidates = store.query_component("tvs_diode", ParameterQuery(limit=5, qty=1))
        assert len(candidates) == 1
        assert candidates[0].lcsc_id == 98765
        assert candidates[0].pick_parameters["polarity"] == "UNIDIRECTIONAL"
    finally:
        store.close()


def test_zig_lookup_store_query_components_batch_success(tmp_path) -> None:
    if shutil.which("zig") is None:
        return

    db_path = tmp_path / "fast.sqlite"
    _create_minimal_fast_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO resistor_pick (
                lcsc_id,
                package,
                stock,
                is_basic,
                is_preferred,
                resistance_ohm,
                resistance_min_ohm,
                resistance_max_ohm,
                tolerance_pct,
                max_power_w,
                max_voltage_v,
                tempco_ppm
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1001, "0603", 100, 1, 0, 1000.0, 999.0, 1001.0, 1.0, 0.125, 50.0, 100.0),
        )
        conn.execute(
            """
            INSERT INTO capacitor_pick (
                lcsc_id,
                package,
                stock,
                is_basic,
                is_preferred,
                capacitance_f,
                capacitance_min_f,
                capacitance_max_f,
                tolerance_pct,
                max_voltage_v,
                tempco_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (2002, "0402", 80, 0, 1, 1e-6, 0.9e-6, 1.1e-6, 10.0, 16.0, "X7R"),
        )
        conn.commit()

    store = ZigFastLookupStore(db_path, cache_root=tmp_path)
    try:
        results = store.query_components_batch(
            [
                ("resistor", ParameterQuery(exact={"resistance_ohm": 1000.0}, limit=5)),
                ("capacitor", ParameterQuery(exact={"tempco_code": "X7R"}, limit=5)),
            ]
        )
        assert [candidate.lcsc_id for candidate in results[0]] == [1001]
        assert [candidate.lcsc_id for candidate in results[1]] == [2002]
    finally:
        store.close()


def test_zig_lookup_store_query_components_batch_validation_error(tmp_path) -> None:
    if shutil.which("zig") is None:
        return

    db_path = tmp_path / "fast.sqlite"
    _create_minimal_fast_db(db_path)
    store = ZigFastLookupStore(db_path, cache_root=tmp_path)
    try:
        store.query_components_batch(
            [
                ("resistor", ParameterQuery(limit=5, qty=1)),
                ("resistor", ParameterQuery(exact={"does_not_exist": 1.0}, limit=5)),
            ]
        )
    except BatchQueryValidationError as exc:
        assert exc.errors == [None, "invalid query filters"]
    else:
        assert False, "Expected BatchQueryValidationError"
    finally:
        store.close()
