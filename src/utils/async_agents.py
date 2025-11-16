"""Async agent execution system for parallel processing (v1.3.0).

This module enables running multiple sub-agents in parallel for 2-3x faster analysis.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)


class AsyncAgentExecutor:
    """Manages async/parallel execution of DeepAgents sub-agents."""

    def __init__(self, max_workers: int = 4):
        """
        Initialize async agent executor.

        Args:
            max_workers: Maximum number of parallel agent threads
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"AsyncAgentExecutor initialized with {max_workers} workers")

    async def run_agent_async(
        self,
        agent_function: Callable,
        query: str,
        data: Optional[Dict] = None,
        agent_name: str = "agent"
    ) -> Dict[str, Any]:
        """
        Run a single agent asynchronously.

        Args:
            agent_function: The agent function to run
            query: User's research query
            data: Optional data to pass to agent
            agent_name: Name for logging

        Returns:
            Dictionary with agent result and metadata
        """
        start_time = time.time()
        logger.info(f"Starting async execution of {agent_name}")

        try:
            # Run agent in thread pool (since DeepAgents might not be truly async)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                agent_function,
                query,
                data
            )

            execution_time = time.time() - start_time
            logger.info(f"{agent_name} completed in {execution_time:.2f}s")

            return {
                "agent": agent_name,
                "result": result,
                "execution_time": execution_time,
                "status": "success"
            }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"{agent_name} failed after {execution_time:.2f}s")

            return {
                "agent": agent_name,
                "result": None,
                "error": str(e),
                "execution_time": execution_time,
                "status": "error"
            }

    async def run_agents_parallel(
        self,
        agent_configs: List[Dict[str, Any]],
        query: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Run multiple agents in parallel.

        Args:
            agent_configs: List of agent configurations
                Each config should have: {
                    "name": "agent_name",
                    "function": agent_callable,
                    "priority": int (optional, for ordering results)
                }
            query: User's research query
            data: Optional data to pass to agents

        Returns:
            Dictionary with all agent results and aggregate metadata
        """
        start_time = time.time()
        logger.info(f"Starting parallel execution of {len(agent_configs)} agents")

        # Create tasks for all agents
        tasks = []
        for config in agent_configs:
            task = self.run_agent_async(
                agent_function=config["function"],
                query=query,
                data=data,
                agent_name=config["name"]
            )
            tasks.append(task)

        # Run all agents in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        agent_results = {}
        successful = 0
        failed = 0
        total_time = time.time() - start_time

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Agent task raised exception: {result}")
                failed += 1
                continue

            agent_name = result["agent"]
            agent_results[agent_name] = result

            if result["status"] == "success":
                successful += 1
            else:
                failed += 1

        logger.info(
            f"Parallel execution complete: {successful} succeeded, {failed} failed, "
            f"total time {total_time:.2f}s"
        )

        return {
            "agent_results": agent_results,
            "metadata": {
                "total_agents": len(agent_configs),
                "successful": successful,
                "failed": failed,
                "total_execution_time": total_time,
                "parallelization_achieved": True
            }
        }

    async def run_agents_with_streaming(
        self,
        agent_configs: List[Dict[str, Any]],
        query: str,
        data: Optional[Dict] = None,
        callback: Optional[Callable] = None
    ):
        """
        Run agents in parallel with progressive streaming as each completes.

        Args:
            agent_configs: List of agent configurations
            query: User's research query
            data: Optional data to pass to agents
            callback: Optional callback function called when each agent completes
                Signature: callback(agent_name: str, result: Dict)

        Yields:
            Agent results as they complete (fastest first)
        """
        start_time = time.time()
        logger.info(f"Starting streaming parallel execution of {len(agent_configs)} agents")

        # Create tasks for all agents
        tasks = {}
        for config in agent_configs:
            task = asyncio.create_task(
                self.run_agent_async(
                    agent_function=config["function"],
                    query=query,
                    data=data,
                    agent_name=config["name"]
                )
            )
            tasks[task] = config["name"]

        # Yield results as they complete
        completed = 0
        failed = 0

        for coro in asyncio.as_completed(tasks.keys()):
            result = await coro
            agent_name = tasks[coro]
            completed += 1

            if result["status"] == "success":
                logger.info(
                    f"Agent {agent_name} completed ({completed}/{len(agent_configs)})"
                )
            else:
                failed += 1
                logger.warning(
                    f"Agent {agent_name} failed ({completed}/{len(agent_configs)})"
                )

            # Call callback if provided
            if callback:
                try:
                    callback(agent_name, result)
                except Exception as e:
                    logger.exception(f"Callback failed for {agent_name}: {e}")

            # Yield result for streaming
            yield result

        total_time = time.time() - start_time
        logger.info(
            f"Streaming execution complete: {completed - failed} succeeded, "
            f"{failed} failed, total time {total_time:.2f}s"
        )

    def shutdown(self):
        """Shutdown the thread pool executor."""
        logger.info("Shutting down AsyncAgentExecutor")
        self.executor.shutdown(wait=True)

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.shutdown()
        except:
            pass


# Global executor instance
_executor_instance = None


def get_async_executor() -> AsyncAgentExecutor:
    """
    Get global async executor instance (singleton pattern).

    Returns:
        AsyncAgentExecutor instance
    """
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = AsyncAgentExecutor(max_workers=4)
    return _executor_instance


# Convenience functions for backward compatibility

async def run_multiple_agents_parallel(
    agents: List[Dict],
    query: str,
    data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Convenience function to run multiple agents in parallel.

    Args:
        agents: List of agent configs
        query: Research query
        data: Optional data

    Returns:
        Combined results from all agents
    """
    executor = get_async_executor()
    return await executor.run_agents_parallel(agents, query, data)


async def stream_agent_results(
    agents: List[Dict],
    query: str,
    data: Optional[Dict] = None,
    callback: Optional[Callable] = None
):
    """
    Convenience function to stream agent results as they complete.

    Args:
        agents: List of agent configs
        query: Research query
        data: Optional data
        callback: Optional completion callback

    Yields:
        Agent results as they complete
    """
    executor = get_async_executor()
    async for result in executor.run_agents_with_streaming(agents, query, data, callback):
        yield result
