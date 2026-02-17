import logging
import sys
from dotenv import load_dotenv
from .server import mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)

def main():
    """Entry point for the ACM UI MCP Server."""
    load_dotenv()
    mcp.run()

if __name__ == "__main__":
    main()
