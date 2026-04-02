# Text-to-SQL Deep Agent

A natural language to SQL query agent powered by LangChain's **Deep Agents** framework.  This is an advanced version of a text-to-SQL agent with planning, filesystem, and subagent capabilities.

## What is Deep Agents?

Deep Agents is a sophisticated agent framework built on LangGraph that provides:

- **Planning capabilities** - Break down complex tasks with `write_todos` tool
- **Filesystem backend** - Save and retrieve context with file operations
- **Subagent spawning** - Delegate specialized tasks to focused agents
- **Context management** - Prevent context window overflow on complex tasks

## Demo Database

Uses the [Chinook database](https://github.com/lerocha/chinook-database) - a sample database representing a digital media store.

## Quick Start

### Prerequisites

- Python 3.11 or higher
- API key for your chosen LLM provider (Anthropic, OpenAI, etc.)
- (Optional) MySQL database if not using the default SQLite
- (Optional) LangSmith API key for tracing ([sign up here](https://smith.langchain.com/))

### Installation

1. Clone the deepagents repository and navigate to this example:

```bash
git clone https://github.com/langchain-ai/deepagents.git
cd deepagents/examples/text-to-sql-agent
```

1. Download the Chinook database:

```bash
# Download the SQLite database file
curl -L -o chinook.db https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite
```

1. Create a virtual environment and install dependencies:

```bash
# Using uv (recommended)
uv venv --python 3.11
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

1. Set up your configuration in `config.yaml`:

```yaml
model:
  provider: "deepseek" # or any other provider
  model: "deepseek-chat"
  temperature: 0
  base_url: "https://api.deepseek.com"
  api_key: "${DEEPSEEK_API_KEY}" # Read from .env

database:
  type: "mysql" # or "sqlite"
  mysql:
    host: "${MYSQL_HOST:-localhost}"
    port: "${MYSQL_PORT:-3306}"
    user: "${MYSQL_USER:-root}"
    password: "${MYSQL_PASSWORD}" # Read from .env
    database: "${MYSQL_DATABASE}"
```

1. Set up your environment variables in `.env`:

```bash
cp .env.example .env
# Add your provider API keys and database credentials:
# DEEPSEEK_API_KEY=your_key
# MYSQL_PASSWORD=your_password
```

### Features

- **Beautiful CLI**: Claude Code-inspired interface with dynamic icons, spinners, and colors.
- **Streaming Output**: Watch the agent think and respond in real-time with Markdown formatting.
- **Process Visibility**: Minimalist tool-call tracking with status indicators (`› running`).
- **Secure Configuration**: Sensitive information is managed via environment variables.

### Architecture

```text
User Question
      ↓
Deep Agent (with streaming)
      ├─ config.yaml (Environment variable substitution)
      ├─ init_chat_model (Unified LLM access)
      ├─ write_todos (plan the approach)
      ├─ SQL Tools (Output visible in real-time)
```

```text
User Question
      ↓
Deep Agent (with planning)
      ├─ config.yaml (Model & DB settings)
      ├─ init_chat_model (Unified LLM access)
      ├─ write_todos (plan the approach)
      ├─ SQL Tools
      │  ├─ list_tables
      │  ├─ get_schema
      │  ├─ query_checker
      │  └─ execute_query
      └─ Subagent Spawning (optional)
      ↓
Database (SQLite or MySQL)
      ↓
Formatted Answer
```

### Configuration

Deep Agents uses **progressive disclosure** with memory files and skills:

**AGENTS.md** (always loaded) - Contains:

- Agent identity and role
- Core principles and safety rules
- General guidelines
- Communication style

**skills/** (loaded on-demand) - Specialized workflows:

- **query-writing** - How to write and execute SQL queries (simple and complex)
- **schema-exploration** - How to discover database structure and relationships

The agent sees skill descriptions in its context but only loads the full SKILL.md instructions when it determines which skill is needed for the current task. This **progressive disclosure** pattern keeps context efficient while providing deep expertise when needed.

## Example Queries

### Simple Query

```text
"How many customers are from Canada?"
```

The agent will directly query and return the count.

### Complex Query with Planning

```text
"Which employee generated the most revenue and from which countries?"
```

The agent will:

1. Use `write_todos` to plan the approach
2. Identify required tables (Employee, Invoice, Customer)
3. Plan the JOIN structure
4. Execute the query
5. Format results with analysis

## Deep Agent Output Example

The Deep Agent shows its reasoning process:

```text
Question: Which employee generated the most revenue by country?

[Planning Step]
...
```

## Project Structure

```text
text-to-sql-agent/
├── agent.py                      # Core Deep Agent implementation with CLI
...
```

## Requirements

All dependencies are specified in `pyproject.toml`:

- deepagents >= 0.3.5
- langchain >= 1.2.3
- langchain-anthropic >= 1.3.1
- langchain-community >= 0.3.0
- langgraph >= 1.0.6
- sqlalchemy >= 2.0.0
- python-dotenv >= 1.0.0
- tavily-python >= 0.5.0
- rich >= 13.0.0

## LangSmith Integration

### Setup

1. Sign up for a free account at [LangSmith](https://smith.langchain.com/)
2. Create an API key from your account settings
3. Add these variables to your `.env` file:

```text
LANGCHAIN_TRACING_V2=true
...
```

### What You'll See

When configured, every query is automatically traced:

![Deep Agent LangSmith Trace Example](text-to-sql-langsmith-trace.png)

You can view:

- Complete execution trace with all tool calls
- Planning steps (write_todos)
- Filesystem operations
- Token usage and costs
- Generated SQL queries
- Error messages and retry attempts

View your traces at: <https://smith.langchain.com/>

## Resources

- [Deep Agents Documentation](https://docs.langchain.com/oss/python/deepagents/overview)
- [LangChain](https://www.langchain.com/)
- [Claude Sonnet 4.5](https://www.anthropic.com/claude)
- [Chinook Database](https://github.com/lerocha/chinook-database)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
