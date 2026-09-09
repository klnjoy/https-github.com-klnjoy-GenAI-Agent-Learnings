"""
01 - Basic LLM Calls
====================
Learn how to make direct calls to OpenAI and Azure OpenAI models.
This is the foundation for everything else.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Example 1: Basic OpenAI call using the openai library directly
# ============================================================

def basic_openai_call():
    """Direct call to OpenAI API - the simplest way to talk to an LLM."""
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is retrieval-augmented generation?"},
        ],
        temperature=0.7,
        max_tokens=200,
    )

    print("=== Basic OpenAI Call ===")
    print(response.choices[0].message.content)
    print(f"\nTokens used: {response.usage.total_tokens}")
    return response


# ============================================================
# Example 2: Azure OpenAI call
# ============================================================

def azure_openai_call():
    """Call Azure OpenAI - same interface, enterprise-grade hosting."""
    from openai import AzureOpenAI

    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        messages=[
            {"role": "system", "content": "You are a helpful energy industry assistant."},
            {"role": "user", "content": "Explain renewable energy certificates (RECs) in 2 sentences."},
        ],
        temperature=0.3,
    )

    print("\n=== Azure OpenAI Call ===")
    print(response.choices[0].message.content)
    return response


# ============================================================
# Example 3: Using LangChain's ChatOpenAI wrapper
# ============================================================

def langchain_llm_call():
    """
    LangChain wraps the OpenAI client with extra features:
    - Automatic retries
    - Streaming support
    - Prompt templates
    - Output parsing
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    # Initialize the LLM
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        max_tokens=200,
    )

    # Simple invocation
    messages = [
        SystemMessage(content="You are a concise technical assistant."),
        HumanMessage(content="What is LangChain and why would I use it?"),
    ]

    response = llm.invoke(messages)

    print("\n=== LangChain LLM Call ===")
    print(response.content)
    print(f"\nMetadata: {response.response_metadata}")
    return response


# ============================================================
# Example 4: Prompt Templates - reusable prompt patterns
# ============================================================

def prompt_template_example():
    """Prompt templates let you parameterize prompts for reuse."""
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    llm = ChatOpenAI(model="gpt-4o", temperature=0.5)

    # Create a reusable template
    template = ChatPromptTemplate.from_messages([
        ("system", "You are an expert in {domain}. Be concise."),
        ("human", "{question}"),
    ])

    # Chain the template with the LLM (this is a "chain")
    chain = template | llm

    # Use it with different inputs
    response = chain.invoke({
        "domain": "electric utilities",
        "question": "What is demand response?",
    })

    print("\n=== Prompt Template Example ===")
    print(response.content)

    # Same template, different inputs
    response2 = chain.invoke({
        "domain": "data engineering",
        "question": "What is a slowly changing dimension?",
    })

    print("\n=== Same Template, Different Domain ===")
    print(response2.content)
    return response


# ============================================================
# Example 5: Streaming responses
# ============================================================

def streaming_example():
    """Stream tokens as they're generated - better UX for chat apps."""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    llm = ChatOpenAI(model="gpt-4o", temperature=0.7, streaming=True)

    print("\n=== Streaming Example ===")
    for chunk in llm.stream([HumanMessage(content="Write a haiku about electricity.")]):
        print(chunk.content, end="", flush=True)
    print()  # newline at end


# ============================================================
# Run all examples
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  BASIC LLM CALLS - Learning the Fundamentals")
    print("=" * 60)

    # Uncomment the examples you want to run:

    # Requires OPENAI_API_KEY
    # basic_openai_call()

    # Requires Azure OpenAI credentials
    # azure_openai_call()

    # Requires OPENAI_API_KEY (uses LangChain wrapper)
    langchain_llm_call()
    prompt_template_example()
    streaming_example()
