
"""
Azure Blob Storage'dan ürün verilerini okur. 

Belirli anahtar kelimeleri kaldırarak ve metni küçük harfe çevirerek ürün verilerini temizler. 

JSON benzeri stringlerden oluşan bir liste oluşturarak verileri indeksleme için hazırlar. 

Ürün verileri için gömümler (embeddings) oluşturmak üzere Azure OpenAI'ye bağlanır. 

Ürün detayları ve gömümler ile bir belge listesi oluşturur. 

Alanlar ve vektör arama yapılandırmaları dahil olmak üzere bir Azure AI Search indeksi için şema tanımlar. 

Aynı ada sahip mevcut herhangi bir indeksi siler. 

Tanımlanan şema ile yeni bir indeks oluşturur. 

Hazırlanan belgeleri yeni oluşturulan indekse partiler halinde yükler. 
 
Modüller: 

pandas: Veri manipülasyonu ve temizleme için kullanılır. 

azure.core.credentials: Azure hizmetleri için kimlik bilgileri sağlar. 

azure.search.documents: Azure AISearch ile etkileşim için kullanılır. 

openai: Azure OpenAI ile gömümler oluşturmak için kullanılır. 
 
Fonksiyonlar: 

Yok 
 
Değişkenler: 

account_name: Azure Depolama hesap adı. 

account_key: Azure Depolama hesap anahtarı. 

connection_string: Azure Depolama için bağlantı dizesi. 

urun_data: Azure Blob Storage'dan okunan ürün verilerini içeren DataFrame. 

urun_data_cleaned: Temizlenmiş ürün verilerini içeren DataFrame. 

row_list: Temizlenmiş ürün verilerini temsil eden JSON benzeri stringlerden oluşan liste. 

service_endpoint: Azure AI Search için uç nokta URL'si. 

key: Azure AI Search için API anahtarı. 

index_client: Azure AI Search indekslerini yönetmek için kullanılan istemci. 

azure_openai_client: Azure OpenAI ile etkileşim için kullanılan istemci. 

embeddings: Azure OpenAI tarafından oluşturulan embedding listesi. 

docs: Azure AI Search'te indekslenecek belgeler listesi. 

name: Azure AI Search indeksi adı. 

fields: Azure AI Search indeksinin şemasını tanımlayan alanlar listesi. 

vector_search: Azure AI Search'te vektör arama yapılandırması. 

prioritized_fields: Anlamsal arama için öncelikli alanlar yapılandırması. 

semantic_config: Anlamsal arama yapılandırması. 

semantic_search_: Anlamsal arama yapılandırma nesnesi. 

cors_options: Azure AI Search indeksi için CORS seçenekleri. 

scoring_profiles: Azure AI Search indeksi için puanlama profilleri listesi. 

index: Azure AI Search indeksi şeması ve yapılandırmalarını tanımlayan SearchIndex nesnesi. 

result: İndeks oluşturma işleminin sonucu. 

index_client_upload: Belgeleri Azure AI Search indeksine yüklemek için kullanılan istemci. 

step_size: Her partide yüklenecek belge sayısı. (Bütün belgeler tek seferde yüklenmek istendiğinde Azure tarafında hata dönüyor) 
"""
import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
from azure.search.documents.indexes import SearchIndexClient 
from azure.search.documents.indexes.models import (  
    SearchIndex,  
    SearchField,  
    SearchFieldDataType,  
    SimpleField,  
    SearchableField,  
    SearchIndex,
    SearchField,  
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    ComplexField,
    CorsOptions,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch
) 
vault_url = "https://kv-sales-assistant-dev.vault.azure.net/"
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=vault_url, credential=credential)
openai_key = secret_client.get_secret("OPENAI-KEY").value
ai_search_key = secret_client.get_secret("AI-SEARCH-ADMIN-KEY").value

urun_data_cleaned = pd.read_csv("products.csv")
urun_data_cleaned['product_desc_cleaned'] = urun_data_cleaned['product_desc'].str.replace('\bKoli\b|\bKOLİ\b|\bkoli\b|\bKOLI\b', '')


row_list = []
for idx,value in urun_data_cleaned.iterrows():
    temp_list = []
    for i in urun_data_cleaned.columns:
        temp_list.append('"{i}": "{k}"'.format(i=i,k=value[i]))
    row_list.append('{'+','.join(temp_list)+'}')
#print("rows are ready")
service_endpoint = "https://ai-search-rag-product-dev.search.windows.net"
#index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]


index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(ai_search_key))

azure_openai_client = AzureOpenAI(
    api_key = openai_key,
    api_version = "2024-02-15-preview",
    azure_deployment= "Text-Embedding",
    azure_endpoint = "https://openai-sales-assistant-dev.openai.azure.com/"
)


embeddings= []
for a in row_list:
    embeddings.append(azure_openai_client.embeddings.create(input=a, model="text-embedding-canada"))
    
    
docs = [
    {
        "product_code": str(row["Product_Code"]),
        "product_desc": str(row["Product_Desc"]),
        "brand_desc": str(row["Brand_Desc"]),
        "category_1_desc": str(row["Category_1_Desc"]),
        "category_2_desc": str(row["Category_2_Desc"]),
        "product_desc_cleaned": str(row["product_desc_cleaned"]),
        "myHnsw": embeddings[idx].data[0].embedding
    }
    for idx, row in urun_data_cleaned.iterrows()
]
#print("docs are ready")

name = "ai-search-rag-product-dev"
fields = [
    SimpleField(name="product_code", type=SearchFieldDataType.String, key=True),
    SearchableField(name="product_desc", type=SearchFieldDataType.String),
    SearchableField(name="brand_desc", type=SearchFieldDataType.String, searchable=True),
    SearchableField(name="category_1_desc", type=SearchFieldDataType.String, searchable=True),
    SearchableField(name="category_2_desc", type=SearchFieldDataType.String, searchable=True),
    SearchableField(name="category_2_desc", type=SearchFieldDataType.String, searchable=True),
    SearchField(name="myHnsw",searchable=True, vector_search_dimensions= 3072,vector_search_profile_name = "myHnsw",type=SearchFieldDataType.Collection(SearchFieldDataType.Single)),
]


vector_search = VectorSearch(
    algorithms=[
        HnswAlgorithmConfiguration(
            name="myHnsw"
        )
    ],
    profiles=[
        VectorSearchProfile(
            name="myHnsw",
            algorithm_configuration_name="myHnsw",
        )
    ]
)
prioritized_fields = {  
    "title_field": None,  
    "content_fields": [SemanticField(field_name='product_desc')],  
    "keywords_fields": [SemanticField(field_name='product_desc_cleaned')]  
}  
semantic_config = SemanticConfiguration(
    name = "semanticconfig",
    prioritized_fields = SemanticPrioritizedFields(content_fields=[SemanticField(field_name='product_desc_cleaned')])
)
    
semantic_search_ = SemanticSearch(default_configuration_name="semanticconfig", configurations= [semantic_config])
index_client.delete_index(name)
#print("index is deleted")
cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=60)
scoring_profiles = []
index = SearchIndex(
    name=name,
    fields=fields,
    vector_search = vector_search,
    semantic_search = semantic_search_
)

result = index_client.create_index(index)

index_client_upload = SearchClient("https://ai-search-rag-product-dev.search.windows.net",name,AzureKeyCredential(ai_search_key))
#print("index is created")
step_size = 500
for i in range(0, int(len(docs)/step_size) + 1):
    if (i+1)*step_size < len(docs):
        index_client_upload.upload_documents(docs[i*step_size:(i+1)*step_size])
    else:
        index_client_upload.upload_documents(docs[i*step_size:])  

#print("documents are uploaded")