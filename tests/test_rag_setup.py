"""
Tests for RAG setup exception handling.

Validates that specific exceptions are caught and handled appropriately,
and that legitimate errors are not silently swallowed.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from chromadb.errors import InternalError, NotFoundError

from core.rag_setup import (
    RAGVectorStore,
    get_rag_store,
    reinitialize_rag_store,
    COLLECTION_NAME,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def memory_bank_dir(temp_dir):
    """Create a temporary memory bank with test files."""
    memory_path = Path(temp_dir) / "memory_bank"
    memory_path.mkdir()

    # Create a test .txt file
    test_file = memory_path / "test_newsletter.txt"
    test_file.write_text("Test newsletter content for RAG testing.")

    return str(memory_path)


@pytest.fixture
def empty_memory_bank(temp_dir):
    """Create an empty memory bank directory."""
    memory_path = Path(temp_dir) / "empty_memory_bank"
    memory_path.mkdir()
    return str(memory_path)


@pytest.fixture
def chromadb_dir(temp_dir):
    """Create a temporary ChromaDB directory."""
    chroma_path = Path(temp_dir) / ".chromadb"
    return str(chroma_path)


@pytest.fixture
def mock_chromadb_client():
    """Mock ChromaDB client to avoid network calls."""
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = COLLECTION_NAME

        mock_client.create_collection.return_value = mock_collection
        mock_client.get_collection.return_value = mock_collection
        mock_client.delete_collection.return_value = None

        mock_client_class.return_value = mock_client

        yield mock_client


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton RAG store before each test."""
    import core.rag_setup

    core.rag_setup._rag_store = None
    yield
    core.rag_setup._rag_store = None


class TestRAGVectorStoreInitialization:
    """Test RAGVectorStore initialization and exception handling."""

    def test_init_vector_store_success(
        self, memory_bank_dir, chromadb_dir, mock_chromadb_client
    ):
        """Test successful vector store initialization."""
        store = RAGVectorStore(persist_directory=chromadb_dir)
        store.init_vector_store(memory_bank_dir)

        assert store.collection is not None
        assert store.collection.name == COLLECTION_NAME

    def test_init_vector_store_memory_bank_not_found(self, chromadb_dir):
        """Test that FileNotFoundError is raised for missing memory bank."""
        store = RAGVectorStore(persist_directory=chromadb_dir)

        with pytest.raises(FileNotFoundError, match="Memory bank not found"):
            store.init_vector_store("/nonexistent/path")

    def test_init_vector_store_no_txt_files(self, empty_memory_bank, chromadb_dir):
        """Test that ValueError is raised when no .txt files found."""
        store = RAGVectorStore(persist_directory=chromadb_dir)

        with pytest.raises(ValueError, match="No .txt files found"):
            store.init_vector_store(empty_memory_bank)

    def test_init_vector_store_handles_not_found_error(
        self, memory_bank_dir, chromadb_dir, mock_chromadb_client
    ):
        """Test that NotFoundError is caught when deleting non-existent collection."""
        store = RAGVectorStore(persist_directory=chromadb_dir)

        # Mock delete_collection to raise NotFoundError
        mock_chromadb_client.delete_collection.side_effect = NotFoundError("test")

        # Should not raise - NotFoundError is caught
        store.init_vector_store(memory_bank_dir)
        assert store.collection is not None

    def test_init_vector_store_twice_recreates_collection(
        self, memory_bank_dir, chromadb_dir, mock_chromadb_client
    ):
        """Test that calling init_vector_store twice recreates the collection."""
        # Create different mock collections for each call
        mock_collection1 = MagicMock()
        mock_collection1.name = COLLECTION_NAME
        mock_collection2 = MagicMock()
        mock_collection2.name = COLLECTION_NAME

        mock_chromadb_client.create_collection.side_effect = [
            mock_collection1,
            mock_collection2,
        ]

        store = RAGVectorStore(persist_directory=chromadb_dir)

        # First initialization
        store.init_vector_store(memory_bank_dir)
        first_collection = store.collection

        # Second initialization should delete and recreate
        store.init_vector_store(memory_bank_dir)
        second_collection = store.collection

        # Collection objects should be different (recreated)
        assert store.collection is not None
        assert first_collection is not second_collection


class TestGetRAGStore:
    """Test get_rag_store function and exception handling."""

    def test_get_rag_store_auto_init_success(
        self, memory_bank_dir, chromadb_dir, mock_chromadb_client
    ):
        """Test successful auto-initialization."""
        store = get_rag_store(
            persist_directory=chromadb_dir,
            auto_init=True,
            memory_bank_path=memory_bank_dir,
        )

        assert store is not None
        assert store.collection is not None

    def test_get_rag_store_without_auto_init(self, chromadb_dir):
        """Test getting store without auto-initialization."""
        store = get_rag_store(
            persist_directory=chromadb_dir,
            auto_init=False,
        )

        assert store is not None
        # Collection should not be initialized
        assert store.collection is None

    def test_get_rag_store_memory_bank_not_exists(self, chromadb_dir):
        """Test that missing memory bank path is silently skipped during auto-initialization."""
        # Should not raise - memory bank path doesn't exist so init is skipped
        store = get_rag_store(
            persist_directory=chromadb_dir,
            auto_init=True,
            memory_bank_path="/nonexistent/path",
        )

        assert store is not None
        assert store.collection is None

    def test_get_rag_store_propagates_file_not_found_error(
        self, temp_dir, chromadb_dir
    ):
        """Test that FileNotFoundError is propagated, not swallowed."""
        # Create a path that exists but triggers FileNotFoundError in init_vector_store
        memory_path = Path(temp_dir) / "memory_bank"
        memory_path.mkdir()

        with patch(
            "core.rag_setup.RAGVectorStore.init_vector_store",
            side_effect=FileNotFoundError("Mocked error"),
        ):
            with pytest.raises(FileNotFoundError, match="Mocked error"):
                get_rag_store(
                    persist_directory=chromadb_dir,
                    auto_init=True,
                    memory_bank_path=str(memory_path),
                )

    def test_get_rag_store_propagates_permission_error(
        self, memory_bank_dir, chromadb_dir
    ):
        """Test that PermissionError is propagated, not swallowed."""
        with patch(
            "core.rag_setup.RAGVectorStore.init_vector_store",
            side_effect=PermissionError("Permission denied"),
        ):
            with pytest.raises(PermissionError, match="Permission denied"):
                get_rag_store(
                    persist_directory=chromadb_dir,
                    auto_init=True,
                    memory_bank_path=memory_bank_dir,
                )

    def test_get_rag_store_propagates_os_error(self, memory_bank_dir, chromadb_dir):
        """Test that OSError is propagated, not swallowed."""
        with patch(
            "core.rag_setup.RAGVectorStore.init_vector_store",
            side_effect=OSError("Disk error"),
        ):
            with pytest.raises(OSError, match="Disk error"):
                get_rag_store(
                    persist_directory=chromadb_dir,
                    auto_init=True,
                    memory_bank_path=memory_bank_dir,
                )

    def test_get_rag_store_propagates_value_error(self, memory_bank_dir, chromadb_dir):
        """Test that ValueError is propagated, not swallowed."""
        with patch(
            "core.rag_setup.RAGVectorStore.init_vector_store",
            side_effect=ValueError("No .txt files found"),
        ):
            with pytest.raises(ValueError, match="No .txt files found"):
                get_rag_store(
                    persist_directory=chromadb_dir,
                    auto_init=True,
                    memory_bank_path=memory_bank_dir,
                )

    def test_get_rag_store_handles_internal_error_collection_exists(
        self, memory_bank_dir, chromadb_dir, mock_chromadb_client, caplog
    ):
        """Test that InternalError for existing collection is handled gracefully."""
        # Create a mock collection
        mock_collection = MagicMock()
        mock_collection.name = COLLECTION_NAME
        mock_chromadb_client.get_collection.return_value = mock_collection

        with (
            patch(
                "core.rag_setup.RAGVectorStore.init_vector_store",
                side_effect=InternalError(
                    "Collection [test_collection] already exists"
                ),
            ),
            caplog.at_level(logging.INFO),
        ):
            store = get_rag_store(
                persist_directory=chromadb_dir,
                auto_init=True,
                memory_bank_path=memory_bank_dir,
            )

            # Should not raise and should log info message
            assert store is not None
            assert "already exists" in caplog.text.lower()

    def test_get_rag_store_propagates_internal_error_other(
        self, memory_bank_dir, chromadb_dir, caplog
    ):
        """Test that other InternalErrors are propagated."""
        with (
            patch(
                "core.rag_setup.RAGVectorStore.init_vector_store",
                side_effect=InternalError("Some other internal error"),
            ),
            caplog.at_level(logging.ERROR),
        ):
            with pytest.raises(InternalError, match="Some other internal error"):
                get_rag_store(
                    persist_directory=chromadb_dir,
                    auto_init=True,
                    memory_bank_path=memory_bank_dir,
                )

            # Should log the error
            assert "internal error" in caplog.text.lower()

    def test_get_rag_store_logs_errors(self, memory_bank_dir, chromadb_dir, caplog):
        """Test that errors are logged before being propagated."""
        with (
            patch(
                "core.rag_setup.RAGVectorStore.init_vector_store",
                side_effect=ValueError("Test validation error"),
            ),
            caplog.at_level(logging.ERROR),
        ):
            with pytest.raises(ValueError):
                get_rag_store(
                    persist_directory=chromadb_dir,
                    auto_init=True,
                    memory_bank_path=memory_bank_dir,
                )

            # Should log the error
            assert "validation error" in caplog.text.lower()

    def test_get_rag_store_singleton_behavior(
        self, memory_bank_dir, chromadb_dir, mock_chromadb_client
    ):
        """Test that get_rag_store returns the same instance."""
        store1 = get_rag_store(
            persist_directory=chromadb_dir,
            auto_init=True,
            memory_bank_path=memory_bank_dir,
        )

        store2 = get_rag_store(
            persist_directory=chromadb_dir,
            auto_init=True,
            memory_bank_path=memory_bank_dir,
        )

        # Should be the same instance
        assert store1 is store2


class TestReinitializeRAGStore:
    """Test reinitialize_rag_store function."""

    def test_reinitialize_creates_new_store(
        self, memory_bank_dir, chromadb_dir, mock_chromadb_client
    ):
        """Test that reinitialize creates a new store instance."""
        # Get initial store
        store1 = get_rag_store(
            persist_directory=chromadb_dir,
            auto_init=True,
            memory_bank_path=memory_bank_dir,
        )

        # Reinitialize
        reinitialize_rag_store(memory_bank_path=memory_bank_dir)

        # Get store again
        store2 = get_rag_store(persist_directory=chromadb_dir)

        # Should be a different instance
        assert store1 is not store2


class TestLogging:
    """Test that proper logging is used for error reporting."""

    def test_logger_is_configured(self):
        """Test that logger is properly configured."""
        from core.rag_setup import logger

        assert logger.name == "core.rag_setup"

    def test_file_system_errors_are_logged(self, memory_bank_dir, chromadb_dir, caplog):
        """Test that file system errors are logged with appropriate level."""
        with (
            patch(
                "core.rag_setup.RAGVectorStore.init_vector_store",
                side_effect=OSError("Disk full"),
            ),
            caplog.at_level(logging.ERROR),
        ):
            with pytest.raises(OSError):
                get_rag_store(
                    persist_directory=chromadb_dir,
                    auto_init=True,
                    memory_bank_path=memory_bank_dir,
                )

            assert "file system error" in caplog.text.lower()
            assert "disk full" in caplog.text.lower()

    def test_chromadb_errors_are_logged(self, memory_bank_dir, chromadb_dir, caplog):
        """Test that ChromaDB errors are logged with appropriate level."""
        with (
            patch(
                "core.rag_setup.RAGVectorStore.init_vector_store",
                side_effect=InternalError("ChromaDB API error"),
            ),
            caplog.at_level(logging.ERROR),
        ):
            with pytest.raises(InternalError):
                get_rag_store(
                    persist_directory=chromadb_dir,
                    auto_init=True,
                    memory_bank_path=memory_bank_dir,
                )

            assert "chromadb internal error" in caplog.text.lower()
