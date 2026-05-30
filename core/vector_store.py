import os
import json
import logging
from typing import Optional

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from core.config import Config
from core.models import Paper

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self) -> None:
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.index_path = os.path.join(Config().DATA_DIR, "faiss_index")
        self._store: Optional[FAISS] = None
        self._papers: dict[str, Paper] = {}

    def index_papers(self, papers: list[Paper]) -> None:
        if not papers:
            return
        texts = []
        metadatas = []
        for p in papers:
            summary_text = p.summary.one_liner if p.summary else p.abstract
            texts.append(summary_text)
            metadatas.append({"paper_id": p.id})
            self._papers[p.id] = p
        self._store = FAISS.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
        )
        self.save()

    def search(self, query: str, k: int = 10) -> list[Paper]:
        if self._store is None:
            loaded = self.load()
            if not loaded or self._store is None:
                return []
        docs: list[Document] = self._store.similarity_search(query, k=k)
        results = []
        for doc in docs:
            paper_id = doc.metadata.get("paper_id")
            if paper_id and paper_id in self._papers:
                results.append(self._papers[paper_id])
        return results

    def save(self) -> None:
        if self._store is None:
            return
        os.makedirs(self.index_path, exist_ok=True)
        self._store.save_local(self.index_path)
        papers_path = os.path.join(self.index_path, "papers.json")
        papers_data = {
            pid: p.model_dump(mode="json") for pid, p in self._papers.items()
        }
        with open(papers_path, "w") as f:
            json.dump(papers_data, f, indent=2)

    def load(self) -> bool:
        if not os.path.exists(os.path.join(self.index_path, "index.faiss")):
            logger.info("No FAISS index found at %s", self.index_path)
            return False
        try:
            self._store = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            papers_path = os.path.join(self.index_path, "papers.json")
            if os.path.exists(papers_path):
                with open(papers_path) as f:
                    papers_data = json.load(f)
                self._papers = {
                    pid: Paper(**pdata) for pid, pdata in papers_data.items()
                }
            return True
        except Exception as e:
            logger.error("Failed to load FAISS index: %s", e)
            return False

    def is_loaded(self) -> bool:
        return self._store is not None
