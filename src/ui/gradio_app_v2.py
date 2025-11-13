"""Enhanced Gradio web interface with streaming and history support."""

import time
import logging
import gradio as gr
from pathlib import Path
from typing import Optional, Generator
import json
from datetime import datetime

from ..utils.config import settings
from ..utils.validation import validate_query
from ..utils.database import get_database

logger = logging.getLogger(__name__)

# Rate limiting storage
_rate_limit_tracker = {}


def rate_limit_check(user_id: str = "default") -> tuple[bool, Optional[str]]:
    """Check if user has exceeded rate limit."""
    current_time = time.time()

    if user_id in _rate_limit_tracker:
        last_request_time = _rate_limit_tracker[user_id]
        time_since_last = current_time - last_request_time

        if time_since_last < settings.RATE_LIMIT_SECONDS:
            wait_time = settings.RATE_LIMIT_SECONDS - time_since_last
            return False, f"Please wait {wait_time:.1f} seconds before submitting another request."

    _rate_limit_tracker[user_id] = current_time
    return True, None


def export_to_json(report: str, symbol: str) -> str:
    """Export research report to JSON file."""
    export_dir = Path(settings.EXPORT_DIR)
    export_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_{timestamp}.json"
    filepath = export_dir / filename

    data = {
        "symbol": symbol,
        "timestamp": timestamp,
        "report": report
    }

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    return str(filepath)


def export_to_text(report: str, symbol: str) -> str:
    """Export research report to text file."""
    export_dir = Path(settings.EXPORT_DIR)
    export_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_{timestamp}.txt"
    filepath = export_dir / filename

    with open(filepath, 'w') as f:
        f.write(f"Stock Research Report: {symbol}\n")
        f.write(f"Generated: {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        f.write(report)

    return str(filepath)


def create_gradio_interface_v2(research_function, research_function_streaming=None):
    """
    Create enhanced Gradio web interface with streaming and history support.

    Args:
        research_function: The function to call for stock research
        research_function_streaming: Optional streaming version of research function

    Returns:
        Gradio Blocks interface
    """

    def run_research_with_validation_streaming(query: str, request: gr.Request) -> Generator[str, None, None]:
        """Run research with streaming output."""
        user_id = request.client.host if request else "default"

        # Validate query
        is_valid, error_msg = validate_query(query)
        if not is_valid:
            logger.warning(f"Invalid query from {user_id}: {error_msg}")
            yield f"❌ Error: {error_msg}"
            return

        # Check rate limit
        is_allowed, rate_error = rate_limit_check(user_id)
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {user_id}")
            yield f"⏱️ {rate_error}"
            return

        # Run research with streaming
        logger.info(f"Starting streaming research for user {user_id}: {query[:50]}...")
        try:
            if research_function_streaming:
                for chunk in research_function_streaming(query):
                    yield chunk
            else:
                # Fallback to non-streaming with simulated progress
                yield "🔄 Processing...\n"
                result = research_function(query)
                yield f"\n\n{result}"

        except Exception as e:
            logger.exception(f"Research failed for {user_id}")
            yield f"\n\n❌ Error: Failed to complete analysis: {str(e)}"

    def load_research_history() -> str:
        """Load research history for display."""
        try:
            db = get_database()
            history = db.get_recent_research(limit=20)

            if not history:
                return "No research history found."

            output = "# 📚 Research History\n\n"
            for item in history:
                output += f"### {item['symbol']} - {item['created_at']}\n"
                output += f"**Query:** {item['query'][:100]}...\n"
                output += f"**ID:** {item['id']}\n\n"
                output += "---\n\n"

            return output

        except Exception as e:
            logger.exception("Failed to load history")
            return f"Error loading history: {str(e)}"

    def load_specific_research(research_id: int) -> str:
        """Load specific research by ID."""
        try:
            if not research_id:
                return "Please enter a research ID"

            db = get_database()
            research = db.get_research_by_id(research_id)

            if not research:
                return f"Research ID {research_id} not found"

            output = f"# Research Report: {research['symbol']}\n\n"
            output += f"**Created:** {research['created_at']}\n"
            output += f"**Query:** {research['query']}\n\n"
            output += "=" * 80 + "\n\n"
            output += research['report']

            return output

        except Exception as e:
            logger.exception("Failed to load research")
            return f"Error: {str(e)}"

    def search_history(search_term: str) -> str:
        """Search research history."""
        try:
            if not search_term:
                return "Please enter a search term"

            db = get_database()
            results = db.search_research(search_term, limit=10)

            if not results:
                return f"No results found for '{search_term}'"

            output = f"# 🔍 Search Results for '{search_term}'\n\n"
            for item in results:
                output += f"### {item['symbol']} - {item['created_at']}\n"
                output += f"**Query:** {item['query'][:100]}...\n"
                output += f"**ID:** {item['id']}\n\n"
                output += "---\n\n"

            return output

        except Exception as e:
            logger.exception("Search failed")
            return f"Error: {str(e)}"

    def export_report(report: str, symbol: str, format: str) -> str:
        """Export report to file."""
        if not report:
            return "❌ No report to export"

        if not symbol:
            symbol = "UNKNOWN"

        try:
            if format == "JSON":
                filepath = export_to_json(report, symbol)
            else:
                filepath = export_to_text(report, symbol)

            return f"✅ Report exported to: {filepath}"
        except Exception as e:
            logger.exception("Export failed")
            return f"❌ Export failed: {str(e)}"

    # Create interface
    with gr.Blocks(title="DeepAgents Stock Research v1.1", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 📊 DeepAgents Stock Research Assistant v1.1

            ### 🚀 NEW Features:
            - **Real-time Streaming** - Watch analysis unfold live
            - **Research History** - Access past analyses
            - **Multi-Stock Comparison** - Compare stocks side-by-side
            - **Async Performance** - 3-5x faster data fetching

            Get comprehensive stock analysis powered by specialized AI agents combining
            **fundamental**, **technical**, **risk**, and **comparison** analysis.
            """
        )

        with gr.Tabs():
            # Tab 1: Main Analysis
            with gr.Tab("🔍 Stock Analysis"):
                gr.Markdown(
                    """
                    ### Example Queries:
                    - *"Comprehensive analysis of Apple (AAPL) for 6-month horizon"*
                    - *"Compare AAPL, MSFT, and GOOGL for portfolio allocation"*
                    - *"Technical analysis and entry points for NVDA"*
                    - *"Risk assessment for Tesla (TSLA)"*
                    """
                )

                with gr.Row():
                    with gr.Column(scale=2):
                        query_input = gr.Textbox(
                            label="Research Query",
                            lines=6,
                            placeholder="Enter your stock research request...\n\nFor comparison: 'Compare AAPL and MSFT'",
                            info="Supports single stock or multi-stock comparison queries"
                        )

                        with gr.Row():
                            run_button = gr.Button("🚀 Run Analysis (Streaming)", variant="primary", size="lg")
                            clear_button = gr.Button("🗑️ Clear", size="lg")

                    with gr.Column(scale=1):
                        gr.Markdown("### ⚙️ Export Options")

                        symbol_input = gr.Textbox(
                            label="Stock Symbol",
                            placeholder="AAPL",
                            info="For export filename"
                        )

                        export_format = gr.Radio(
                            label="Export Format",
                            choices=["Text", "JSON"],
                            value="Text"
                        )

                        export_button = gr.Button("💾 Export Report")

                        export_status = gr.Textbox(
                            label="Export Status",
                            interactive=False
                        )

                output_box = gr.Textbox(
                    label="Research Report (Streaming)",
                    lines=30,
                    max_lines=50,
                    show_copy_button=True,
                    interactive=False
                )

            # Tab 2: Research History
            with gr.Tab("📚 Research History"):
                gr.Markdown("### Browse your research history and reload past analyses")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Recent Research")
                        refresh_button = gr.Button("🔄 Refresh History")
                        history_display = gr.Textbox(
                            label="Recent Analyses",
                            lines=20,
                            interactive=False
                        )

                    with gr.Column():
                        gr.Markdown("#### Load Specific Report")
                        research_id_input = gr.Number(
                            label="Research ID",
                            precision=0,
                            info="Enter ID from history list"
                        )
                        load_button = gr.Button("📄 Load Report")

                        gr.Markdown("#### Search History")
                        search_input = gr.Textbox(
                            label="Search Term",
                            placeholder="Enter stock symbol or keyword..."
                        )
                        search_button = gr.Button("🔍 Search")

                report_display = gr.Textbox(
                    label="Loaded Report",
                    lines=25,
                    interactive=False,
                    show_copy_button=True
                )

        gr.Markdown(
            """
            ---
            ### ℹ️ Information

            **🆕 v1.1 Updates:**
            - Real-time streaming responses
            - Automatic research history saving
            - Multi-stock comparison agent
            - 3-5x faster parallel data fetching

            **Rate Limit:** One request per 10 seconds per user
            **Powered by:** LangChain DeepAgents Framework
            **Data Source:** Yahoo Finance (Real-time)

            ⚠️ **Disclaimer:** This tool is for educational purposes only. Not financial advice.
            """
        )

        # Event handlers - Analysis Tab
        run_button.click(
            fn=run_research_with_validation_streaming,
            inputs=query_input,
            outputs=output_box
        )

        clear_button.click(
            fn=lambda: ("", ""),
            inputs=None,
            outputs=[query_input, output_box]
        )

        export_button.click(
            fn=export_report,
            inputs=[output_box, symbol_input, export_format],
            outputs=export_status
        )

        # Event handlers - History Tab
        refresh_button.click(
            fn=load_research_history,
            inputs=None,
            outputs=history_display
        )

        load_button.click(
            fn=load_specific_research,
            inputs=research_id_input,
            outputs=report_display
        )

        search_button.click(
            fn=search_history,
            inputs=search_input,
            outputs=report_display
        )

        # Load history on page load
        demo.load(
            fn=load_research_history,
            inputs=None,
            outputs=history_display
        )

    return demo
