"""
Main entry point for the Hermes Free Router.

Can be run directly with:
    python -m app.main

Or via the proxy server:
    python -m app.main --mode proxy
"""

import argparse
import uvicorn
from .proxy import app as proxy_app


def main():
    parser = argparse.ArgumentParser(description="Hermes Free Router")
    parser.add_argument(
        "--mode", 
        choices=["proxy", "cli"], 
        default="proxy",
        help="Run mode: 'proxy' for HTTP server, 'cli' for command line"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    
    args = parser.parse_args()
    
    if args.mode == "proxy":
        print(f"Starting Hermes Free Router proxy on {args.host}:{args.port}")
        uvicorn.run(proxy_app, host=args.host, port=args.port)
    elif args.mode == "cli":
        from .cli import app as cli_app
        cli_app()


if __name__ == "__main__":
    main()
