"""
04 - LangGraph Agent
====================
Build a stateful agent with tools using LangGraph.
This is the most powerful pattern - an LLM that can reason, use tools, 
and maintain complex state across interactions.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Example 1: Simple ReAct Agent with Tools
# ============================================================

def simple_agent():
    """
    A ReAct agent that can use tools to answer questions.
    
    ReAct pattern: Reason → Act → Observe → Repeat
    
    LangGraph models this as a graph:
    - Nodes: steps in the workflow (call LLM, execute tool)
    - Edges: transitions between steps
    - State: shared data that flows through the graph
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent

    # --- Define tools the agent can use ---

    @tool
    def get_weather(city: str) -> str:
        """Get the current weather for a city."""
        # Mock implementation - in production, call a real API
        weather_data = {
            "portland": "72°F, partly cloudy, wind 8mph NW",
            "seattle": "65°F, overcast, wind 12mph W",
            "san francisco": "68°F, foggy, wind 15mph W",
        }
        return weather_data.get(city.lower(), f"Weather data not available for {city}")

    @tool
    def calculate_energy_cost(kwh: float, rate: float = 0.12) -> str:
        """Calculate electricity cost given usage in kWh and rate per kWh."""
        cost = kwh * rate
        return f"{kwh} kWh at ${rate}/kWh = ${cost:.2f}"

    @tool
    def search_documentation(query: str) -> str:
        """Search internal documentation for relevant information."""
        # Mock - in production, this would search your actual docs
        docs = {
            "snowflake": "Snowflake is our cloud data warehouse. Connect via account: myorg.us-west-2",
            "lambda": "Lambda functions are deployed via CloudFormation. Runtime: Python 3.11",
            "etl": "ETL pipelines run on schedule via EventBridge. Logs in CloudWatch.",
            "langgraph": "LangGraph builds stateful agents with graph-based workflows.",
        }
        for key, value in docs.items():
            if key in query.lower():
                return value
        return "No documentation found for that query."

    # --- Create the agent ---
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    agent = create_react_agent(
        llm,
        tools=[get_weather, calculate_energy_cost, search_documentation],
        state_modifier="""You are a helpful assistant for enterprise employees.
You have access to tools for weather, energy calculations, and documentation search.
Always use tools when they can help answer a question.
Be concise in your final answers.""",
    )

    # --- Run the agent ---
    print("=== LangGraph ReAct Agent ===\n")

    queries = [
        "What's the weather like in Portland?",
        "How much would 500 kWh of electricity cost at the standard rate?",
        "What do we use for our data warehouse?",
        "What's the weather in Portland and how much would it cost to run AC for 8 hours at 2kW?",
    ]

    for query in queries:
        print(f"User: {query}")
        result = agent.invoke({"messages": [("human", query)]})
        # Get the last AI message
        final_message = result["messages"][-1]
        print(f"Agent: {final_message.content}\n")

    return agent


# ============================================================
# Example 2: Custom LangGraph workflow (multi-step agent)
# ============================================================

def custom_graph_agent():
    """
    Build a custom graph for a multi-step workflow:
    1. Classify the user's intent
    2. Route to appropriate handler
    3. Generate response
    
    This shows the power of LangGraph for complex workflows.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, AIMessage
    from langgraph.graph import StateGraph, MessagesState, START, END

    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # --- Define the graph nodes ---

    def classify_intent(state: MessagesState):
        """Classify what the user wants."""
        messages = state["messages"]
        last_message = messages[-1].content

        classification_prompt = f"""Classify this message into one category:
- TECHNICAL: coding, data, infrastructure questions
- GENERAL: general knowledge, weather, small talk
- TASK: requests to do something specific

Message: {last_message}

Respond with just the category name."""

        response = llm.invoke([HumanMessage(content=classification_prompt)])
        category = response.content.strip().upper()

        # Store classification in state by adding a system-like message
        return {"messages": [AIMessage(content=f"[CLASSIFIED: {category}]")]}

    def handle_technical(state: MessagesState):
        """Handle technical questions with detailed responses."""
        messages = state["messages"]
        # Find the original user message (skip classification)
        user_msg = next(m for m in messages if isinstance(m, HumanMessage))

        response = llm.invoke([
            HumanMessage(content=f"""You are a senior data engineer. 
Answer this technical question thoroughly but concisely.
Include code examples if relevant.

Question: {user_msg.content}""")
        ])
        return {"messages": [response]}

    def handle_general(state: MessagesState):
        """Handle general questions casually."""
        messages = state["messages"]
        user_msg = next(m for m in messages if isinstance(m, HumanMessage))

        response = llm.invoke([
            HumanMessage(content=f"""Answer this casually and briefly: {user_msg.content}""")
        ])
        return {"messages": [response]}

    def handle_task(state: MessagesState):
        """Handle task requests with action items."""
        messages = state["messages"]
        user_msg = next(m for m in messages if isinstance(m, HumanMessage))

        response = llm.invoke([
            HumanMessage(content=f"""The user wants to do something. 
Break it into clear action items.

Request: {user_msg.content}""")
        ])
        return {"messages": [response]}

    # --- Define routing logic ---

    def route_by_intent(state: MessagesState):
        """Route to the right handler based on classification."""
        messages = state["messages"]
        # Find the classification message
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and "[CLASSIFIED:" in msg.content:
                if "TECHNICAL" in msg.content:
                    return "handle_technical"
                elif "TASK" in msg.content:
                    return "handle_task"
                else:
                    return "handle_general"
        return "handle_general"

    # --- Build the graph ---
    workflow = StateGraph(MessagesState)

    # Add nodes
    workflow.add_node("classify", classify_intent)
    workflow.add_node("handle_technical", handle_technical)
    workflow.add_node("handle_general", handle_general)
    workflow.add_node("handle_task", handle_task)

    # Add edges
    workflow.add_edge(START, "classify")
    workflow.add_conditional_edges("classify", route_by_intent)
    workflow.add_edge("handle_technical", END)
    workflow.add_edge("handle_general", END)
    workflow.add_edge("handle_task", END)

    # Compile
    app = workflow.compile()

    # --- Test the workflow ---
    print("\n=== Custom LangGraph Workflow ===\n")

    test_messages = [
        "How do I optimize a Snowflake query with clustering keys?",
        "What's a good restaurant in Portland?",
        "I need to set up a new ETL pipeline for billing data",
    ]

    for msg in test_messages:
        print(f"User: {msg}")
        result = app.invoke({"messages": [HumanMessage(content=msg)]})
        # Get the final response (last AI message that isn't classification)
        final = [m for m in result["messages"] if isinstance(m, AIMessage) and "[CLASSIFIED:" not in m.content]
        if final:
            print(f"Agent: {final[-1].content}\n")
        print("-" * 40 + "\n")

    return app


# ============================================================
# Example 3: Agent with persistent memory (conversation)
# ============================================================

def agent_with_memory():
    """
    LangGraph agent that maintains conversation history across invocations.
    Uses checkpointing for state persistence.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent
    from langgraph.checkpoint.memory import MemorySaver

    @tool
    def note_taker(note: str) -> str:
        """Save a note for later reference."""
        return f"Note saved: {note}"

    llm = ChatOpenAI(model="gpt-4o", temperature=0.5)

    # MemorySaver keeps state in memory (use SqliteSaver for persistence)
    memory = MemorySaver()

    agent = create_react_agent(
        llm,
        tools=[note_taker],
        checkpointer=memory,
        state_modifier="You are a helpful assistant. Remember previous conversations.",
    )

    # Thread ID groups messages into a conversation
    config = {"configurable": {"thread_id": "session-1"}}

    print("\n=== Agent with Memory ===\n")

    # Multi-turn conversation
    conversations = [
        "Hi, I'm working on the NEMA project. Can you remember that?",
        "Save a note: need to review the CDC lambda handler this week",
        "What project am I working on?",
    ]

    for msg in conversations:
        print(f"User: {msg}")
        result = agent.invoke({"messages": [("human", msg)]}, config=config)
        print(f"Agent: {result['messages'][-1].content}\n")


# ============================================================
# Run examples
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  LANGGRAPH AGENTS")
    print("=" * 60)

    simple_agent()
    custom_graph_agent()
    agent_with_memory()
