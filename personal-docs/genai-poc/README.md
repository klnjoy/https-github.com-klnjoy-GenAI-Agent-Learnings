# GenAI POC - LangChain & LangGraph Learning

Hands-on POC examples for learning LLM calls, LangChain, and LangGraph.

## Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
copy .env.example .env
```

## Phase 1 - Foundations

| File | Description |
|------|-------------|
| `01_basic_llm_call.py` | Direct LLM calls with OpenAI and Azure OpenAI |
| `02_langchain_chat.py` | Chat assistant with conversation memory |
| `03_langchain_rag.py` | RAG (Retrieval Augmented Generation) basics |
| `04_langgraph_agent.py` | Stateful agent with tools using LangGraph |

## Phase 2 - Advanced Patterns

| File | Description |
|------|-------------|
| `05_streamlit_chat_ui.py` | Web-based chat UI with streaming |
| `06_multi_agent_system.py` | Supervisor + workers, debate/critique patterns |
| `07_tool_calling_agent.py` | Agent that queries Snowflake and calls APIs |
| `08_document_qa.py` | Upload docs and ask questions (RAG app) |

## Running

```bash
# Phase 1
python 01_basic_llm_call.py
python 02_langchain_chat.py
python 03_langchain_rag.py
python 04_langgraph_agent.py

# Phase 2
streamlit run 05_streamlit_chat_ui.py
python 06_multi_agent_system.py
python 07_tool_calling_agent.py
python 08_document_qa.py
```
