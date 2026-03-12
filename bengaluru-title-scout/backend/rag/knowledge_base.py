import os
import logging
from pathlib import Path
from typing import List, Dict, Any

log = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    log.warning("chromadb not installed.")

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False

from rag.law_chunks import KARNATAKA_LAW_CHUNKS


class KnowledgeBase:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.persist_dir = persist_dir
        self.client = None
        self.collection = None
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None and ST_AVAILABLE:
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedder

    def initialize(self):
        if not CHROMA_AVAILABLE:
            log.warning("ChromaDB not available — RAG disabled.")
            return

        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

        existing = [c.name for c in self.client.list_collections()]
        if "karnataka_laws" not in existing:
            log.info("Knowledge base not found — building from Karnataka law chunks...")
            self._build()
        else:
            self.collection = self.client.get_collection("karnataka_laws")
            log.info(f"Knowledge base loaded — {self.collection.count()} chunks.")

    def rebuild(self):
        if not CHROMA_AVAILABLE:
            return
        try:
            self.client.delete_collection("karnataka_laws")
        except Exception:
            pass
        self._build()

    def _build(self):
        self.collection = self.client.get_or_create_collection(
            name="karnataka_laws",
            metadata={"hnsw:space": "cosine"},
        )
        chunks = KARNATAKA_LAW_CHUNKS
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            ids        = [c["id"]       for c in batch]
            documents  = [c["text"]     for c in batch]
            metadatas  = [c["metadata"] for c in batch]
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)

        log.info(f"Knowledge base built — {len(chunks)} chunks indexed.")

    def query_relevant_laws(self, document_text: str, parsed: dict, n_results: int = 12) -> List[Dict]:
        if not CHROMA_AVAILABLE or self.collection is None:
            return self._keyword_fallback(document_text, parsed)

        queries = self._build_queries(document_text, parsed)
        seen_ids = set()
        results = []

        for query in queries:
            try:
                res = self.collection.query(
                    query_texts=[query],
                    n_results=min(n_results, self.collection.count()),
                    include=["documents", "metadatas", "distances"],
                )
                for doc, meta, dist in zip(
                    res["documents"][0],
                    res["metadatas"][0],
                    res["distances"][0],
                ):
                    chunk_id = meta.get("id", doc[:40])
                    if chunk_id not in seen_ids and dist < 0.7:
                        seen_ids.add(chunk_id)
                        results.append({
                            "text":       doc,
                            "act":        meta.get("act", ""),
                            "section":    meta.get("section", ""),
                            "relevance":  round(1 - dist, 3),
                            "tags":       meta.get("tags", "").split(","),
                        })
            except Exception as e:
                log.error(f"KB query error: {e}")

        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:15]

    def _build_queries(self, text: str, parsed: dict) -> List[str]:
        queries = ["Karnataka land title due diligence requirements"]
        doc_type = parsed.get("doc_type", "")

        if "grant" in text.lower() or "sc" in text.lower() or "st" in text.lower():
            queries.append("PTCL Act SC ST grant land transfer restrictions Karnataka")
        if "79" in text or "land reform" in text.lower():
            queries.append("Karnataka Land Reforms Act section 79A 79B ceiling agricultural land")
        if "rtc" in doc_type or "pahani" in text.lower() or "mutation" in text.lower():
            queries.append("RTC record of rights tenancy crops Karnataka Land Revenue Act")
        if "ec" in doc_type or "encumbrance" in text.lower():
            queries.append("encumbrance certificate mortgage lien charge Karnataka")
        if "sale deed" in text.lower() or "conveyance" in text.lower():
            queries.append("sale deed registration stamp duty Karnataka Registration Act")
        if "khatha" in text.lower():
            queries.append("khatha certificate BBMP property tax assessment Bengaluru")
        if "conversion" in text.lower() or "dc order" in text.lower():
            queries.append("DC conversion agricultural to non-agricultural Karnataka section 95")
        if "rera" in text.lower() or "apartment" in text.lower():
            queries.append("RERA Karnataka real estate developer registration apartment")
        if "survey" in text.lower():
            queries.append("survey number village map sketch land records Karnataka")

        return queries

    def _keyword_fallback(self, text: str, parsed: dict) -> List[Dict]:
        relevant = []
        text_lower = text.lower()
        for chunk in KARNATAKA_LAW_CHUNKS:
            tags = chunk["metadata"].get("tags", "").lower()
            score = 0
            for kw in ["grant land", "sc/st", "ptcl", "79a", "79b", "encumbrance", "mutation", "khatha", "rtc", "conversion"]:
                if kw in text_lower and kw.replace(" ", "") in tags.replace(" ", ""):
                    score += 1
            if score > 0:
                relevant.append({"text": chunk["text"], "act": chunk["metadata"].get("act", ""), "section": chunk["metadata"].get("section", ""), "relevance": score / 10, "tags": []})

        relevant.sort(key=lambda x: x["relevance"], reverse=True)
        return relevant[:12]
