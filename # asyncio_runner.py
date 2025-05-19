# asyncio_runner.py 
import asyncio
import threading
import concurrent.futures
from typing import Any, Coroutine, Optional

# Basic logging for the runner thread
import logging
runner_logger = logging.getLogger(__name__)
runner_logger.setLevel(logging.INFO)

class AsyncioRunner:
    """Manages a dedicated asyncio event loop in a separate thread."""
    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def start(self):
        """Starts the asyncio loop thread."""
        if self._is_running:
            runner_logger.info("AsyncioRunner already running.")
            return

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True) # Daemon=True allows app to exit even if thread stuck
        self._thread.start()
        self._is_running = True
        runner_logger.info("AsyncioRunner thread started.")

    def _run_loop(self):
        """The target function for the runner thread."""
        runner_logger.info(f"AsyncioRunner thread ({threading.get_ident()}): Setting event loop.")
        asyncio.set_event_loop(self._loop)
        runner_logger.info(f"AsyncioRunner thread ({threading.get_ident()}): Starting event loop.")
        try:
            # run_forever blocks until stop() is called
            self._loop.run_forever()
        finally:
            runner_logger.info(f"AsyncioRunner thread ({threading.get_ident()}): Loop stopped. Cleaning up tasks.")
            # Cancel all outstanding tasks before closing the loop
            tasks = asyncio.all_tasks(self._loop)
            if tasks:
                for task in tasks:
                    task.cancel()
                try:
                    # Wait for tasks to complete their cancellation/cleanup
                    self._loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                except asyncio.CancelledError:
                    runner_logger.info("AsyncioRunner thread: Pending tasks cancellation complete.")
            runner_logger.info(f"AsyncioRunner thread ({threading.get_ident()}): Closing loop.")
            self._loop.close()
            runner_logger.info(f"AsyncioRunner thread ({threading.get_ident()}): Loop closed.")
            asyncio.set_event_loop(None) # Unset the loop for this thread

    def run_awaitable(self, coro: Coroutine, timeout: Optional[float] = None) -> Any:
        """Submits a coroutine to the runner's loop and waits for its result."""
        if not self._is_running or not self._loop or self._loop.is_closed() or not self._thread or not self._thread.is_alive():
            runner_logger.error("AsyncioRunner not active.")
            raise RuntimeError("AsyncioRunner is not running or loop is closed.")

        # Use concurrent.futures.Future to get the result back to the calling thread
        future = concurrent.futures.Future()

        def _callback():
            # This callback runs in the runner thread's loop
            async def _run_and_complete():
                try:
                    result = await coro
                    self._loop.call_soon_threadsafe(future.set_result, result)
                except Exception as e:
                    self._loop.call_soon_threadsafe(future.set_exception, e)

            asyncio.create_task(_run_and_complete())

        # Schedule the callback to run in the runner's loop
        self._loop.call_soon_threadsafe(_callback)

        # Wait for the result in the calling thread (blocks)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            runner_logger.warning("Coroutine execution timed out.")
            # Optional: Add logic here to cancel the task in the remote loop if timeout occurs
            raise TimeoutError(f"Coroutine execution timed out after {timeout} seconds.")
        except Exception as e:
             runner_logger.error(f"Error running coroutine: {e}")
             raise # Re-raise the exception from the coroutine


    def shutdown(self, timeout: float = 5.0):
        """Stops the asyncio loop and waits for the thread to join."""
        if not self._is_running or not self._loop or self._loop.is_closed() or not self._thread or not self._thread.is_alive():
            runner_logger.info("AsyncioRunner not active for shutdown.")
            self._is_running = False
            self._loop = None
            self._thread = None
            return

        runner_logger.info("AsyncioRunner: Signalling loop stop.")
        # Signal the loop to stop
        self._loop.call_soon_threadsafe(self._loop.stop)

        # Wait for the thread to finish its execution (loop.run_forever exits)
        runner_logger.info(f"AsyncioRunner: Waiting for thread ({self._thread.ident}) to join.")
        self._thread.join(timeout=timeout)

        if self._thread.is_alive():
            runner_logger.warning("AsyncioRunner WARNING: Thread did not join in time.")

        self._is_running = False
        self._loop = None # Clear references
        self._thread = None
        runner_logger.info("AsyncioRunner: Shutdown complete.")

# Helper to get or create the runner instance in session state
def get_asyncio_runner():
    if 'asyncio_runner' not in st.session_state:
        runner = AsyncioRunner()
        runner.start()
        st.session_state.asyncio_runner = runner
        # Register shutdown with atexit *only once*
        if 'asyncio_runner_atexit_registered' not in st.session_state:
             print("Registering AsyncioRunner atexit cleanup.")
             atexit.register(st.session_state.asyncio_runner.shutdown)
             st.session_state.asyncio_runner_atexit_registered = True
    return st.session_state.asyncio_runner