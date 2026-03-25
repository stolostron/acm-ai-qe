# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file was developed with AI assistance.

"""Main entry point for the Jira MCP server."""

import argparse
import asyncio
import logging
import sys
from typing import Optional

from .server import JiraMCPServer


async def main_async() -> None:
    """Main async function for server initialization."""
    server = JiraMCPServer()
    await server.start()
    return server


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Jira MCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "sse"], 
        default="stdio",
        help="Transport type to use (default: stdio)"
    )
    parser.add_argument(
        "--host", 
        default="127.0.0.1",
        help="Host to bind to for SSE transport (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="Port to bind to for SSE transport (default: 8000)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.transport == "sse":
            # Initialize server and run with SSE transport
            server = asyncio.run(main_async())
            server.run_sse_server(host=args.host, port=args.port)
        else:
            # Initialize the server asynchronously for stdio transport
            server = asyncio.run(main_async())
            
            # Run the MCP server (this is synchronous and manages its own event loop)
            server.mcp.run()
    except KeyboardInterrupt:
        logging.info("Server stopped")
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()