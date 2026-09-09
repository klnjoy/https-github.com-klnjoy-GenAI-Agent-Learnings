"""
03 - RAG (Retrieval Augmented Generation)
==========================================
Ground LLM responses in your own documents/data.
This is how you build assistants that "know" about your internal docs.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Example 1: Simple RAG with in-memory vector store
# ============================================================

def simple_rag():
    """
    Basic RAG pipeline:
    1. Load documents
    2. Split into chunks
    3. Create embeddings and store in vector DB
    4. Query: retrieve relevant chunks + send to LLM
    """
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # --- Step 1: Prepare sample documents ---
    # In production, these would come from files, databases, APIs, etc.
    documents = [
        """An electric utility provides power to residential and commercial customers
        across a service territory. Utilities generate electricity from diverse sources
        including wind, solar, natural gas, and hydroelectric power.""",

        """A typical data engineering team uses Snowflake as their cloud data warehouse.
        They build ETL pipelines using AWS Lambda, Python, and various orchestration tools.
        Data flows from source systems through S3 into Snowflake for analytics.""",

        """Renewable Energy Certificates (RECs) represent the environmental attributes of
        one megawatt-hour of renewable electricity generation. Utilities use RECs
        to demonstrate compliance with Renewable Portfolio Standards (RPS).""",

        """AWS Lambda is a serverless compute service that runs code in response to events.
        Teams use Lambda functions for ETL processing, triggered by S3 events or scheduled
        via EventBridge. Functions are written in Python and deployed via CloudFormation.""",

        """LangChain is a framework for building applications with large language models.
        It provides tools for prompt management, memory, chains, and agents.
        LangGraph extends LangChain with graph-based workflow orchestration.""",

        """Snowflake best practices include: use appropriate warehouse sizes, implement
        clustering keys for large tables, use materialized views for complex queries,
        and leverage Snowpipe for real-time data ingestion.""",
    ]

    # --- Step 2: Split documents into chunks ---
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
    )
    chunks = text_splitter.create_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks")

    # --- Step 3: Create embeddings and vector store ---
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # Create a retriever (returns top 3 most relevant chunks)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # --- Step 4: Build the RAG chain ---
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """Answer the question based on the provided context. 
If the context doesn't contain enough information, say so.
Be concise and specific.

Context:
{context}"""),
        ("human", "{question}"),
    ])

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # The RAG chain: retrieve docs -> format -> prompt -> LLM -> parse
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # --- Step 5: Ask questions ---
    print("\n=== RAG Q&A ===\n")

    questions = [
        "What data warehouse does the org use?",
        "How are Lambda functions deployed?",
        "What is a REC?",
        "What are Snowflake best practices?",
    ]

    for q in questions:
        answer = rag_chain.invoke(q)
        print(f"Q: {q}")
        print(f"A: {answer}\n")

    return rag_chain, vectorstore


# ============================================================
# Example 2: RAG with source citations
# ============================================================

def rag_with_citations():
    """
    Enhanced RAG that shows which documents were used to answer.
    Important for trust and verification.
    """
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from pydantic import BaseModel, Field

    # Sample docs with metadata (source tracking)
    from langchain_core.documents import Document

    docs_with_sources = [
        Document(
            page_content="The org uses Snowflake for data warehousing and analytics.",
            metadata={"source": "data-architecture.md", "section": "Infrastructure"},
        ),
        Document(
            page_content="ETL pipelines are built with Python Lambda functions on AWS.",
            metadata={"source": "etl-guide.md", "section": "Pipeline Design"},
        ),
        Document(
            page_content="LangGraph uses a graph-based state machine for agent workflows.",
            metadata={"source": "genai-notes.md", "section": "Frameworks"},
        ),
    ]

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(docs_with_sources, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    # Structured output for citations
    class AnswerWithSources(BaseModel):
        answer: str = Field(description="The answer to the question")
        sources: list[str] = Field(description="List of source documents used")
        confidence: str = Field(description="high, medium, or low")

    llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(AnswerWithSources)

    print("\n=== RAG with Citations ===\n")

    # Retrieve and answer
    question = "What tools does the org use for data pipelines?"
    docs = retriever.invoke(question)

    context = "\n".join(
        f"[Source: {d.metadata['source']}] {d.page_content}" for d in docs
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer based on the context. Cite your sources.\n\nContext:\n{context}"),
        ("human", "{question}"),
    ])

    chain = prompt | llm
    result = chain.invoke({"context": context, "question": question})

    print(f"Q: {question}")
    print(f"A: {result.answer}")
    print(f"Sources: {result.sources}")
    print(f"Confidence: {result.confidence}")


# ============================================================
# Run examples
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  RAG - Retrieval Augmented Generation")
    print("=" * 60)

    simple_rag()
    rag_with_citations()
