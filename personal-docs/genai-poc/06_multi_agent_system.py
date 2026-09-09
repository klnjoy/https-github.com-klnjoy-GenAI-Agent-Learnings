"""
06 - Multi-Agent System
=======================
Multiple specialized agents that collaborate to solve complex tasks.
Pattern: Supervisor routes work to specialized workers.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import create_react_agent


# ============================================================
# Example 1: Supervisor + Workers Pattern
# ============================================================

def supervisor_agent_system():
    """
    Architecture:
    - Supervisor: decides which worker should handle the task
    - Researcher: finds information and context
    - Writer: produces polished output
    - Coder: writes code solutions
    
    The supervisor orchestrates the flow between workers.
    """
    from pydantic import BaseModel, Field
    from typing import Literal

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    creative_llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

    # --- Define routing schema ---
    class RouteDecision(BaseModel):
        """Supervisor's routing decision."""
        next_worker: Literal["researcher", "writer", "coder", "FINISH"] = Field(
            description="Which worker should handle this next, or FINISH if done"
        )
        instructions: str = Field(
            description="Specific instructions for the next worker"
        )

    # --- Worker definitions ---
    def make_researcher_node():
        """Researcher gathers information and provides context."""

        @tool
        def search_knowledge_base(query: str) -> str:
            """Search the internal knowledge base for relevant information."""
            # Mock knowledge base
            kb = {
                "snowflake": "The org uses Snowflake Enterprise on AWS us-west-2. Key databases: RAW, STAGING, ANALYTICS. Warehouses: ETL_WH (XL), ANALYTICS_WH (L), DEV_WH (S).",
                "lambda": "ETL Lambdas use Python 3.11, deployed via CloudFormation. Timeout: 15min. Memory: 512MB-3GB. Layers: pandas, snowflake-connector.",
                "architecture": "Source → S3 Raw → Lambda ETL → Snowflake Staging → dbt → Analytics layer. CDC via DynamoDB streams.",
                "security": "All data encrypted at rest (AES-256) and in transit (TLS 1.2). IAM roles per service. Secrets in AWS Secrets Manager.",
            }
            results = []
            for key, value in kb.items():
                if key in query.lower():
                    results.append(value)
            return "\n".join(results) if results else "No specific info found. Use general knowledge."

        agent = create_react_agent(
            llm,
            tools=[search_knowledge_base],
            state_modifier="You are a research specialist. Find relevant information and summarize findings clearly. Always use your search tool.",
        )
        return agent

    def make_writer_node():
        """Writer produces polished, well-structured content."""

        @tool
        def format_as_markdown(content: str) -> str:
            """Format content as clean markdown."""
            return content  # The LLM handles formatting

        agent = create_react_agent(
            creative_llm,
            tools=[format_as_markdown],
            state_modifier="""You are a technical writer. Take research or rough notes 
and produce polished, well-organized documentation. Use markdown formatting.
Be concise but thorough.""",
        )
        return agent

    def make_coder_node():
        """Coder writes implementation code."""

        @tool
        def validate_python(code: str) -> str:
            """Validate Python code syntax."""
            try:
                compile(code, "<string>", "exec")
                return "✅ Code is syntactically valid"
            except SyntaxError as e:
                return f"❌ Syntax error: {e}"

        agent = create_react_agent(
            llm,
            tools=[validate_python],
            state_modifier="""You are a senior Python developer. Write clean, well-documented code.
Follow best practices: type hints, docstrings, error handling.
Always validate your code before submitting.""",
        )
        return agent

    # --- Build the supervisor graph ---
    researcher = make_researcher_node()
    writer = make_writer_node()
    coder = make_coder_node()

    def supervisor_node(state: MessagesState):
        """Supervisor decides what to do next."""
        structured_llm = llm.with_structured_output(RouteDecision)

        messages = state["messages"]
        # Build context for supervisor
        supervisor_prompt = f"""You are a project supervisor managing a team of:
- researcher: finds information, searches knowledge bases
- writer: produces polished documentation and explanations  
- coder: writes Python code solutions

Based on the conversation so far, decide:
1. Which worker should handle the next step
2. What specific instructions to give them
3. Or if the task is COMPLETE, route to FINISH

Look at the full conversation to understand what's been done and what remains."""

        decision = structured_llm.invoke(
            [SystemMessage(content=supervisor_prompt)] + messages
        )

        return {
            "messages": [
                AIMessage(content=f"[SUPERVISOR → {decision.next_worker}]: {decision.instructions}")
            ]
        }

    def route_supervisor(state: MessagesState):
        """Route based on supervisor's decision."""
        last_msg = state["messages"][-1].content
        if "FINISH" in last_msg:
            return END
        elif "researcher" in last_msg:
            return "researcher"
        elif "writer" in last_msg:
            return "writer"
        elif "coder" in last_msg:
            return "coder"
        return END

    def researcher_node(state: MessagesState):
        result = researcher.invoke(state)
        return {"messages": result["messages"][-1:]}

    def writer_node(state: MessagesState):
        result = writer.invoke(state)
        return {"messages": result["messages"][-1:]}

    def coder_node(state: MessagesState):
        result = coder.invoke(state)
        return {"messages": result["messages"][-1:]}

    # --- Assemble the graph ---
    workflow = StateGraph(MessagesState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("coder", coder_node)

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges("supervisor", route_supervisor)
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("writer", "supervisor")
    workflow.add_edge("coder", "supervisor")

    app = workflow.compile()

    # --- Test it ---
    print("=== Multi-Agent Supervisor System ===\n")

    tasks = [
        "Research our Snowflake setup and write a brief onboarding guide for new team members.",
        "Write a Python function that connects to Snowflake and runs a health check query.",
    ]

    for task in tasks:
        print(f"📋 Task: {task}")
        print("-" * 50)

        result = app.invoke(
            {"messages": [HumanMessage(content=task)]},
            {"recursion_limit": 15},
        )

        # Print the final outputs (skip supervisor routing messages)
        for msg in result["messages"]:
            if isinstance(msg, AIMessage) and "[SUPERVISOR" not in msg.content:
                print(f"\n{msg.content}")

        print("\n" + "=" * 60 + "\n")

    return app


# ============================================================
# Example 2: Debate/Critique Pattern
# ============================================================

def debate_agents():
    """
    Two agents debate a topic, improving each other's arguments.
    Pattern: Proposer → Critic → Proposer (refined) → Final
    
    Useful for: code review, document review, decision analysis
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

    from typing import TypedDict, Annotated
    from langgraph.graph import add_messages

    class DebateState(TypedDict):
        messages: Annotated[list, add_messages]
        topic: str
        rounds: int

    def proposer_node(state: DebateState):
        """Makes the initial proposal or refines based on critique."""
        messages = state["messages"]
        topic = state["topic"]

        if len(messages) == 0:
            # Initial proposal
            prompt = f"Make a clear, well-reasoned argument about: {topic}"
        else:
            # Refine based on critique
            prompt = f"""Based on the critique, improve your argument about: {topic}
Address the weak points raised. Keep it concise."""

        response = llm.invoke(
            [SystemMessage(content="You are a thoughtful proposer. Make clear arguments.")] + 
            messages + 
            [HumanMessage(content=prompt)]
        )
        return {"messages": [AIMessage(content=f"[PROPOSER]: {response.content}")]}

    def critic_node(state: DebateState):
        """Critiques the proposal, finds weaknesses."""
        messages = state["messages"]

        response = llm.invoke(
            [SystemMessage(content="You are a constructive critic. Find weaknesses and suggest improvements. Be specific.")] + 
            messages + 
            [HumanMessage(content="Critique the latest proposal. What are the weak points? What's missing?")]
        )
        return {
            "messages": [AIMessage(content=f"[CRITIC]: {response.content}")],
            "rounds": state["rounds"] + 1,
        }

    def should_continue(state: DebateState):
        """Stop after 2 rounds of debate."""
        if state["rounds"] >= 2:
            return "synthesize"
        return "proposer"

    def synthesize_node(state: DebateState):
        """Produce final synthesis incorporating all perspectives."""
        messages = state["messages"]

        response = llm.invoke(
            [SystemMessage(content="Synthesize the debate into a final, balanced conclusion.")] + 
            messages + 
            [HumanMessage(content="Produce a final synthesis that incorporates the best points from both sides. Be concise.")]
        )
        return {"messages": [AIMessage(content=f"[FINAL SYNTHESIS]: {response.content}")]}

    # Build graph
    workflow = StateGraph(DebateState)
    workflow.add_node("proposer", proposer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("synthesize", synthesize_node)

    workflow.add_edge(START, "proposer")
    workflow.add_edge("proposer", "critic")
    workflow.add_conditional_edges("critic", should_continue)
    workflow.add_edge("synthesize", END)

    app = workflow.compile()

    # Test
    print("\n=== Debate Pattern ===\n")

    topic = "Should our team migrate from AWS Lambda to AWS Step Functions for ETL orchestration?"
    print(f"🎯 Topic: {topic}\n")

    result = app.invoke({"messages": [], "topic": topic, "rounds": 0})

    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            print(f"{msg.content}\n")
            print("-" * 40)

    return app


# ============================================================
# Run examples
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  MULTI-AGENT SYSTEMS")
    print("=" * 60)

    supervisor_agent_system()
    debate_agents()
