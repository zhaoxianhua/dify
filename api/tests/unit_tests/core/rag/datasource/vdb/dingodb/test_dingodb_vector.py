import json
import unittest
from unittest.mock import MagicMock, patch

import pytest

from core.rag.datasource.vdb.dingodb.dingodb_vector import (
    DingoDBVector,
    DingoDBConfig,
)
from core.rag.models.document import Document

try:
    from mysql.connector import Error as MySQLError
except ImportError:
    # Fallback for testing environments where mysql-connector-python might not be installed
    class MySQLError(Exception):
        def __init__(self, errno, msg):
            self.errno = errno
            self.msg = msg
            super().__init__(msg)


class TestDingoDBVector(unittest.TestCase):
    def setUp(self):
        self.config = DingoDBConfig(
            host="172.30.14.123",
            port=3307,
            user="root",
            password="123123",
            database="dify",
            max_connection=5,
            charset="utf8mb4",
        )
        self.collection_name = "test_collection"

        # Sample documents for testing
        self.sample_documents = [
            Document(
                page_content="This is a test document about AI.",
                metadata={"doc_id": "doc1", "document_id": "dataset1", "source": "test"},
            ),
            Document(
                page_content="Another document about machine learning.",
                metadata={"doc_id": "doc2", "document_id": "dataset1", "source": "test"},
            ),
        ]

        # Sample embeddings
        self.sample_embeddings = [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_init(self, mock_pool_class):
        """Test DingoDBVector initialization."""
        # Mock the connection pool
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        # Mock connection and cursor for vector support check
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("8.0.36",)

        dingodb_vector = DingoDBVector(self.collection_name, self.config)

        assert dingodb_vector.collection_name == self.collection_name
        assert dingodb_vector.table_name == self.collection_name.lower()
        assert dingodb_vector.get_type() == "dingodb"
        assert dingodb_vector.distance_function == "cosine"
        assert dingodb_vector.pool is not None

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_create_collection(self, mock_pool_class):
        """Test collection creation."""
        # Mock the connection pool
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("8.0.36",)

        dingodb_vector = DingoDBVector(self.collection_name, self.config)
        dingodb_vector._create_collection(4)

        # Verify CREATE TABLE was called
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_add_texts(self, mock_pool_class):
        """Test adding texts to collection."""
        # Mock the connection pool
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("8.0.36",)

        dingodb_vector = DingoDBVector(self.collection_name, self.config)

        # Add feature_id to metadata
        for doc in self.sample_documents:
            doc.metadata["feature_id"] = 1

        dingodb_vector.add_texts(self.sample_documents, self.sample_embeddings)

        # Verify INSERT was called
        mock_cursor.executemany.assert_called()
        mock_conn.commit.assert_called()

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_search_by_vector(self, mock_pool_class):
        """Test vector search."""
        # Mock the connection pool
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("8.0.36",)

        # Mock search results
        mock_cursor.fetchall.return_value = [
            {
                "text": "Test document",
                "meta": '{"doc_id": "doc1", "document_id": "dataset1"}',
                "feature_index$distance": 0.1,
            }
        ]

        dingodb_vector = DingoDBVector(self.collection_name, self.config)
        results = dingodb_vector.search_by_vector([0.1, 0.2, 0.3, 0.4])

        assert len(results) == 1
        assert results[0].page_content == "Test document"
        assert results[0].metadata["doc_id"] == "doc1"
        assert "score" in results[0].metadata

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_search_by_full_text(self, mock_pool_class):
        """Test full-text search."""
        # Mock the connection pool
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("8.0.36",)

        # Mock search results
        mock_cursor.fetchall.return_value = [
            {
                "text": "Test document",
                "meta": '{"doc_id": "doc1", "document_id": "dataset1"}',
                "text_index$rank_bm25": 1.5,
            }
        ]

        dingodb_vector = DingoDBVector(self.collection_name, self.config)
        results = dingodb_vector.search_by_full_text("test query")

        assert len(results) == 1
        assert results[0].page_content == "Test document"
        assert results[0].metadata["doc_id"] == "doc1"
        assert results[0].metadata["score"] == 1.5

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_delete_by_ids(self, mock_pool_class):
        """Test deleting documents by IDs."""
        # Mock the connection pool
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("8.0.36",)

        dingodb_vector = DingoDBVector(self.collection_name, self.config)
        dingodb_vector.delete_by_ids(["doc1", "doc2"])

        # Verify DELETE was called
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_delete_collection(self, mock_pool_class):
        """Test deleting the entire collection."""
        # Mock the connection pool
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("8.0.36",)

        dingodb_vector = DingoDBVector(self.collection_name, self.config)
        dingodb_vector.delete()

        # Verify DROP TABLE was called
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
