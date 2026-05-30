import os
import sys
import logging
import uvicorn

from configurations.config import load_config
from web_server import WebServer


def setup_logging(log_level: str):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("agent.log")
        ]
    )


async def main():
    """Main entry point"""
    # Load configuration
    config = load_config()

    # Setup logging
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    logger.info("Starting Robot Agent System")

    # Create and run web server
    server = WebServer(config)

    # Get host and port from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    logger.info(f"Starting web server on {host}:{port}")

    # Run server
    config_uvicorn = uvicorn.Config(
        server.app,
        host=host,
        port=port,
        log_level=config.log_level.lower()
    )
    server_uvicorn = uvicorn.Server(config_uvicorn)
    await server_uvicorn.serve()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
