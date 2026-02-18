"""
memory.py — 장기 기억 모듈 (ChromaDB + Ollama 임베딩)

역할:
- 대화 내용을 벡터 DB에 저장 (save)
- 유사도 검색으로 관련 기억 회수 (recall)
- RAG 파이프라인의 핵심 컴포넌트
"""

import uuid
from pathlib import Path
import chromadb
import ollama

# 프로젝트 루트 기준 기본 경로 계산
_DEFAULT_CHROMA_DIR = str(Path(__file__).resolve().parent.parent / "Agent_Workspace" / ".chroma")


class AgentMemory:
    def __init__(self, persist_dir: str = _DEFAULT_CHROMA_DIR):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="agent_memory",
            metadata={"hnsw:space": "cosine"}
        )

    def _embed(self, text: str) -> list[float]:
        """Ollama 임베딩 모델로 텍스트를 벡터로 변환"""
        response = ollama.embeddings(model="nomic-embed-text", prompt=text)
        return response["embedding"]

    def save(self, text: str, metadata: dict = {}):
        """대화 또는 설정을 임베딩하여 저장"""
        self.collection.add(
            ids=[str(uuid.uuid4())],
            embeddings=[self._embed(text)],
            documents=[text],
            metadatas=[metadata] if metadata else [{}]
        )
        print(f"[Memory] Saved: {text[:80]}...")

    def recall(self, query: str, n_results: int = 5) -> list[str]:
        """관련 기억 검색 (RAG)"""
        # 컬렉션이 비어있으면 빈 리스트 반환
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_embeddings=[self._embed(query)],
            n_results=min(n_results, self.collection.count())
        )
        return results["documents"][0] if results["documents"] else []
