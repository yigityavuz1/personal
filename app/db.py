from pymongo import MongoClient
from pymongo.operations import SearchIndexModel
from app.config import MONGO_CONNECTION_STRING, MONGO_DATABASE_NAME

class MongoDBClient:
    def __init__(self):
        self.client = MongoClient(MONGO_CONNECTION_STRING)
        self.db = self.client[MONGO_DATABASE_NAME]
        self.collection = self.db['job_postings']
        self.create_vector_index()

    def create_vector_index(self):
        num_dimensions = 1536  # for text-embedding-ada-002 

        search_index_model = SearchIndexModel(
            definition={
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": num_dimensions,
                        "similarity": "cosine"
                    }
                ]
            },
            name="vector_index",
            type="vectorSearch",
        )
        try:
            result = self.collection.create_search_index(model=search_index_model)
            print(f"Index creation result: {result}")
        except Exception as e:
            print(f"Index creation failed: {e}")

    def insert_job_posting(self, job_posting_id: str, embedding: list, job_posting_text: str):
        self.collection.insert_one({
            "job_posting_id": job_posting_id,
            "embedding": embedding,
            "job_posting_text": job_posting_text
        })

    def find_similar_job_posting(self, query_embedding: list, num_candidates: int = 15, limit: int = 1):
        """
        Finds similar job postings based on the given query embedding.
        
        :param query_embedding: The vector embedding of the query text.
        :param num_candidates: Number of candidate vectors to consider for the search.
        :param limit: Number of top results to return.
        :return: A list of documents containing the most similar job postings.
        """    
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "queryVector": query_embedding,
                    "path": "embedding",
                    "numCandidates": num_candidates,
                    "limit": limit
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
