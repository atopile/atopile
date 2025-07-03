from atopile.mcp.util import mcp_decorate


@mcp_decorate()
def build_project(absolute_project_dir: str, target_name_from_yaml: str) -> str:
    from atopile.cli.build import build

    try:
        build(
            selected_builds=[target_name_from_yaml],
            entry=absolute_project_dir,
            open_layout=False,
        )
    except Exception as e:
        raise ValueError(f"Failed to build project: {e}")

    return f"Built project {absolute_project_dir} with target {target_name_from_yaml}"
