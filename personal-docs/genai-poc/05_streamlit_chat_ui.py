"""
05 - Streamlit Chat UI
======================
A web-based chat interface for your LangChain assistant.
Run with: streamlit run 05_streamlit_chat_ui.py
"""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage


# --- Page config ---
st.set_page_config(
    page_title="GenAI Assistant",
    page_icon="⚡",
    layout="centered",
)

st.title("⚡ GenAI Assistant")
st.caption("Powered by LangChain + OpenAI | Learning POC")


# --- Initialize session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "llm" not in st.session_state:
    st.session_state.llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        streaming=True,
    )


# --- Sidebar settings ---
with st.sidebar:
    st.header("⚙️ Settings")

    system_prompt = st.text_area(
        "System Prompt",
        value="""You are a helpful assistant for enterprise employees.
You help with:
- Data engineering (Snowflake, Python, ETL, AWS)
- Energy industry concepts
- General programming questions
- GenAI/LLM concepts

Be concise, friendly, and technical when needed.""",
        height=200,
    )

    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    max_tokens = st.slider("Max Tokens", 100, 4000, 1000, 100)

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("### Quick Prompts")
    quick_prompts = [
        "Explain RAG in simple terms",
        "How do LangGraph agents work?",
        "Snowflake optimization tips",
        "Compare LangChain vs LangGraph",
    ]
    for qp in quick_prompts:
        if st.button(qp, key=f"qp_{qp}"):
            st.session_state.pending_prompt = qp
            st.rerun()


# --- Display chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# --- Handle input ---
# Check for pending quick prompt
user_input = None
if "pending_prompt" in st.session_state:
    user_input = st.session_state.pending_prompt
    del st.session_state.pending_prompt
else:
    user_input = st.chat_input("Ask me anything...")

if user_input:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build the prompt with history
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    # Convert session messages to LangChain format
    history = []
    for msg in st.session_state.messages[:-1]:  # exclude current
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        else:
            history.append(AIMessage(content=msg["content"]))

    # Create chain with current settings
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=True,
    )
    chain = prompt | llm

    # Stream the response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        for chunk in chain.stream({"input": user_input, "history": history}):
            full_response += chunk.content
            response_placeholder.markdown(full_response + "▌")

        response_placeholder.markdown(full_response)

    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": full_response})
