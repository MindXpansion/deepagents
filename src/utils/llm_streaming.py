"""True LLM token-by-token streaming support (v1.3.0).

Enables real-time streaming of LLM tokens for ChatGPT-like user experience.
"""

import logging
from typing import Any, Dict, List, Optional, Generator
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult
import queue
import threading

logger = logging.getLogger(__name__)


class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming LLM tokens to Gradio UI."""

    def __init__(self):
        """Initialize streaming callback handler."""
        self.token_queue = queue.Queue()
        self.is_streaming = False
        self.current_tokens = []
        logger.info("StreamingCallbackHandler initialized")

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Called when LLM starts generating."""
        self.is_streaming = True
        self.current_tokens = []
        logger.debug("LLM generation started")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """
        Called when a new token is generated.

        Args:
            token: The new token from the LLM
        """
        if self.is_streaming:
            self.current_tokens.append(token)
            self.token_queue.put(("token", token))
            logger.debug(f"New token: {token[:20]}...")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM finishes generating."""
        self.is_streaming = False
        self.token_queue.put(("end", None))
        logger.debug(f"LLM generation ended, total tokens: {len(self.current_tokens)}")

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when LLM encounters an error."""
        self.is_streaming = False
        self.token_queue.put(("error", str(error)))
        logger.error(f"LLM error: {error}")

    def get_tokens(self) -> Generator[str, None, None]:
        """
        Generator that yields tokens as they arrive.

        Yields:
            Tokens from the LLM
        """
        while True:
            try:
                event_type, data = self.token_queue.get(timeout=0.1)

                if event_type == "token":
                    yield data
                elif event_type == "end":
                    break
                elif event_type == "error":
                    logger.error(f"Streaming error: {data}")
                    yield f"\n\n❌ Error: {data}\n"
                    break

            except queue.Empty:
                continue

    def get_full_response(self) -> str:
        """
        Get the complete response after generation finishes.

        Returns:
            Full LLM response as string
        """
        return "".join(self.current_tokens)


class GradioStreamingHandler(BaseCallbackHandler):
    """
    Streaming handler optimized for Gradio's progressive updates.

    This handler accumulates tokens and yields complete chunks for better
    Gradio rendering performance.
    """

    def __init__(self, chunk_size: int = 5):
        """
        Initialize Gradio streaming handler.

        Args:
            chunk_size: Number of tokens to accumulate before yielding
        """
        self.chunk_size = chunk_size
        self.token_buffer = []
        self.full_response = []
        self.chunk_queue = queue.Queue()
        self.is_active = False
        logger.info(f"GradioStreamingHandler initialized (chunk_size={chunk_size})")

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Called when LLM starts."""
        self.is_active = True
        self.token_buffer = []
        self.full_response = []
        self.chunk_queue.put(("start", ""))
        logger.debug("Gradio streaming started")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """
        Accumulate tokens and yield in chunks.

        Args:
            token: New token from LLM
        """
        if not self.is_active:
            return

        self.token_buffer.append(token)
        self.full_response.append(token)

        # Yield chunk when buffer reaches chunk_size
        if len(self.token_buffer) >= self.chunk_size:
            chunk = "".join(self.token_buffer)
            self.chunk_queue.put(("chunk", chunk))
            self.token_buffer = []

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Flush remaining tokens and signal completion."""
        # Flush any remaining tokens
        if self.token_buffer:
            chunk = "".join(self.token_buffer)
            self.chunk_queue.put(("chunk", chunk))
            self.token_buffer = []

        self.is_active = False
        self.chunk_queue.put(("end", ""))
        logger.debug(f"Gradio streaming ended, total response: {len(self.full_response)} tokens")

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Handle LLM errors."""
        self.is_active = False
        self.chunk_queue.put(("error", str(error)))
        logger.error(f"Gradio streaming error: {error}")

    def stream_chunks(self) -> Generator[str, None, None]:
        """
        Generator for streaming chunks to Gradio.

        Yields:
            Text chunks as they're generated
        """
        accumulated_text = ""

        while True:
            try:
                event_type, data = self.chunk_queue.get(timeout=0.1)

                if event_type == "start":
                    continue
                elif event_type == "chunk":
                    accumulated_text += data
                    yield accumulated_text  # Gradio needs full accumulated text
                elif event_type == "end":
                    yield accumulated_text  # Final update
                    break
                elif event_type == "error":
                    accumulated_text += f"\n\n❌ Error: {data}\n"
                    yield accumulated_text
                    break

            except queue.Empty:
                continue

    def get_complete_response(self) -> str:
        """Get the complete LLM response."""
        return "".join(self.full_response)


def create_streaming_model(base_model, streaming_handler: Optional[BaseCallbackHandler] = None):
    """
    Create a streaming-enabled model from a base model.

    Args:
        base_model: Base LangChain model (ChatOllama, ChatOpenAI, etc.)
        streaming_handler: Optional custom streaming handler

    Returns:
        Model configured for streaming
    """
    if streaming_handler is None:
        streaming_handler = GradioStreamingHandler()

    # Configure model for streaming
    model_config = {
        "streaming": True,
        "callbacks": [streaming_handler]
    }

    # Update model configuration
    if hasattr(base_model, "streaming"):
        base_model.streaming = True
    if hasattr(base_model, "callbacks"):
        if base_model.callbacks:
            base_model.callbacks.append(streaming_handler)
        else:
            base_model.callbacks = [streaming_handler]

    logger.info(f"Created streaming model from {type(base_model).__name__}")
    return base_model, streaming_handler


# Global streaming handler for main agent
_global_streaming_handler = None


def get_global_streaming_handler() -> GradioStreamingHandler:
    """
    Get or create global streaming handler.

    Returns:
        Global GradioStreamingHandler instance
    """
    global _global_streaming_handler
    if _global_streaming_handler is None:
        _global_streaming_handler = GradioStreamingHandler(chunk_size=3)
    return _global_streaming_handler


def reset_global_handler():
    """Reset global streaming handler for new request."""
    global _global_streaming_handler
    _global_streaming_handler = GradioStreamingHandler(chunk_size=3)
    return _global_streaming_handler
