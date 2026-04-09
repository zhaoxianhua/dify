from core.rag.datasource.vdb.dingodb.dingodb_vector import DingoDBVector, DingoDBConfig
from tests.integration_tests.vdb.test_vector_store import AbstractVectorTest, setup_mock_redis
from tests.integration_tests.vdb.__mock.dingodb import setup_dingodb_mock

class DingoDBVectorTest(AbstractVectorTest):
    def __init__(self):
        super().__init__()
        self.vector = DingoDBVector(
            collection_name="test_collection",
            config=DingoDBConfig(
                host="172.30.14.123",
                port=3307,
                user="root",
                password="123123",
                database="dify",
            ),
        )

    def search_by_vector(self):
        hits_by_vector = self.vector.search_by_vector(query_vector=self.example_embedding)
        assert len(hits_by_vector) == 1

    def get_ids_by_metadata_field(self):
        ids = self.vector.get_ids_by_metadata_field(key="doc_id", value="test_document_id")
        assert len(ids) > 0

def test_dingodb_vector(setup_mock_redis, setup_dingodb_mock):
    DingoDBVectorTest().run_all_tests()


