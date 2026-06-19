"""Retrieval-augmented generation using OpenAI GPT."""

from typing import List, Generator
from openai import OpenAI

from vector_store import VectorStore

CHAT_MODEL = "gpt-4o"
SYSTEM_PROMPT = """\
You are a helpful assistant that answers questions based strictly on the provided context.
If the context does not contain enough information to answer the question, say so clearly.
Always cite the source document and page when referencing specific information.
"""


class RAGEngine:
    def __init__(self, openai_api_key: str, vector_store: VectorStore):
        self._llm = OpenAI(api_key=openai_api_key)
        self._store = vector_store

    def answer(
        self,
        question: str,
        history: List[dict],
        stream: bool = True,
    ) -> Generator[str, None, None]:
        """
        Yield response tokens. history is list of {"role": str, "content": str}.
        """
        chunks = self._store.query(question)
        context = self._build_context(chunks)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"## Retrieved Context\n\n{context}",
            },
            *history,
            {"role": "user", "content": question},
        ]

        response = self._llm.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            stream=stream,
            temperature=0.2,
        )

        if stream:
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        else:
            yield response.choices[0].message.content

    def _build_context(self, chunks: List[dict]) -> str:
        if not chunks:
            return "No relevant documents found."
        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"[{i}] Source: {chunk['source']}, Page: {chunk['page']}\n{chunk['text']}"
            )
        return "\n\n---\n\n".join(parts)
