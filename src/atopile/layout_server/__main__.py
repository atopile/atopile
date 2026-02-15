"""CLI entry point: python -m atopile.layout_server <path.kicad_pcb> [--port 8100]"""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="PCB Layout Viewer/Editor")
    parser.add_argument("pcb_path", type=Path, help="Path to .kicad_pcb file")
    parser.add_argument("--port", type=int, default=8100, help="Server port")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    args = parser.parse_args()

    if not args.pcb_path.exists():
        parser.error(f"File not found: {args.pcb_path}")

    from atopile.layout_server.server import create_app

    app = create_app(args.pcb_path)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
