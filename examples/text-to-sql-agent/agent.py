import argparse
import os
import sys
from typing import Any

import yaml
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessageChunk
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from rich.console import Console
from rich.panel import Panel
from rich.status import Status

# Load environment variables
load_dotenv()

console = Console()


def load_config() -> dict[str, Any]:
    """Load configuration from config.yaml with env var substitution"""
    import re

    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.yaml")

    if not os.path.exists(config_path):
        console.print(f"[bold red]Error:[/bold red] {config_path} not found.")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern for ${VAR} or ${VAR:-default}
    pattern = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")

    def replacer(match):
        env_var = match.group(1)
        default_value = match.group(2)
        # return the value from env, or the default, or the original string if neither exist
        res = os.getenv(env_var)
        if res is not None:
            return res
        if default_value is not None:
            return default_value
        return match.group(0)

    content = pattern.sub(replacer, content)
    return yaml.safe_load(content)


def create_sql_deep_agent():
    """Create and return a text-to-SQL Deep Agent"""

    # Get base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Load config
    config = load_config()

    # Database configuration
    db_config = config.get("database", {})
    db_type = db_config.get("type", "sqlite")

    if db_type == "sqlite":
        sqlite_config = db_config.get("sqlite", {})
        db_path = sqlite_config.get("path", "chinook.db")
        if not os.path.isabs(db_path):
            db_path = os.path.join(base_dir, db_path)
        db_uri = f"sqlite:///{db_path}"
    elif db_type == "mysql":
        mysql_config = db_config.get("mysql", {})
        user = mysql_config.get("user", "root")
        password = mysql_config.get("password", "")
        host = mysql_config.get("host", "localhost")
        port = mysql_config.get("port", 3306)
        db_name = mysql_config.get("database", "")
        db_uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
    else:
        console.print(
            f"[bold red]Error:[/bold red] Unsupported database type: {db_type}"
        )
        sys.exit(1)

    # Initialize SQLDatabase
    db = SQLDatabase.from_uri(db_uri, sample_rows_in_table_info=3)

    # Model configuration
    model_config = config.get("model", {})
    provider = model_config.get("provider", "anthropic")
    model_name = model_config.get("model", "claude-3-5-sonnet-20240620")
    temperature = model_config.get("temperature", 0)

    # Merge provider-specific config (like base_url, api_key) if present
    init_params = {
        "model": model_name,
        "model_provider": provider,
        "temperature": temperature,
    }

    # Pass through additional model parameters
    for key, value in model_config.items():
        if key not in ["provider", "model", "temperature"]:
            init_params[key] = value

    # Initialize model using init_chat_model
    model = init_chat_model(**init_params)

    # Create SQL toolkit and get tools
    toolkit = SQLDatabaseToolkit(db=db, llm=model)
    sql_tools = toolkit.get_tools()

    # Create the Deep Agent with all parameters
    agent = create_deep_agent(
        model=model,
        memory=["./AGENTS.md"],  # Agent identity and general instructions
        skills=["./skills/"],  # Specialized workflows
        tools=sql_tools,  # SQL database tools
        subagents=[],  # No subagents needed
        backend=FilesystemBackend(
            root_dir=base_dir, virtual_mode=True
        ),  # Persistent file storage
    )

    return agent


def main():
    """Main entry point for the SQL Deep Agent CLI"""
    parser = argparse.ArgumentParser(
        description="Text-to-SQL Deep Agent - Claude Code Style",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent.py "What are the top 5 best-selling artists?"
  python agent.py "How many customers are from Canada?"
        """,
    )
    parser.add_argument(
        "question",
        type=str,
        help="Natural language question to answer",
    )

    args = parser.parse_args()

    # Logo/Header
    console.print("\n[bold]Deep SQL Agent[/bold] [dim]v0.1.0[/dim]\n")
    console.print(f"[bold cyan]User:[/bold cyan] {args.question}\n")

    # Initialization status
    with Status(
        "[dim]Initializing agent...[/dim]", console=console, spinner="dots"
    ) as status:
        agent = create_sql_deep_agent()

    # Streaming and state management
    full_response = ""

    try:
        with Status(
            "[dim]Thinking...[/dim]", console=console, spinner="dots"
        ) as status:
            # Stream the agent's work
            for stream_mode, data in agent.stream(
                {"messages": [{"role": "user", "content": args.question}]},
                stream_mode=["messages", "updates"],
            ):
                if stream_mode == "messages":
                    chunk, _ = data
                    # console.print("chunk:", chunk)
                    if not isinstance(chunk, AIMessageChunk):
                        continue
                    if hasattr(chunk, "content") and chunk.content:
                        # Append to buffer
                        full_response += chunk.content

                        # Once we start getting text, stop the thinking spinner
                        # but keep it clean
                        if status._live:
                            status.stop()

                        # Show output to the user progressively
                        console.print(chunk.content, end="")

                elif stream_mode == "updates":
                    for node_name, node_data in data.items():
                        if not node_data:
                            continue

                        # Tool call detection
                        if "messages" in node_data and isinstance(
                            node_data["messages"], list
                        ):
                            for msg in node_data["messages"]:
                                if hasattr(msg, "tool_calls") and msg.tool_calls:
                                    for tc in msg.tool_calls:
                                        tool_name = tc["name"]
                                        # Update status and restart spinner if it's currently stopped
                                        status.update(
                                            f"[dim]› running {tool_name}...[/dim]"
                                        )
                                        if not status._live:
                                            status.start()

                                        # Also log a very clean indicator
                                        console.print(
                                            f"\n[dim]› {tool_name}({str(tc['args'])[:80]}...)[/dim]"
                                        )

                                # Process tool results
                                if node_name == "tools":
                                    status.update("[dim]Analyzing results...[/dim]")

        # After streaming is done, if we have a full response, re-render it as beautiful Markdown
        # if full_response:
        #     console.print("\n")
        #     console.print(Markdown(full_response))
        #     console.print("\n")

    except Exception as e:
        import traceback

        console.print(
            Panel(
                f"[bold red]Error:[/bold red]\n\n{str(e)}\n\n{traceback.format_exc()}",
                border_style="red",
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
