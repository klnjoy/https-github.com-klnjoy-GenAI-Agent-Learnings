---
icon: material/laptop
---

# Local Environment Setup

Get a clean Python environment ready for GenAI work.

## 1. Python & virtual environment

```bash
# check you have 3.10+
python --version

# create + activate a venv (Windows PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install core libraries

```bash
pip install langchain langchain-community langgraph openai boto3 \
    chromadb faiss-cpu python-dotenv
```

!!! note "Behind a corporate proxy?"
    If pip fails with an SSL certificate error, add trusted hosts:
    ```bash
    pip install <pkg> --trusted-host pypi.org --trusted-host files.pythonhosted.org
    ```

## 3. Manage secrets with a `.env` file

Never hard-code keys. Create `.env`:

```bash
# .env  (never commit this)
OPENAI_API_KEY=sk-...
AWS_REGION=us-west-2
```

Load it in code:

```python
from dotenv import load_dotenv
load_dotenv()
```

Add `.env` to `.gitignore`.

## 4. Suggested project layout

```text
my-genai-app/
├── .venv/
├── .env                 # secrets (gitignored)
├── requirements.txt
├── data/                # source docs for RAG
├── src/
│   ├── llm.py           # model client
│   ├── rag.py           # retrieval
│   └── agent.py         # agent loop
└── app.py               # entrypoint / API
```

## Next

→ [LLM Access](../llm-access/index.md) — make your first model call.
