from openai import AzureOpenAI
from app.config import AZURE_KEY, AZURE_ENDPOINT, AZURE_DEPLOYMENT, API_VERSION

class EmbeddingService:
    def __init__(self):
        self.client = AzureOpenAI(api_key=AZURE_KEY, azure_endpoint=AZURE_ENDPOINT,azure_deployment=AZURE_DEPLOYMENT, api_version=API_VERSION)
    
    def create_embedding(self, text: str):
        response = self.client.embeddings.create(input=text)
        return response['data'][0]['embedding']
