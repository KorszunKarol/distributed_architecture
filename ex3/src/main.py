#!/usr/bin/env python3
"""Main entry point for the distributed mutual exclusion system."""

import asyncio
import logging
from src.common.constants import NetworkConfig
from src.processes.heavyweight.heavyweight_a import HeavyweightProcessA
from src.processes.heavyweight.heavyweight_b import HeavyweightProcessB
from src.processes.lightweight.lightweight_a import LightweightProcessA
from src.processes.lightweight.lightweight_b import LightweightProcessB

async def create_lightweight_processes(num_processes: int, process_class, start_port: int):
    """Create lightweight processes of specified class.

    Args:
        num_processes: Number of processes to create
        process_class: Class of processes to create (A or B)
        start_port: Starting port number for processes

    Returns:
        List of created lightweight processes
    """
    processes = []
    for i in range(num_processes):
        process = process_class(
            number=i,
            port=start_port + i
        )
        processes.append(process)
    return processes

async def main():
    """Initialize and run the distributed mutual exclusion system."""
    # Configure logging to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs.txt'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("Main")

    # Initialize variables for cleanup
    process_a = None
    process_b = None
    lightweight_a = []
    lightweight_b = []

    try:
        # Create heavyweight processes
        process_a = HeavyweightProcessA(
            number=0,
            port=NetworkConfig.HEAVYWEIGHT_A_PORT
        )
        process_a.has_token = True  # Set token after creation
        print(f"Heavyweight process A created at port {NetworkConfig.HEAVYWEIGHT_A_PORT}")

        process_b = HeavyweightProcessB(
            number=0,
            port=NetworkConfig.HEAVYWEIGHT_B_PORT
        )
        print(f"Heavyweight process B created at port {NetworkConfig.HEAVYWEIGHT_B_PORT}")

        # Create lightweight processes
        lightweight_a = await create_lightweight_processes(
            NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES,
            LightweightProcessA,
            NetworkConfig.LIGHTWEIGHT_A_BASE_PORT
        )
        print(f"Lightweight process A created at port {NetworkConfig.LIGHTWEIGHT_A_BASE_PORT}")
        lightweight_b = await create_lightweight_processes(
            NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES,
            LightweightProcessB,
            NetworkConfig.LIGHTWEIGHT_B_BASE_PORT
        )
        print(f"Lightweight process B created at port {NetworkConfig.LIGHTWEIGHT_B_BASE_PORT}")

        # Collect all process coroutines
        process_tasks = [
            process_a.run(),
            process_b.run()
        ]
        process_tasks.extend(lw.run() for lw in lightweight_a)
        process_tasks.extend(lw.run() for lw in lightweight_b)

        logger.info("Starting all processes...")
        # Add timeout to prevent infinite waiting
        await asyncio.wait_for(
            asyncio.gather(*process_tasks),
            timeout=NetworkConfig.SYSTEM_TIMEOUT
        )

    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        logger.info("Cleaning up processes...")
        # Cleanup heavyweight processes
        if process_a:
            await process_a.cleanup()
        if process_b:
            await process_b.cleanup()

        # Cleanup lightweight processes
        for lw in lightweight_a + lightweight_b:
            await lw.cleanup()

        logger.info("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())