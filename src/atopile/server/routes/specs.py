"""Spec extraction routes — walks the compiled graph for has_requirement modules."""

from __future__ import annotations

import asyncio
import logging
import textwrap
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

log = logging.getLogger(__name__)

router = APIRouter(tags=["specs"])


def _extract_specs(project_root: str, target: str) -> dict:
    """Walk the compiled graph and extract modules that have has_requirement traits.

    This is a synchronous function run in a thread because graph
    compilation touches C-extensions that are not async-safe.
    """
    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.graph as graph
    import faebryk.core.node as fabll
    import faebryk.library._F as F
    from faebryk.core.node import TypeNodeBoundTG

    from atopile.compiler.build import Linker, StdlibRegistry, build_file
    from atopile.config import config as ato_config

    project_path = Path(project_root)
    if not project_path.is_dir():
        raise ValueError(f"Project root not found: {project_root}")

    # Find the entry file from ato.yaml
    ato_yaml = project_path / "ato.yaml"
    if not ato_yaml.exists():
        raise ValueError(f"No ato.yaml found in {project_root}")

    import yaml

    with open(ato_yaml) as f:
        proj_cfg = yaml.safe_load(f) or {}

    # Resolve entry point
    builds = proj_cfg.get("builds", {})
    if target != "default" and target in builds:
        entry_point = builds[target].get("entry", "")
    elif "default" in builds:
        entry_point = builds["default"].get("entry", "")
    else:
        # Take first build
        for _name, build_cfg in builds.items():
            entry_point = build_cfg.get("entry", "")
            break
        else:
            raise ValueError("No builds defined in ato.yaml")

    if not entry_point or ":" not in entry_point:
        raise ValueError(f"Invalid entry point: {entry_point}")

    file_part, _module = entry_point.rsplit(":", 1)
    file_path = project_path / file_part

    if not file_path.exists():
        raise ValueError(f"Entry file not found: {file_path}")

    # Build the file
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    result = build_file(g=g, tg=tg, import_path=file_part, path=file_path)

    # Try to link imports
    try:
        ato_config.apply_options(entry=None, working_dir=project_path)
        stdlib = StdlibRegistry(tg)
        linker = Linker(config_obj=ato_config, stdlib=stdlib, tg=tg)
        linker._link_recursive(g, result.state)
    except Exception as link_exc:
        log.debug("Import linking skipped: %s", link_exc)

    # Get type node references for the traits we care about
    has_doc_string_type = TypeNodeBoundTG.get_or_create_type_in_tg(
        tg=tg, t=F.has_doc_string
    )
    has_requirement_type = TypeNodeBoundTG.get_or_create_type_in_tg(
        tg=tg, t=F.has_requirement
    )

    specs: list[dict] = []

    for type_name, type_root in result.state.type_roots.items():
        # Collect has_requirement traits for this module
        requirements = _collect_requirements(
            tg, type_root, has_requirement_type, fbrk, F
        )

        # Skip modules that have no requirements — they're not spec-relevant
        if not requirements:
            continue

        spec_data: dict = {
            "module": type_name,
            "file": file_part,
            "docstring": None,
            "requirements": requirements,
            "assertions": [],
            "children": [],
            "connections": [],
        }

        # Extract docstring
        doc_impl = fbrk.Trait.try_get_trait(
            target=type_root, trait_type=has_doc_string_type
        )
        if doc_impl is not None:
            try:
                doc_trait = F.has_doc_string(doc_impl)
                spec_data["docstring"] = textwrap.dedent(doc_trait.doc_string).strip()
            except Exception:
                pass

        # Extract children (sub-modules)
        try:
            make_children = tg.collect_make_children(type_node=type_root)
            for identifier, make_child in make_children:
                if not identifier or identifier.startswith("_"):
                    continue
                # Skip trait-like names
                if identifier.startswith(("is_", "has_", "can_", "implements_")):
                    continue
                if identifier.startswith("anon"):
                    continue

                child_type_name = "Unknown"
                child_docstring = None
                try:
                    type_ref = tg.get_make_child_type_reference(
                        make_child=make_child
                    )
                    resolved = fbrk.Linker.get_resolved_type(type_reference=type_ref)
                    if resolved is not None:
                        child_type_name = fbrk.TypeGraph.get_type_name(
                            type_node=resolved
                        )
                        # Check if child is a module (not interface/parameter)
                        if not fabll.TypeNodeBoundTG.has_instance_of_type_has_trait(
                            resolved, fabll.is_module
                        ):
                            continue

                        # Get child's docstring
                        child_doc = fbrk.Trait.try_get_trait(
                            target=resolved, trait_type=has_doc_string_type
                        )
                        if child_doc is not None:
                            try:
                                child_docstring = textwrap.dedent(
                                    F.has_doc_string(child_doc).doc_string
                                ).strip()
                            except Exception:
                                pass
                    else:
                        child_type_name = fbrk.TypeGraph.get_type_reference_identifier(
                            type_reference=type_ref
                        )
                except Exception:
                    pass

                spec_data["children"].append(
                    {
                        "name": identifier,
                        "type": child_type_name,
                        "docstring": child_docstring,
                    }
                )
        except Exception as exc:
            log.debug("Failed to extract children for %s: %s", type_name, exc)

        # Extract connections
        try:
            make_links = tg.collect_make_links(type_node=type_root)
            for link in make_links:
                try:
                    from_path = fbrk.TypeGraph.get_make_link_source_path(link)
                    to_path = fbrk.TypeGraph.get_make_link_target_path(link)
                    if from_path and to_path:
                        spec_data["connections"].append(
                            {"from": from_path, "to": to_path}
                        )
                except Exception:
                    continue
        except Exception as exc:
            log.debug("Failed to extract connections for %s: %s", type_name, exc)

        specs.append(spec_data)

    return {"specs": specs}


def _collect_requirements(tg, type_root, has_requirement_type, fbrk, F) -> list[dict]:
    """Extract all has_requirement traits from a type node.

    Traits defined in .ato are stored as MakeLink descriptions at the type level
    and only become real EdgeTrait edges after instantiation.  We instantiate
    the type into a temporary instance so we can query EdgeTrait edges.
    """
    try:
        instance = tg.instantiate_node(type_node=type_root, attributes={})
    except Exception:
        log.debug("Failed to instantiate %s for trait extraction", type_root,
                  exc_info=True)
        return []

    trait_edges: list = []

    def _collect_trait_edges(ctx: list, edge) -> None:
        ctx.append(edge)

    try:
        fbrk.EdgeTrait.visit_trait_instances_of_type(
            owner=instance,
            trait_type=has_requirement_type.node(),
            ctx=trait_edges,
            f=_collect_trait_edges,
        )
    except Exception:
        log.debug("Failed to visit trait edges for %s", type_root, exc_info=True)
        return []

    requirements: list[dict] = []
    for edge in trait_edges:
        try:
            trait_node = fbrk.EdgeTrait.get_trait_instance_node(edge=edge.edge())
            trait_bound = edge.g().bind(node=trait_node)
            req_trait = F.has_requirement(trait_bound)
            requirements.append(
                {
                    "id": req_trait.id,
                    "text": req_trait.text,
                    "criteria": req_trait.criteria,
                    "source": "trait",
                }
            )
        except Exception:
            continue

    return requirements


@router.get("/api/specs")
async def get_specs(
    project_root: str = Query(
        "", description="Path to the project root (containing ato.yaml)"
    ),
    target: str = Query("default", description="Build target name"),
):
    """Extract spec data from modules with has_requirement traits."""
    if not project_root:
        return {"specs": []}
    try:
        result = await asyncio.to_thread(_extract_specs, project_root, target)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.exception("Failed to extract specs")
        raise HTTPException(status_code=500, detail=str(exc))
