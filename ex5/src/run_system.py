"""Script to run both the web server and the test system."""
import asyncio
import subprocess
import sys
from manual_test import main as test_main

async def run_system():
    """Run the web server and test system."""
    # Start the FastAPI server in a separate process
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "web.backend.server:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd="src"
    )

    try:
        # Run the test system
        await test_main()
    finally:
        # Cleanup
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    asyncio.run(run_system())