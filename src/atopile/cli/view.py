# pylint: disable=logging-fstring-interpolation

"""
`ato view`

Commands for viewing and exporting graph visualizations.
"""

import logging
from pathlib import Path
from typing import Annotated

import typer

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def view(
    entry: Annotated[str | None, typer.Argument()] = None,
    build: Annotated[list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")] = [],
    target: Annotated[
        list[str], typer.Option("--target", "-t", envvar="ATO_TARGET")
    ] = [],
    export: Annotated[
        str | None,
        typer.Option(
            "--export",
            "-e",
            help="Export graph to JSON file at the specified path",
        ),
    ] = None,
    serve: Annotated[
        bool,
        typer.Option(
            "--serve",
            "-s",
            help="Start a local server to view the graph visualization",
        ),
    ] = False,
    port: Annotated[
        int,
        typer.Option(
            "--port",
            "-p",
            help="Port to serve the visualizer on (default: 8765)",
        ),
    ] = 8765,
):
    """
    View a block diagram or schematic of your project.

    Use --export to save the graph as JSON, or --serve to open an interactive
    visualization in your browser.
    """
    from atopile.config import config

    # Handle config setup
    config.apply_options(
        entry=entry,
        selected_builds=build if build else (),
        include_targets=target if target else (),
    )

    # If no action specified, default to serve
    if not export and not serve:
        serve = True

    # Build the app to get the graph - use first selected build
    from atopile.buildutil import init_app

    build_name = list(config.selected_builds)[0]
    log.info(f"Building {build_name}...")

    with config.select_build(build_name):
        app = init_app()

        # Export to JSON if requested
        if export:
            from faebryk.core.graph_export import export_graph_to_json

            output_path = Path(export)
            log.info(f"Exporting graph to {output_path}...")

            data = export_graph_to_json(app.instance, output_path)
            log.info(
                f"Exported {data['metadata']['totalNodes']} nodes and "
                f"{data['metadata']['totalEdges']} edges"
            )

        # Serve the visualizer
        if serve:
            _serve_visualizer(app, port)


def _serve_visualizer(app, port: int):
    """Start a local HTTP server for the graph visualization."""
    import http.server
    import json
    import socketserver
    import tempfile
    import webbrowser

    from faebryk.core.graph_export import export_graph_to_json

    # Export graph to a temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="ato_visualizer_"))
    graph_path = temp_dir / "graph.json"

    log.info("Exporting graph data...")
    try:
        data = export_graph_to_json(app.instance, graph_path)
        log.info(
            f"Exported {data['metadata']['totalNodes']} nodes, "
            f"{data['metadata']['totalEdges']} edges"
        )

        # Verify the JSON is valid
        with open(graph_path, "r") as f:
            json.load(f)
        log.info(f"JSON validated successfully at {graph_path}")
    except Exception as e:
        log.error(f"Failed to export graph: {e}")
        import traceback

        traceback.print_exc()
        return

    # Check if the web app is built
    web_dir = Path(__file__).parent.parent / "visualizer" / "web" / "dist"
    if not web_dir.exists():
        log.warning(
            f"Visualizer web app not built at {web_dir}. "
            "Serving JSON data only. Run 'npm ci' then 'npm run build' in the "
            f"{web_dir.parent} directory to build the full visualizer."
        )
        # Fall back to serving just the temp dir with JSON
        web_dir = temp_dir
    else:
        # Copy graph.json to the web dist directory
        import shutil

        shutil.copy(graph_path, web_dir / "graph.json")

    # Create a simple HTTP handler that serves from the web directory
    class GraphHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_dir), **kwargs)

        def log_message(self, format, *args):
            # Suppress default logging
            pass

        def end_headers(self):
            # Add CORS headers and proper content types
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            super().end_headers()

        def guess_type(self, path):
            if str(path).endswith(".json"):
                return "application/json"
            return super().guess_type(path)

    try:
        with socketserver.TCPServer(("", port), GraphHandler) as httpd:
            url = f"http://localhost:{port}"
            log.info(f"Serving visualizer at {url}")
            log.info("Press Ctrl+C to stop")

            # Open browser
            webbrowser.open(url)

            # Serve until interrupted
            httpd.serve_forever()
    finally:
        # Clean up temp directory
        import shutil

        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
