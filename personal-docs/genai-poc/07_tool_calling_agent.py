"""
07 - Tool-Calling Agent (Snowflake + API Integration)
=====================================================
An agent that can query databases, call APIs, and take real actions.
This demonstrates how to give an LLM access to your actual systems.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver


# ============================================================
# Tool Definitions
# ============================================================

@tool
def query_snowflake(sql: str) -> str:
    """
    Execute a SELECT query against Snowflake and return results.
    Only SELECT queries are allowed for safety.
    """
    # --- MOCK IMPLEMENTATION ---
    # In production, replace with actual Snowflake connector:
    #
    # import snowflake.connector
    # conn = snowflake.connector.connect(
    #     account=os.getenv("SNOWFLAKE_ACCOUNT"),
    #     user=os.getenv("SNOWFLAKE_USER"),
    #     password=os.getenv("SNOWFLAKE_PASSWORD"),
    #     warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    #     database=os.getenv("SNOWFLAKE_DATABASE"),
    # )
    # cursor = conn.cursor()
    # cursor.execute(sql)
    # results = cursor.fetchall()
    # columns = [desc[0] for desc in cursor.description]
    # return format_results(columns, results)

    if not sql.strip().upper().startswith("SELECT"):
        return "ERROR: Only SELECT queries are permitted."

    # Mock responses based on query content
    if "count" in sql.lower() and "customers" in sql.lower():
        return "| COUNT | \n|-------|\n| 892,451 |"
    elif "tables" in sql.lower() or "information_schema" in sql.lower():
        return """| TABLE_NAME | ROW_COUNT | LAST_MODIFIED |
|------------|-----------|---------------|
| CUSTOMERS | 892,451 | 2024-10-15 |
| BILLING | 12,340,000 | 2024-10-15 |
| METERS | 1,205,000 | 2024-10-14 |
| USAGE_HOURLY | 450,000,000 | 2024-10-15 |"""
    elif "billing" in sql.lower():
        return """| MONTH | TOTAL_REVENUE | AVG_BILL |
|-------|---------------|----------|
| 2024-08 | $145,230,000 | $162.73 |
| 2024-09 | $138,450,000 | $155.12 |
| 2024-10 | $152,100,000 | $170.42 |"""
    else:
        return f"Query executed: {sql}\n(Mock: 0 rows returned)"


@tool
def get_pipeline_status(pipeline_name: str) -> str:
    """Check the status of an ETL pipeline by name."""
    # Mock - in production, check CloudWatch/Step Functions/Airflow
    pipelines = {
        "billing_daily": {"status": "✅ SUCCESS", "last_run": "2024-10-15 06:00 UTC", "duration": "4m 32s", "records": "1.2M"},
        "customer_cdc": {"status": "✅ SUCCESS", "last_run": "2024-10-15 08:15 UTC", "duration": "2m 10s", "records": "3,421"},
        "meter_reads": {"status": "⚠️ WARNING", "last_run": "2024-10-15 05:00 UTC", "duration": "12m 45s", "records": "5.8M", "warning": "Slower than usual"},
        "nem_export": {"status": "❌ FAILED", "last_run": "2024-10-15 04:00 UTC", "error": "Timeout connecting to PowerClerk API"},
    }

    pipeline = pipelines.get(pipeline_name.lower().replace(" ", "_"))
    if not pipeline:
        available = ", ".join(pipelines.keys())
        return f"Pipeline '{pipeline_name}' not found. Available: {available}"

    result = f"Pipeline: {pipeline_name}\n"
    for key, value in pipeline.items():
        result += f"  {key}: {value}\n"
    return result


@tool
def check_data_quality(table_name: str) -> str:
    """Run data quality checks on a Snowflake table."""
    # Mock
    checks = {
        "customers": {
            "null_check": "✅ No nulls in required fields",
            "duplicate_check": "✅ No duplicate customer IDs",
            "freshness": "✅ Data updated within last 24h",
            "row_count_trend": "✅ Within 5% of 7-day average",
        },
        "billing": {
            "null_check": "✅ No nulls in required fields",
            "duplicate_check": "⚠️ 3 duplicate invoice IDs found",
            "freshness": "✅ Data updated within last 24h",
            "row_count_trend": "✅ Within expected range",
            "value_range": "⚠️ 12 records with negative amounts",
        },
        "usage_hourly": {
            "null_check": "✅ No nulls in required fields",
            "duplicate_check": "✅ No duplicates",
            "freshness": "❌ Data is 36 hours stale",
            "row_count_trend": "⚠️ 15% below 7-day average",
        },
    }

    table = table_name.lower().replace(" ", "_")
    if table not in checks:
        return f"No quality checks configured for '{table_name}'. Available: {', '.join(checks.keys())}"

    result = f"Data Quality Report: {table_name}\n{'=' * 40}\n"
    for check, status in checks[table].items():
        result += f"  {check}: {status}\n"
    return result


@tool
def create_jira_ticket(title: str, description: str, priority: str = "medium") -> str:
    """Create a Jira ticket for tracking issues."""
    # Mock
    import random
    ticket_id = f"DATA-{random.randint(1000, 9999)}"
    return f"✅ Created ticket {ticket_id}: '{title}' (Priority: {priority})"


@tool
def send_slack_alert(channel: str, message: str) -> str:
    """Send an alert to a Slack channel."""
    # Mock
    return f"✅ Alert sent to #{channel}: {message}"


# ============================================================
# Agent Definition
# ============================================================

def create_data_ops_agent():
    """
    A Data Ops agent that can:
    - Query Snowflake
    - Check pipeline status
    - Run data quality checks
    - Create Jira tickets
    - Send Slack alerts
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    memory = MemorySaver()

    tools = [
        query_snowflake,
        get_pipeline_status,
        check_data_quality,
        create_jira_ticket,
        send_slack_alert,
    ]

    agent = create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        state_modifier="""You are a Data Operations assistant for a data engineering team.

Your capabilities:
1. Query Snowflake (SELECT only) for data analysis
2. Check ETL pipeline status
3. Run data quality checks on tables
4. Create Jira tickets for issues
5. Send Slack alerts for urgent problems

Guidelines:
- Always check data quality when asked about table health
- If you find issues, offer to create a Jira ticket
- For critical failures, suggest sending a Slack alert
- Be concise and actionable in responses
- Use tables to format query results nicely""",
    )

    return agent


# ============================================================
# Demo: Interactive Data Ops Session
# ============================================================

def demo_data_ops():
    """Run a demo conversation with the Data Ops agent."""
    agent = create_data_ops_agent()
    config = {"configurable": {"thread_id": "demo-session"}}

    print("=== Data Operations Agent ===\n")

    conversations = [
        "What tables do we have in Snowflake and how big are they?",
        "Check the status of all our ETL pipelines",
        "The nem_export pipeline failed. Run data quality checks on the billing table and create a ticket if there are issues.",
        "Show me the billing revenue trend for the last 3 months",
    ]

    for msg in conversations:
        print(f"👤 User: {msg}")
        print("-" * 50)

        result = agent.invoke(
            {"messages": [("human", msg)]},
            config=config,
        )

        # Get the final AI response
        final_msg = result["messages"][-1]
        print(f"🤖 Agent: {final_msg.content}\n")
        print("=" * 60 + "\n")


# ============================================================
# Interactive mode
# ============================================================

def interactive_data_ops():
    """Run the Data Ops agent interactively."""
    agent = create_data_ops_agent()
    config = {"configurable": {"thread_id": "interactive-session"}}

    print("\n" + "=" * 60)
    print("  Data Operations Agent - Interactive Mode")
    print("  Type 'quit' to exit")
    print("=" * 60 + "\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "quit":
            break
        if not user_input:
            continue

        result = agent.invoke(
            {"messages": [("human", user_input)]},
            config=config,
        )

        print(f"\nAgent: {result['messages'][-1].content}\n")


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  TOOL-CALLING AGENT (Data Ops)")
    print("=" * 60)

    demo_data_ops()

    # Uncomment for interactive mode:
    # interactive_data_ops()
