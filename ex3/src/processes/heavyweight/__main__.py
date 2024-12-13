"""Main entry point for heavyweight processes.

This module provides the entry point for running heavyweight processes
as standalone Python modules.
"""
import asyncio
import sys
from .heavyweight_a import HeavyweightProcessA
from .heavyweight_b import HeavyweightProcessB

async def main():
    """Main entry point.

    Parses command line arguments and starts the appropriate process.
    """
    if len(sys.argv) != 3:
        print("Usage: python -m src.processes.heavyweight <process_number> <port>")
        sys.exit(1)

    process_number = int(sys.argv[1])
    port = int(sys.argv[2])

    # Select process class based on process number
    process_class = HeavyweightProcessA if process_number == 0 else HeavyweightProcessB
    process = process_class(port=port)

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