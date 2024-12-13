"""Main entry point for lightweight processes.

This module provides the entry point for running lightweight processes
as standalone Python modules.
"""
import asyncio
import sys
from .lightweight_a import LightweightProcessA
from .lightweight_b import LightweightProcessB

async def main():
    """Main entry point.

    Parses command line arguments and starts the appropriate process.
    """
    if len(sys.argv) != 3:
        print("Usage: python -m src.processes.lightweight <process_number> <port>")
        sys.exit(1)

    process_number = int(sys.argv[1])
    port = int(sys.argv[2])

    # Select process class based on port range
    is_group_a = port < NetworkConfig.LIGHTWEIGHT_B_BASE_PORT
    process_class = LightweightProcessA if is_group_a else LightweightProcessB
    process = process_class(number=process_number, port=port)

    try:
        await process.run()
    except KeyboardInterrupt:
        process.cleanup()
    except Exception as e:
        process.logger.error(f"Process terminated with error: {e}")
        process.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())