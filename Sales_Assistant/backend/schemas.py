from pydantic import BaseModel
from typing import Literal,List

class VoiceAssistantModel(BaseModel):
    VoiceOutput: str
    ActivityID: str

class CustomerInfoModel(BaseModel):
    CustomerID: str
    CustomerEMail: str

class BasketItemsModel(BaseModel):
    ItemKey: str
    ItemName: str
    ItemQuantity: int
    ItemUnit: Literal['adet','koli','paket']
    EntryNumber: int

class SuggestionListModel(BaseModel):
    ItemKey: str
    SuggestionNumber: int    

class VoiceOutputModel(BaseModel):
    VoiceOutput: str
    VoiceUrl: str
    VoiceOutputMapped: str

class ProductSuggestionModel(BaseModel):
    ItemKey: str
    LineNumber: int

class RequestModel(BaseModel):
    ConversationID: str
    VoiceAssistant: VoiceAssistantModel
    BasketItems: list[BasketItemsModel]
    CustomerInfo: CustomerInfoModel
    SuggestionList: SuggestionListModel
    SearchTopN: int = 5

class ResponseModel(BaseModel):
    SessionID: str
    VoiceAssistant: VoiceOutputModel
    Function: Literal['basketupdate','basketdelete','basketinsert','ödemeyegeç','kampanyagösterme','listitems', '',"emptybasket","showbasket","restock_notification"]
    BasketFunctionParameters: BasketItemsModel
    ProductSuggestionList: List[ProductSuggestionModel]
    OptionList: List
    

class SimpleDataModel(BaseModel):
    session_id: str
    cart: str
    text: str
