"""
RAG (Retrieval-Augmented Generation) layer using ChromaDB.

Ingests newsletter content from memory_bank/ directory and provides
semantic search for strategic content patterns.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
from chromadb.errors import InternalError, NotFoundError

# Set up logging
logger = logging.getLogger(__name__)

# Default memory bank location
DEFAULT_MEMORY_BANK = "memory_bank"
COLLECTION_NAME = "tech_audience_accelerator"


class RAGVectorStore:
    """
    Vector store for newsletter content retrieval.

    Uses ChromaDB for semantic search over Tech Audience Accelerator newsletters.
    """

    def __init__(self, persist_directory: str = ".chromadb"):
        """
        Initialize ChromaDB client with persistent storage.

        Args:
            persist_directory: Directory to persist vector database
        """
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = None

    def init_vector_store(self, memory_bank_path: str | Path) -> None:
        """
        Ingest all .txt files from memory_bank into vector store.

        Creates embeddings for each document and stores in ChromaDB collection.
        If collection already exists, it will be recreated.

        Args:
            memory_bank_path: Path to directory containing newsletter .txt files

        Raises:
            FileNotFoundError: If memory_bank_path doesn't exist
            ValueError: If no .txt files found in memory_bank

        Example:
            >>> store = RAGVectorStore()
            >>> store.init_vector_store("memory_bank")
            >>> # Now ready for queries
        """
        memory_bank_path = Path(memory_bank_path)

        if not memory_bank_path.exists():
            raise FileNotFoundError(f"Memory bank not found: {memory_bank_path}")

        # Find all .txt files
        txt_files = list(memory_bank_path.glob("*.txt"))

        if not txt_files:
            raise ValueError(f"No .txt files found in {memory_bank_path}")

        # Delete existing collection if it exists
        try:
            self.client.delete_collection(name=COLLECTION_NAME)
        except NotFoundError:
            pass  # Collection doesn't exist yet

        # Create new collection
        self.collection = self.client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Tech Audience Accelerator newsletter corpus"},
        )

        # Ingest documents
        documents = []
        metadatas = []
        ids = []

        for idx, txt_file in enumerate(txt_files):
            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()

            documents.append(content)
            metadatas.append({"source": txt_file.name, "path": str(txt_file)})
            ids.append(f"doc_{idx}")

        # Add to collection (ChromaDB handles embedding automatically)
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)

    def query_memory_bank(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Semantic search over newsletter corpus.

        Args:
            query: Search query (e.g., "content strategies for technical audiences")
            k: Number of results to return (default: 5)

        Returns:
            List of dictionaries with keys:
            - document: Text content
            - metadata: Source file info
            - distance: Similarity score (lower = more similar)

        Raises:
            ValueError: If vector store not initialized

        Example:
            >>> store = RAGVectorStore()
            >>> store.init_vector_store("memory_bank")
            >>> results = store.query_memory_bank("hook strategies", k=3)
            >>> for result in results:
            ...     print(f"Source: {result['metadata']['source']}")
            ...     print(f"Content: {result['document'][:200]}...")
        """
        if self.collection is None:
            # Try to get existing collection
            try:
                self.collection = self.client.get_collection(name=COLLECTION_NAME)
            except ValueError:
                raise ValueError(
                    "Vector store not initialized. Call init_vector_store() or use get_rag_store(auto_init=True)."
                )

        # Perform semantic search
        results = self.collection.query(query_texts=[query], n_results=k)

        # Format results
        formatted_results = []

        if results["documents"] and results["documents"][0]:
            for idx in range(len(results["documents"][0])):
                formatted_results.append(
                    {
                        "document": results["documents"][0][idx],
                        "metadata": results["metadatas"][0][idx],
                        "distance": (
                            results["distances"][0][idx]
                            if results.get("distances")
                            else None
                        ),
                    }
                )

        return formatted_results


# Singleton instance
_rag_store: RAGVectorStore | None = None


def get_rag_store(
    persist_directory: str = ".chromadb",
    auto_init: bool = True,
    memory_bank_path: str = DEFAULT_MEMORY_BANK,
) -> RAGVectorStore:
    """
    Get singleton RAG vector store instance.

    Args:
        persist_directory: ChromaDB persistence directory
        auto_init: Automatically initialize from memory_bank if collection missing
        memory_bank_path: Path to memory bank for auto-initialization

    Returns:
        RAGVectorStore instance

    Example:
        >>> store = get_rag_store()
        >>> results = store.query_memory_bank("content structure patterns")
    """
    global _rag_store

    if _rag_store is None:
        _rag_store = RAGVectorStore(persist_directory=persist_directory)

        if auto_init:
            memory_path = Path(memory_bank_path)
            if memory_path.exists():
                try:
                    _rag_store.init_vector_store(memory_bank_path)
                except InternalError as e:
                    # Collection already exists - try to get it instead
                    if "already exists" in str(e):
                        logger.info(
                            f"Collection {COLLECTION_NAME} already exists, using existing collection"
                        )
                        try:
                            _rag_store.collection = _rag_store.client.get_collection(
                                name=COLLECTION_NAME
                            )
                        except Exception as get_error:
                            logger.error(
                                f"Failed to get existing collection: {get_error}"
                            )
                            raise
                    else:
                        # Other internal errors should be logged and propagated
                        logger.error(f"ChromaDB internal error: {e}")
                        raise
                except (OSError, PermissionError) as e:
                    # File system errors should be logged and propagated
                    logger.error(f"File system error initializing RAG store: {e}")
                    raise
                except ValueError as e:
                    # No .txt files or other validation errors
                    logger.error(f"Validation error initializing RAG store: {e}")
                    raise

    return _rag_store


def reinitialize_rag_store(memory_bank_path: str = DEFAULT_MEMORY_BANK) -> None:
    """
    Force reinitialization of RAG store from memory bank.

    Use this when memory bank content has been updated.

    Args:
        memory_bank_path: Path to memory bank directory

    Example:
        >>> # After adding new newsletters
        >>> reinitialize_rag_store("memory_bank")
    """
    global _rag_store
    _rag_store = RAGVectorStore()
    _rag_store.init_vector_store(memory_bank_path)
