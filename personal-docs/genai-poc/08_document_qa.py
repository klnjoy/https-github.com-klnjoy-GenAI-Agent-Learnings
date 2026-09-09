"""
08 - Document Q&A App
=====================
Upload documents (PDF, TXT, MD) and ask questions about them.
Uses RAG with a local vector store for document understanding.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ============================================================
# Document Loading Utilities
# ============================================================

def load_text_file(file_path: str) -> str:
    """Load a plain text or markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_pdf_file(file_path: str) -> str:
    """Load a PDF file (requires pypdf)."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except ImportError:
        return "ERROR: Install pypdf to load PDFs: pip install pypdf"


def load_document(file_path: str) -> str:
    """Load any supported document format."""
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return load_pdf_file(file_path)
    elif path.suffix.lower() in [".txt", ".md", ".py", ".sql", ".yaml", ".yml", ".json"]:
        return load_text_file(file_path)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


# ============================================================
# Document Q&A Engine
# ============================================================

class DocumentQA:
    """
    A document question-answering engine.
    
    Workflow:
    1. Load documents
    2. Split into chunks
    3. Create embeddings
    4. Store in vector DB
    5. Query: retrieve relevant chunks → LLM generates answer
    """

    def __init__(self, model: str = "gpt-4o", chunk_size: int = 500, chunk_overlap: int = 100):
        self.llm = ChatOpenAI(model=model, temperature=0.3)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self.vectorstore = None
        self.retriever = None
        self.documents_loaded = []

    def add_document(self, file_path: str):
        """Load and index a document."""
        print(f"📄 Loading: {file_path}")
        content = load_document(file_path)
        filename = Path(file_path).name

        # Create document chunks with metadata
        from langchain_core.documents import Document
        chunks = self.text_splitter.create_documents(
            texts=[content],
            metadatas=[{"source": filename}],
        )
        print(f"   Split into {len(chunks)} chunks")

        # Add to vector store
        if self.vectorstore is None:
            self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
        else:
            self.vectorstore.add_documents(chunks)

        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 4})
        self.documents_loaded.append(filename)
        print(f"   ✅ Indexed successfully")

    def add_text(self, text: str, source_name: str = "direct_input"):
        """Index raw text content."""
        from langchain_core.documents import Document
        chunks = self.text_splitter.create_documents(
            texts=[text],
            metadatas=[{"source": source_name}],
        )

        if self.vectorstore is None:
            self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
        else:
            self.vectorstore.add_documents(chunks)

        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 4})
        self.documents_loaded.append(source_name)

    def ask(self, question: str) -> dict:
        """Ask a question about the loaded documents."""
        if self.retriever is None:
            return {"answer": "No documents loaded yet. Use add_document() first.", "sources": []}

        # Retrieve relevant chunks
        relevant_docs = self.retriever.invoke(question)

        # Format context
        context = "\n\n---\n\n".join(
            f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
            for doc in relevant_docs
        )

        # Generate answer
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Answer the question based on the provided document context.
If the context doesn't contain enough information, say so clearly.
Always cite which source document(s) you used.
Be precise and concise.

Context:
{context}"""),
            ("human", "{question}"),
        ])

        chain = prompt | self.llm | StrOutputParser()
        answer = chain.invoke({"context": context, "question": question})

        # Collect unique sources
        sources = list(set(doc.metadata.get("source", "unknown") for doc in relevant_docs))

        return {"answer": answer, "sources": sources}

    def ask_with_followup(self, question: str) -> str:
        """Ask and suggest follow-up questions."""
        result = self.ask(question)

        # Generate follow-up suggestions
        followup_prompt = ChatPromptTemplate.from_messages([
            ("system", "Based on this Q&A, suggest 3 natural follow-up questions the user might ask."),
            ("human", "Question: {question}\nAnswer: {answer}\n\nSuggest 3 follow-up questions:"),
        ])

        chain = followup_prompt | self.llm | StrOutputParser()
        followups = chain.invoke({"question": question, "answer": result["answer"]})

        output = f"📝 Answer: {result['answer']}\n"
        output += f"📚 Sources: {', '.join(result['sources'])}\n"
        output += f"\n💡 Follow-up questions:\n{followups}"
        return output


# ============================================================
# Demo with sample documents
# ============================================================

def demo_document_qa():
    """Demo with sample content (no file dependencies)."""
    print("=== Document Q&A Engine ===\n")

    qa = DocumentQA()

    # Add sample documents as text
    qa.add_text("""
    Data Architecture Overview
    ==============================
    
    Our data platform is built on three layers:
    
    1. Raw Layer (S3): Landing zone for all source data. Files arrive via API pulls,
       SFTP transfers, and streaming. Retention: 90 days.
    
    2. Staging Layer (Snowflake STAGING database): Cleaned and typed data.
       ETL Lambda functions transform raw files and load here. Schema-on-read
       with basic validation.
    
    3. Analytics Layer (Snowflake ANALYTICS database): Business-ready data models
       built with dbt. Star schema design. Used by Tableau dashboards and 
       data science notebooks.
    
    Key Technologies:
    - Storage: AWS S3, Snowflake
    - Compute: AWS Lambda, Snowflake Warehouses
    - Orchestration: AWS EventBridge, Step Functions
    - Transformation: Python, dbt
    - BI: Tableau, Jupyter
    """, "data-architecture.md")

    qa.add_text("""
    ETL Pipeline Standards
    ======================
    
    All ETL pipelines must follow these standards:
    
    Naming Convention:
    - Lambda functions: {team}_{source}_{process_type}
    - Example: intrcon_pwrclrk_etl_cdc
    
    Error Handling:
    - All errors must be caught and logged to CloudWatch
    - Critical failures trigger SNS alerts to #data-alerts Slack channel
    - Failed records written to error table for reprocessing
    
    Data Quality:
    - Null checks on required fields
    - Duplicate detection on primary keys
    - Row count validation (+/- 10% of rolling average)
    - Freshness monitoring (alert if >24h stale)
    
    Performance:
    - Lambda timeout: max 15 minutes
    - Batch size: 10,000 records per invoke
    - Use Snowflake COPY INTO for bulk loads
    - Avoid single-row inserts
    """, "etl-standards.md")

    qa.add_text("""
    Snowflake Access & Security
    ===========================
    
    Roles:
    - SYSADMIN: Full access (DBA team only)
    - DATA_ENGINEER: Create/modify tables in STAGING and ANALYTICS
    - ANALYST: Read-only access to ANALYTICS
    - SERVICE_ACCOUNT: Used by ETL pipelines, scoped to specific schemas
    
    Warehouses:
    - ETL_WH (X-Large): For ETL workloads, auto-suspend 60s
    - ANALYTICS_WH (Large): For dashboards and ad-hoc queries
    - DEV_WH (Small): For development and testing
    - ML_WH (Medium): For data science workloads
    
    Best Practices:
    - Never use ACCOUNTADMIN for routine work
    - All service accounts use key-pair authentication
    - Data masking policies on PII columns
    - Network policies restrict access to the corporate VPN
    """, "snowflake-security.md")

    # Ask questions
    print("\n" + "=" * 50)
    print("Asking questions about the documents...\n")

    questions = [
        "What are the three data layers and what technology does each use?",
        "What's the naming convention for Lambda functions?",
        "What Snowflake warehouse should I use for development?",
        "What happens when an ETL pipeline fails?",
        "How is PII data protected in Snowflake?",
    ]

    for q in questions:
        result = qa.ask(q)
        print(f"❓ {q}")
        print(f"📝 {result['answer']}")
        print(f"📚 Sources: {', '.join(result['sources'])}")
        print()

    return qa


# ============================================================
# Streamlit version (run with: streamlit run 08_document_qa.py)
# ============================================================

def streamlit_document_qa():
    """
    Streamlit UI for document Q&A.
    Uncomment the imports and run with: streamlit run 08_document_qa.py
    """
    import streamlit as st

    st.set_page_config(page_title="Document Q&A", page_icon="📚")
    st.title("📚 Document Q&A")

    # Initialize
    if "qa_engine" not in st.session_state:
        st.session_state.qa_engine = DocumentQA()

    # File upload
    with st.sidebar:
        st.header("📄 Upload Documents")
        uploaded_files = st.file_uploader(
            "Upload files",
            type=["txt", "md", "pdf", "py", "sql"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            for file in uploaded_files:
                if file.name not in st.session_state.qa_engine.documents_loaded:
                    content = file.read().decode("utf-8")
                    st.session_state.qa_engine.add_text(content, file.name)
                    st.success(f"Loaded: {file.name}")

        st.divider()
        st.write(f"**Documents loaded:** {len(st.session_state.qa_engine.documents_loaded)}")
        for doc in st.session_state.qa_engine.documents_loaded:
            st.write(f"- {doc}")

    # Q&A interface
    question = st.text_input("Ask a question about your documents:")
    if question:
        with st.spinner("Searching documents..."):
            result = st.session_state.qa_engine.ask(question)

        st.markdown(f"**Answer:** {result['answer']}")
        st.caption(f"Sources: {', '.join(result['sources'])}")


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  DOCUMENT Q&A")
    print("=" * 60)

    demo_document_qa()

    # To run the Streamlit version:
    # streamlit run 08_document_qa.py
    # (It will detect Streamlit and use streamlit_document_qa())
