"""Streaming utilities for real-time response generation."""

import logging
import time
from typing import Generator, Iterator
import queue
import threading

logger = logging.getLogger(__name__)


class StreamBuffer:
    """Thread-safe buffer for streaming content."""

    def __init__(self):
        """Initialize stream buffer."""
        self.queue = queue.Queue()
        self.finished = False

    def write(self, content: str):
        """
        Write content to buffer.

        Args:
            content: Content to write
        """
        if content:
            self.queue.put(content)

    def finish(self):
        """Mark stream as finished."""
        self.finished = True
        self.queue.put(None)  # Sentinel value

    def read_stream(self) -> Generator[str, None, None]:
        """
        Read from buffer as generator.

        Yields:
            Content chunks as they become available
        """
        while True:
            try:
                item = self.queue.get(timeout=0.1)
                if item is None:  # Sentinel value
                    break
                yield item
            except queue.Empty:
                if self.finished:
                    break
                continue


def create_streaming_wrapper(func):
    """
    Create a streaming wrapper for a function.

    This wrapper runs the function in a separate thread and
    yields progress updates and the final result.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function that yields streaming updates
    """
    def streaming_function(*args, **kwargs) -> Generator[str, None, None]:
        """
        Streaming wrapper function.

        Yields:
            Status updates and final result
        """
        # Initial status
        yield "🔄 Initializing analysis...\n\n"
        time.sleep(0.1)

        # Create buffer for thread communication
        buffer = StreamBuffer()
        result_container = {"result": None, "error": None}

        def run_function():
            """Run function in thread."""
            try:
                result = func(*args, **kwargs)
                result_container["result"] = result
            except Exception as e:
                logger.exception("Function execution failed")
                result_container["error"] = str(e)
            finally:
                buffer.finish()

        # Start function in background thread
        thread = threading.Thread(target=run_function, daemon=True)
        thread.start()

        # Yield progress updates
        progress_messages = [
            "📊 Gathering market data...",
            "💹 Analyzing financial metrics...",
            "📈 Calculating technical indicators...",
            "📰 Checking recent news...",
            "🏦 Reviewing analyst opinions...",
            "🤖 AI agents processing data...",
            "📝 Generating comprehensive report...",
        ]

        for i, message in enumerate(progress_messages):
            if not thread.is_alive() and result_container.get("result"):
                break

            yield f"\n{message}\n"
            time.sleep(0.3)  # Simulated progress

            # Check if function finished
            if not thread.is_alive():
                break

        # Wait for completion
        thread.join(timeout=300)  # 5 minute timeout

        # Yield final result
        if result_container["error"]:
            yield f"\n\n❌ Error: {result_container['error']}\n"
        elif result_container["result"]:
            yield f"\n\n{'='*80}\n"
            yield "✅ **ANALYSIS COMPLETE**\n"
            yield f"{'='*80}\n\n"
            yield result_container["result"]
        else:
            yield "\n\n⚠️ Analysis timed out or produced no result\n"

    return streaming_function


def stream_with_progress(
    func,
    status_callback=None,
    progress_steps=None
) -> Generator[str, None, None]:
    """
    Stream function execution with progress updates.

    Args:
        func: Function to execute
        status_callback: Optional callback for status updates
        progress_steps: Optional list of progress step descriptions

    Yields:
        Progress updates and final result
    """
    if progress_steps is None:
        progress_steps = [
            "Initializing...",
            "Fetching data...",
            "Processing...",
            "Finalizing..."
        ]

    # Yield initial status
    for step in progress_steps:
        if status_callback:
            status_callback(step)
        yield f"⏳ {step}\n"
        time.sleep(0.2)

    # Execute function
    try:
        result = func()
        yield f"\n✅ Complete!\n\n{result}"
    except Exception as e:
        logger.exception("Streaming execution failed")
        yield f"\n❌ Error: {str(e)}"


class TokenStreamSimulator:
    """
    Simulates token-by-token streaming for pre-generated text.

    This provides a ChatGPT-like streaming experience even when
    the full response is generated at once.
    """

    def __init__(self, text: str, tokens_per_second: int = 50):
        """
        Initialize stream simulator.

        Args:
            text: Full text to stream
            tokens_per_second: Streaming speed (tokens/second)
        """
        self.text = text
        self.tokens_per_second = tokens_per_second
        self.delay = 1.0 / tokens_per_second

    def stream(self) -> Generator[str, None, None]:
        """
        Stream text token by token.

        Yields:
            Individual tokens (words/characters)
        """
        # Split into words for word-by-word streaming
        words = self.text.split(' ')

        for i, word in enumerate(words):
            if i > 0:
                yield ' ' + word
            else:
                yield word

            # Add delay for realistic streaming effect
            time.sleep(self.delay)

    def stream_lines(self) -> Generator[str, None, None]:
        """
        Stream text line by line.

        Yields:
            Individual lines
        """
        lines = self.text.split('\n')

        for line in lines:
            yield line + '\n'
            time.sleep(self.delay * 5)  # Slower for lines


def create_progress_tracker(total_steps: int):
    """
    Create a progress tracking context manager.

    Args:
        total_steps: Total number of steps

    Returns:
        Progress tracker instance
    """
    class ProgressTracker:
        def __init__(self, total):
            self.total = total
            self.current = 0
            self.messages = []

        def update(self, message: str) -> str:
            """
            Update progress.

            Args:
                message: Progress message

            Returns:
                Formatted progress string
            """
            self.current += 1
            progress_pct = (self.current / self.total) * 100
            status = f"[{self.current}/{self.total}] ({progress_pct:.0f}%) {message}"
            self.messages.append(status)
            return status

        def get_summary(self) -> str:
            """Get progress summary."""
            return "\n".join(self.messages)

    return ProgressTracker(total_steps)
