import json
import logging
import math
from typing import Any
import uuid
from contextlib import contextmanager

from pydantic import BaseModel, model_validator
import mysql.connector
from mysql.connector import Error as MySQLError
from sqlalchemy import JSON, Column, String, func, text, create_engine
from sqlalchemy.dialects.mysql import LONGTEXT

from configs import dify_config
from core.rag.datasource.vdb.vector_base import BaseVector
from core.rag.datasource.vdb.vector_factory import AbstractVectorFactory
from core.rag.datasource.vdb.vector_type import VectorType
from core.rag.embedding.embedding_base import Embeddings
from core.rag.models.document import Document
from extensions.ext_redis import redis_client
from models.dataset import Dataset

logger = logging.getLogger(__name__)

DEFAULT_DingoDB_HNSW_BUILD_PARAM = {"M": 32, "efConstruction": 40}
DEFAULT_DingoDB_HNSW_SEARCH_PARAM = {"efSearch": 64}
DingoDB_SUPPORTED_VECTOR_INDEX_TYPE = "HNSW"
DEFAULT_DingoDB_VECTOR_METRIC_TYPE = "L2"  # DingoDB是大写L2


class DingoDBVectorConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str = "utf8mb4"
    max_connection: int = 5  # 保留配置，但实际不用连接池

    @model_validator(mode="before")
    @classmethod
    def validate_config(cls, values: dict) -> dict:
        if not values["host"]:
            raise ValueError("config DingoDB_VECTOR_HOST is required")
        if not values["port"]:
            raise ValueError("config DingoDB_VECTOR_PORT is required")
        if not values["user"]:
            raise ValueError("config DingoDB_VECTOR_USER is required")
        if not values["database"]:
            raise ValueError("config DingoDB_VECTOR_DATABASE is required")
        values.setdefault("charset", "utf8mb4")
        values.setdefault("max_connection", 5)
        return values


class DingoDBVector(BaseVector):
    def __init__(self, collection_name: str, config: DingoDBVectorConfig):
        super().__init__(collection_name)
        self._config = config
        self._hnsw_ef_search = -1
        self._vec_dim = 0
        self._table_name = collection_name.lower()
        self._db_config = {
            "host": config.host,
            "port": config.port,
            "user": config.user,
            "password": config.password,
            "database": config.database,
            "charset": config.charset
        }

    def get_type(self) -> str:
        return VectorType.DINGODB

    @contextmanager
    def _get_cursor(self):
        """获取数据库游标（自动管理连接，和正确代码一致）"""
        conn = None
        cur = None
        try:
            conn = mysql.connector.connect(**self._db_config)
            cur = conn.cursor()
            yield cur
            conn.commit()
        except MySQLError as e:
            if conn:
                conn.rollback()
            logger.error(f"DingoDB operation error: {e}")
            raise
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    def _vector_to_str(self, vector: list[float]) -> str:
        """
        将float列表转为DingoDB兼容的逗号分隔字符串
        """

        def format_float(x):
            formatted = f"{x:.6f}"
            if '.' in formatted:
                formatted = formatted.rstrip('0').rstrip('.') if formatted.rstrip('0').endswith(
                    '.') else formatted.rstrip('0')
            return formatted

        return ",".join([format_float(x) for x in vector])

    def _text_deal(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace('\'', '"')
        text = text.replace('\\"', '"')
        text = text.replace('\\', '\\\\')
        text = text.replace('\\\'', '"')
        text = text.replace("/*", "/.")
        text = text.replace("*/", "./")
        return text

    def create(self, texts: list[Document], embeddings: list[list[float]], **kwargs):
        if not embeddings:
            raise ValueError("Embeddings list cannot be empty")
        self._vec_dim = len(embeddings[0])
        self._create_collection()
        self.add_texts(texts, embeddings)

    def _create_collection(self) -> None:
        lock_name = "vector_indexing_lock_" + self._collection_name
        with redis_client.lock(lock_name, timeout=20):
            collection_exist_cache_key = "vector_indexing_" + self._collection_name
            if redis_client.get(collection_exist_cache_key):
                return

            if self._check_table_exists():
                return

            self.delete()
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self._table_name}(
                id BIGINT AUTO_INCREMENT,
                chunk_content VARCHAR(10000) NOT NULL,
                file_name VARCHAR(256),
                vecs FLOAT ARRAY NOT NULL,
                metadata JSON NOT NULL,
                INDEX vecs_index VECTOR(id, vecs)
                PARAMETERS(
                    type=hnsw,
                    metricType={DEFAULT_DingoDB_VECTOR_METRIC_TYPE},
                    dimension={self._vec_dim},
                    efConstruction={DEFAULT_DingoDB_HNSW_BUILD_PARAM["efConstruction"]},
                    nlinks={DEFAULT_DingoDB_HNSW_BUILD_PARAM["M"]}
                ),
                PRIMARY KEY(id)
            ) COMMENT 'columnar=1';
            """

            with self._get_cursor() as cur:
                clean_sql = create_table_sql.replace("\n", " ").replace("  ", " ").strip()
                cur.execute(clean_sql)
                logger.info(f"DingoDB table {self._table_name} created successfully with vector index")

            redis_client.set(collection_exist_cache_key, 1, ex=3600)

    def _check_table_exists(self) -> bool:
        """检查表是否存在"""
        check_sql = f"""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s;
        """
        with self._get_cursor() as cur:
            cur.execute(check_sql, (self._config.database, self._table_name))
            result = cur.fetchone()
            return result[0] > 0  # 普通游标返回元组，取第一个元素

    def _get_uuids(self, documents: list[Document]) -> list[str]:
        """生成文档ID（补充缺失的方法）"""
        ids = []
        for doc in documents:
            if doc.metadata and doc.metadata.get("doc_id"):
                ids.append(doc.metadata["doc_id"])
            else:
                ids.append(str(uuid.uuid4()))
        return ids

    def add_texts(self, documents: list[Document], embeddings: list[list[float]], **kwargs):
        if len(documents) != len(embeddings):
            raise ValueError("Documents and embeddings length mismatch")

        ids = self._get_uuids(documents)
        entry_count = 0

        try:
            with self._get_cursor() as cur:
                for i, doc in enumerate(documents):
                    file_name = doc.metadata.get("file_name", ids[i]) if doc.metadata else ids[i]
                    clean_content = self._text_deal(doc.page_content)
                    clean_filename = self._text_deal(file_name)
                    vec_str = self._vector_to_str(embeddings[i])
                    meta_str = self._text_deal(json.dumps(doc.metadata or {}))

                    insert_sql = f"""
                    INSERT INTO {self._table_name} (chunk_content, file_name, vecs, metadata)
                    VALUES ('{clean_content}', '{clean_filename}', array[{vec_str}], '{meta_str}')
                    """
                    clean_insert_sql = insert_sql.replace("\n", " ").strip()

                    try:
                        cur.execute(clean_insert_sql)
                        entry_count += 1
                    except MySQLError as e:
                        logger.error(f"Insert failed for doc {ids[i]}: {e}, SQL: {clean_insert_sql[:200]}...")
                        raise

                logger.info(f"Successfully inserted {entry_count} documents to DingoDB")
        except Exception as e:
            logger.error(f"DingoDB insert failed: {e}")
            raise

        return ids

    def text_exists(self, id: str) -> bool:
        check_sql = f"""
        SELECT id FROM {self._table_name}
        WHERE JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.doc_id')) = %s LIMIT 1;
        """
        with self._get_cursor() as cur:
            cur.execute(check_sql, (id,))
            return cur.fetchone() is not None

    def delete_by_ids(self, ids: list[str]) -> None:
        if not ids:
            return
        placeholders = ",".join(["%s"] * len(ids))
        delete_sql = f"""
        DELETE FROM {self._table_name}
        WHERE JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.doc_id')) IN ({placeholders});
        """
        with self._get_cursor() as cur:
            cur.execute(delete_sql, ids)

    def get_ids_by_metadata_field(self, key: str, value: str) -> list[str]:
        # 修复点11：普通游标适配
        query_sql = f"""
        SELECT JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.doc_id')) FROM {self._table_name}
        WHERE JSON_UNQUOTE(JSON_EXTRACT(metadata, %s)) = %s;
        """
        json_path = f"$.{key}"
        with self._get_cursor() as cur:
            cur.execute(query_sql, (json_path, value))
            results = cur.fetchall()
            return [row[0] for row in results if row[0]]

    def delete_by_metadata_field(self, key: str, value: str) -> None:
        ids = self.get_ids_by_metadata_field(key, value)
        self.delete_by_ids(ids)

    def search_by_full_text(self, query: str, **kwargs: Any) -> list[Document]:
        raise NotImplementedError("DingoDB full-text search is not supported in this version")

    def search_by_vector(self, query_vector: list[float], **kwargs: Any) -> list[Document]:
        topk = kwargs.get("top_k", 10)
        if topk <= 0:
            raise ValueError("top_k must be a positive integer")

        query_vector_str = self._vector_to_str(query_vector)
        base_sql = f"""
        SELECT chunk_content, metadata, vecs_index$distance
        FROM vector({self._table_name}, vecs, array[{query_vector_str}], {topk})
        """

        document_ids_filter = kwargs.get("document_ids_filter")
        if document_ids_filter:
            ids_placeholder = ",".join([f"'{self._text_deal(id)}'" for id in document_ids_filter])
            base_sql += f" WHERE JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.doc_id')) IN ({ids_placeholder})"

        search_sql = f"{base_sql} ORDER BY vecs_index$distance;"
        clean_search_sql = search_sql.replace("\n", " ").strip()

        docs = []
        score_threshold = float(kwargs.get("score_threshold", 0.0))
        with self._get_cursor() as cur:
            cur.execute(clean_search_sql)
            results = cur.fetchall()

            for row in results:
                text = row[0]
                metadata = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                distance = row[2]
                score = 1 / (1 + distance) if distance and distance >= 0 else 0.0
                if score >= score_threshold:
                    metadata["score"] = score
                    metadata["distance"] = distance
                    docs.append(
                        Document(
                            page_content=text,
                            metadata=metadata,
                        )
                    )
        return docs

    def delete(self) -> None:
        """删除表"""
        drop_sql = f"DROP TABLE IF EXISTS {self._table_name};"
        with self._get_cursor() as cur:
            cur.execute(drop_sql)


class DingoDBVectorFactory(AbstractVectorFactory):
    def init_vector(
        self,
        dataset: Dataset,
        attributes: list,
        embeddings: Embeddings,
    ) -> BaseVector:
        if dataset.index_struct_dict:
            vector_type = dataset.index_struct_dict.get("type", VectorType.DINGODB)
            class_prefix: str = dataset.index_struct_dict["vector_store"]["class_prefix"]
            collection_name = class_prefix.lower()
        else:
            dataset_id = dataset.id
            collection_name = Dataset.gen_collection_name_by_id(dataset_id).lower()
            dataset.index_struct = json.dumps(self.gen_index_struct_dict(VectorType.DINGODB, collection_name))

        return DingoDBVector(
            collection_name=collection_name,
            config=DingoDBVectorConfig(
                host=dify_config.DINGODB_HOST or "",
                port=dify_config.DINGODB_PORT or 0,
                user=dify_config.DINGODB_USER or "",
                password=dify_config.DINGODB_PASSWORD or "",
                database=dify_config.DINGODB_DATABASE or "",
                charset=dify_config.DINGODB_CHARSET or "utf8mb4",
                max_connection=dify_config.DINGODB_MAX_CONNECTION or 5,
            ),
        )

    def gen_index_struct_dict(self, vector_type, collection_name):
        """修正：type字段放在顶层，匹配调用方逻辑"""
        return {
            "type": vector_type,
            "vector_store": {
                "class_prefix": collection_name
            }
        }
