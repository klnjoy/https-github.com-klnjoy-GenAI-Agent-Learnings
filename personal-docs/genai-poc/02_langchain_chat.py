"""
02 - LangChain Chat Assistant with Memory
==========================================
Build a conversational assistant that remembers context across messages.
This is the core pattern for any chatbot/assistant application.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Example 1: Chat with in-memory conversation history
# ============================================================

def chat_with_memory():
    """
    A chat assistant that maintains conversation history.
    
    Key concepts:
    - ChatMessageHistory: stores messages in memory
    - RunnableWithMessageHistory: wraps a chain to auto-manage history
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.chat_history import InMemoryChatMessageHistory
    from langchain_core.runnables.history import RunnableWithMessageHistory

    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

    # Define the prompt with a placeholder for conversation history
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant for enterprise employees. 
You help with questions about energy, data engineering, and general topics.
Be friendly and concise."""),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    # Create the chain
    chain = prompt | llm

    # Store for session histories (in production, use Redis/DB)
    session_store = {}

    def get_session_history(session_id: str):
        if session_id not in session_store:
            session_store[session_id] = InMemoryChatMessageHistory()
        return session_store[session_id]

    # Wrap the chain with message history management
    chat_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )

    # Simulate a conversation
    print("=== Chat with Memory ===")
    print("(The assistant remembers previous messages)\n")

    config = {"configurable": {"session_id": "user-123"}}

    # Turn 1
    response1 = chat_with_history.invoke(
        {"input": "Hi! My name is Alex and I work in the data engineering team."},
        config=config,
    )
    print(f"User: Hi! My name is Alex and I work in the data engineering team.")
    print(f"Assistant: {response1.content}\n")

    # Turn 2 - the assistant should remember the name
    response2 = chat_with_history.invoke(
        {"input": "What are some good Python libraries for ETL pipelines?"},
        config=config,
    )
    print(f"User: What are some good Python libraries for ETL pipelines?")
    print(f"Assistant: {response2.content}\n")

    # Turn 3 - the assistant should still know the context
    response3 = chat_with_history.invoke(
        {"input": "Which of those would you recommend for someone on my team?"},
        config=config,
    )
    print(f"User: Which of those would you recommend for someone on my team?")
    print(f"Assistant: {response3.content}\n")

    return chat_with_history


# ============================================================
# Example 2: Interactive chat loop
# ============================================================

def interactive_chat():
    """
    Run an interactive chat session in the terminal.
    Type 'quit' to exit.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.chat_history import InMemoryChatMessageHistory
    from langchain_core.runnables.history import RunnableWithMessageHistory

    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a knowledgeable assistant that helps with:
- Data engineering questions (Snowflake, Python, ETL)
- Cloud services (AWS, Azure)
- Energy industry concepts
- General programming help

Be concise but thorough. Ask clarifying questions when needed."""),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    chain = prompt | llm
    history = InMemoryChatMessageHistory()

    chat = RunnableWithMessageHistory(
        chain,
        lambda _: history,
        input_messages_key="input",
        history_messages_key="history",
    )

    config = {"configurable": {"session_id": "interactive"}}

    print("\n" + "=" * 60)
    print("  Interactive Chat Assistant")
    print("  Type 'quit' to exit, 'clear' to reset history")
    print("=" * 60 + "\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "quit":
            print("Goodbye!")
            break
        elif user_input.lower() == "clear":
            history.clear()
            print("(History cleared)\n")
            continue
        elif not user_input:
            continue

        response = chat.invoke({"input": user_input}, config=config)
        print(f"Assistant: {response.content}\n")


# ============================================================
# Example 3: Chat with structured output
# ============================================================

def chat_with_structured_output():
    """
    Get structured (JSON) responses from the LLM.
    Useful for extracting data from conversations.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from pydantic import BaseModel, Field

    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # Define the output structure
    class TaskExtraction(BaseModel):
        """Extract task details from a user message."""
        task_description: str = Field(description="What needs to be done")
        priority: str = Field(description="high, medium, or low")
        category: str = Field(description="Category: data, code, infrastructure, or other")
        estimated_hours: float = Field(description="Rough estimate in hours")

    # Bind the structure to the LLM
    structured_llm = llm.with_structured_output(TaskExtraction)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract task details from the user's message."),
        ("human", "{input}"),
    ])

    chain = prompt | structured_llm

    # Test it
    print("\n=== Structured Output Example ===")

    tasks = [
        "I need to build a new Snowflake pipeline for the billing data by Friday",
        "Can someone fix the typo in the README? It's not urgent.",
        "We need to migrate the Lambda functions to use Python 3.12 runtime ASAP",
    ]

    for task in tasks:
        result = chain.invoke({"input": task})
        print(f"\nInput: {task}")
        print(f"  Task: {result.task_description}")
        print(f"  Priority: {result.priority}")
        print(f"  Category: {result.category}")
        print(f"  Est. Hours: {result.estimated_hours}")


# ============================================================
# Run examples
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  LANGCHAIN CHAT ASSISTANT")
    print("=" * 60)

    # Run the memory demo
    chat_with_memory()

    # Run structured output demo
    chat_with_structured_output()

    # Uncomment for interactive mode:
    # interactive_chat()
