"""Streamlit UI for the RAG Conversational Engine."""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from document_processor import extract_text, SUPPORTED_EXTENSIONS
from vector_store import VectorStore
from rag_engine import RAGEngine

load_dotenv()

st.set_page_config(
    page_title="RAG Conversational Engine",
    page_icon="🔍",
    layout="wide",
)


# ── helpers ──────────────────────────────────────────────────────────────────

def get_api_key() -> str:
    return st.session_state.get("api_key") or os.getenv("OPENAI_API_KEY", "")


@st.cache_resource
def get_vector_store(api_key: str) -> VectorStore:
    return VectorStore(persist_dir="./chroma_db", openai_api_key=api_key)


def get_rag_engine(api_key: str) -> RAGEngine:
    store = get_vector_store(api_key)
    return RAGEngine(openai_api_key=api_key, vector_store=store)


# ── session state defaults ────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("OPENAI_API_KEY", "")


# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Settings")

    api_key_input = st.text_input(
        "OpenAI API Key",
        value=st.session_state.api_key,
        type="password",
        placeholder="sk-...",
    )
    if api_key_input:
        st.session_state.api_key = api_key_input

    st.divider()
    st.subheader("📁 Upload Documents")

    ext_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    uploaded_files = st.file_uploader(
        f"Supported: {ext_list}",
        accept_multiple_files=True,
        type=[e.lstrip(".") for e in SUPPORTED_EXTENSIONS],
    )

    if uploaded_files and get_api_key():
        store = get_vector_store(get_api_key())
        for f in uploaded_files:
            with st.spinner(f"Processing {f.name}…"):
                try:
                    chunks = extract_text(f.name, f.read())
                    added = store.add_documents(chunks)
                    if added:
                        st.success(f"✅ {f.name}: {added} chunks added")
                    else:
                        st.info(f"ℹ️ {f.name}: already indexed")
                except Exception as e:
                    st.error(f"❌ {f.name}: {e}")
    elif uploaded_files and not get_api_key():
        st.warning("Enter your OpenAI API key first.")

    st.divider()
    st.subheader("🗂️ Indexed Documents")

    if get_api_key():
        store = get_vector_store(get_api_key())
        sources = store.list_sources()
        if sources:
            for src in sources:
                col1, col2 = st.columns([4, 1])
                col1.text(src)
                if col2.button("🗑️", key=f"del_{src}", help=f"Remove {src}"):
                    removed = store.delete_source(src)
                    st.success(f"Removed {removed} chunks from {src}")
                    st.rerun()
            st.caption(f"Total chunks: {store.count()}")
        else:
            st.caption("No documents indexed yet.")

    st.divider()
    if st.button("🧹 Clear conversation"):
        st.session_state.messages = []
        st.rerun()


# ── main chat area ────────────────────────────────────────────────────────────

st.title("🔍 RAG Conversational Engine")
st.caption("Powered by OpenAI GPT-4o + text-embedding-3-small · Vector store: ChromaDB")

if not get_api_key():
    st.info("👈 Enter your OpenAI API key in the sidebar to get started.")
    st.stop()

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask a question about your documents…"):
    store = get_vector_store(get_api_key())

    if store.count() == 0:
        st.warning("Upload at least one document before asking questions.")
        st.stop()

    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream assistant response
    engine = get_rag_engine(get_api_key())
    history = st.session_state.messages[:-1]  # exclude current user turn

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        for token in engine.answer(prompt, history):
            full_response += token
            response_placeholder.markdown(full_response + "▌")
        response_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
