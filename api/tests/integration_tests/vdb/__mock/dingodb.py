import os
from unittest.mock import MagicMock
from typing import List, Dict, Any, Union
import pytest
from _pytest.monkeypatch import MonkeyPatch
from core.rag.models.document import Document
from core.rag.datasource.vdb.dingodb.dingodb_vector import DingoDBVector, DingoDBConfig

# 全局变量：模拟测试用的文档ID
_TEST_DOC_ID = None
MOCK = os.getenv("MOCK_SWITCH", "false").lower() == "true"

# 修正后的 Mock 核心方法：使用 texts 参数
def mock_create(self, texts: List[Any], embeddings: List[List[float]], **kwargs) -> None:
    """Mock create 方法，匹配 BaseVector 抽象类签名"""
    global _TEST_DOC_ID
    _TEST_DOC_ID = [doc.metadata.get("doc_id") for doc in texts]


def mock_search_by_vector(
    self,
    query_vector: List[float],
    top_k: int = 10,
    filter: Dict[str, Any] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """Mock search_by_vector 方法"""
    global _TEST_DOC_ID
    return [
        {
            "id": _TEST_DOC_ID[0] if _TEST_DOC_ID else "mock_doc_id",
            "text": "mock content",
            "meta": '{"doc_id": "' + (_TEST_DOC_ID[0] if _TEST_DOC_ID else "mock_doc_id") + '"}',
            "feature_index$distance": 0.1
        }
    ]


def mock_search_by_full_text(self, query: str, **kwargs) -> List[Document]:
    """Mock search_by_full_text 方法，返回 Document 对象"""
    from core.rag.models.document import Document

    global _TEST_DOC_ID
    return [
        Document(
            page_content="mock content",
            metadata={
                "doc_id": _TEST_DOC_ID[0] if _TEST_DOC_ID else "mock_doc_id"
            }
        )
    ]


def mock_add_texts(self, documents: List[Any], embeddings: List[List[float]], **kwargs) -> List[str]:
    """Mock add_texts 方法，匹配 BaseVector 抽象类签名"""
    global _TEST_DOC_ID
    _TEST_DOC_ID = [doc.metadata.get("doc_id") for doc in documents]
    return _TEST_DOC_ID


def mock_text_exists(self, doc_id: str) -> bool:
    """Mock text_exists 方法"""
    global _TEST_DOC_ID
    return _TEST_DOC_ID and doc_id in _TEST_DOC_ID


def mock_delete_by_ids(self, ids: List[str]) -> None:
    """Mock delete_by_ids 方法"""
    global _TEST_DOC_ID
    if _TEST_DOC_ID:
        _TEST_DOC_ID = [doc_id for doc_id in _TEST_DOC_ID if doc_id not in ids]


def mock_delete_by_metadata_field(self, key: str, value: str) -> None:
    """Mock delete_by_metadata_field 方法"""
    pass


def mock_delete(self) -> None:
    """Mock delete 方法"""
    global _TEST_DOC_ID
    _TEST_DOC_ID = None


MOCK = os.getenv("MOCK_SWITCH", "false").lower() == "true"

@pytest.fixture
def setup_dingodb_mock(request, monkeypatch: MonkeyPatch):
    if MOCK:
        # Mock MySQL connection pool
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Version check
        mock_cursor.fetchone.return_value = ("8.0.36",)

        # Mock search results for search_by_vector
        mock_cursor.fetchall.side_effect = [
            # First call: get_ids_by_metadata_field returns
            [{"doc_id": "test_document_id"}],
            # Second call: search_by_vector returns
            [{
                "id": "test_document_id",
                "text": "test content",
                "meta": '{"doc_id": "test_document_id"}',
                "feature_index$distance": 0.1
            }],
            # Third call: search_by_full_text returns
            [{
                "id": "test_document_id",
                "text": "test content",
                "meta": '{"doc_id": "test_document_id"}',
                "text_index$rank_bm25": 0.9
            }]
        ]

        monkeypatch.setattr(
            "mysql.connector.pooling.MySQLConnectionPool",
            lambda **kwargs: mock_pool
        )

        # Mock all required methods
        monkeypatch.setattr(DingoDBVector, "create", mock_create)
        monkeypatch.setattr(DingoDBVector, "add_texts", mock_add_texts)
        monkeypatch.setattr(DingoDBVector, "search_by_vector", mock_search_by_vector)
        monkeypatch.setattr(DingoDBVector, "search_by_full_text", mock_search_by_full_text)
        monkeypatch.setattr(DingoDBVector, "text_exists", mock_text_exists)
        monkeypatch.setattr(DingoDBVector, "delete_by_ids", mock_delete_by_ids)
        monkeypatch.setattr(DingoDBVector, "delete_by_metadata_field", mock_delete_by_metadata_field)
        monkeypatch.setattr(DingoDBVector, "delete", mock_delete)

    yield
    if MOCK:
        monkeypatch.undo()
