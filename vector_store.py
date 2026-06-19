"""ChromaDB vector store with OpenAI text-embedding-3-small."""

from typing import List, Optional
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI


COLLECTION_NAME = "rag_documents"
EMBED_MODEL = "text-embedding-3-small"
TOP_K = 5


class VectorStore:
    def __init__(self, persist_dir: str = "./chroma_db", openai_api_key: str = ""):
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name=EMBED_MODEL,
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, chunks: List[dict]) -> int:
        """
        Add text chunks to the store.
        Each chunk: {"text": str, "source": str, "page": int|str}
        Returns number of chunks added.
        """
        if not chunks:
            return 0

        # Avoid duplicates: derive IDs from source + page
        existing_ids = set(self._collection.get()["ids"])
        new_docs, new_ids, new_metas = [], [], []

        for i, chunk in enumerate(chunks):
            doc_id = f"{chunk['source']}::p{chunk['page']}::{i}"
            if doc_id not in existing_ids:
                new_docs.append(chunk["text"])
                new_ids.append(doc_id)
                new_metas.append({"source": chunk["source"], "page": str(chunk["page"])})

        if new_docs:
            self._collection.add(documents=new_docs, ids=new_ids, metadatas=new_metas)

        return len(new_docs)

    def query(self, question: str, top_k: int = TOP_K) -> List[dict]:
        """Return top-k relevant chunks for a question."""
        results = self._collection.query(
            query_texts=[question],
            n_results=min(top_k, self._collection.count() or 1),
        )
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        return [
            {"text": doc, "source": meta["source"], "page": meta["page"]}
            for doc, meta in zip(docs, metas)
        ]

    def list_sources(self) -> List[str]:
        """Return distinct source file names in the store."""
        if self._collection.count() == 0:
            return []
        all_metas = self._collection.get()["metadatas"]
        return sorted({m["source"] for m in all_metas})

    def delete_source(self, source: str) -> int:
        """Remove all chunks belonging to a source file."""
        results = self._collection.get(where={"source": source})
        ids = results["ids"]
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def count(self) -> int:
        return self._collection.count()
