import json
from langchain_core.tools import BaseTool
from langchain_core.messages.ai import AIMessage
from typing import (
    Any,
    Dict,
    Optional
)
from typing_extensions import get_args

from .states import InjectedState
from .schemas import ResponseModel, VoiceAssistantModel, BasketItemsModel, CustomerInfoModel, SuggestionListModel, RequestModel, VoiceOutputModel, ProductSuggestionModel
import logging
from configparser import ConfigParser
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta


def get_sas_url_for_file(blob_name,config):
    # config = ConfigParser()
    # config.read(config_path)
    connection_string = config.get('azure_storage', 'connection_string')
    container_name = config.get('azure_storage', 'container_static_assistant', fallback='default_container')
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    container_name = config.get('azure_storage', 'container_static_assistant', fallback='default_container')
    try:
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now() + timedelta(minutes=5)
        )
        sas_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
        logging.info(f"Generated SAS URL for blob: {blob_name}")
        return sas_url
    except Exception as e:
        logging.error(f"Failed to generate SAS URL for blob {blob_name}: {e}")
        return None
def _get_state_args(tool: BaseTool) -> Dict[str, Optional[str]]:
    full_schema = tool.get_input_schema()
    tool_args_to_state_fields: Dict = {}
    for name, type_ in full_schema.__annotations__.items():
        injections = [
            type_arg
            for type_arg in get_args(type_)
            if isinstance(type_arg, InjectedState)
            or (isinstance(type_arg, type) and issubclass(type_arg, InjectedState))
        ]
        if len(injections) > 1:
            raise ValueError(
                "A tool argument should not be annotated with InjectedState more than "
                f"once. Received arg {name} with annotations {injections}."
            )
        elif len(injections) == 1:
            injection = injections[0]
            if isinstance(injection, InjectedState) and injection.field:
                tool_args_to_state_fields[name] = injection.field
            else:
                tool_args_to_state_fields[name] = None
        else:
            pass
    return tool_args_to_state_fields


def str_output(output: Any) -> str:
    if isinstance(output, str):
        return output
    else:
        try:
            return json.dumps(output)
        except Exception:
            return str(output)
        
class LanguageAwareStr(str):
    lang = None
class TurkishStr(LanguageAwareStr):
    lang = 'tr'

    _case_lookup_upper = {'İ': 'i', 'I': 'ı'}  # lookup uppercase letters
    _case_lookup_lower = {v: k for (k, v) in _case_lookup_upper.items()}

    # here we override the lower() and upper() methods
    def lower(self):
        chars = [self._case_lookup_upper.get(c, c) for c in self]
        result = ''.join(chars).lower()
        cls = type(self)  # so we return a TurkishStr result
        return cls(result)

    def upper(self):
        chars = [self._case_lookup_lower.get(c, c) for c in self]
        result = ''.join(chars).upper()
        cls = type(self)  # so we return a TurkishStr result
        return cls(result)
    
def entity_output_parser(llm_output):
    '''
    Parse the output of the entity extraction model. Output will be string in JSON format.
    '''
    entity = json.loads(llm_output)
    return entity[0]

def output_creator(cart, result,session_id,voice_config):
    '''
    Create the output of the agent. Output will be string in JSON format.
    '''
    if isinstance(result['messages'][0], AIMessage):
        VoiceAssistantData = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl="",VoiceOutputMapped="")
        FunctionData = ""
        BasketFunctionParametersData = BasketItemsModel(ItemKey="", ItemName="", ItemQuantity=0, ItemUnit="adet", EntryNumber=0)
        ProductSuggestionListData = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
        OptionListData = []
        Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistantData, Function=FunctionData, BasketFunctionParameters=BasketFunctionParametersData, ProductSuggestionList=ProductSuggestionListData, OptionList=OptionListData)
        return Output
    else:
        try:
            try:
                if result['messages'][0].artifact['voice_name']:
                    voiceurl = get_sas_url_for_file(result['messages'][0].artifact['voice_name'] + '.wav',voice_config)
                else:
                    voiceurl = ""
            except:
                voiceurl = ""
                    
            if result['messages'][0].name == "add_new_product_to_cart":
                if result['messages'][0].artifact['condition'] == 1:
                    VoiceAssistantData = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                    FunctionData = "basketinsert"
                    BasketFunctionParametersData = BasketItemsModel(ItemKey=result['messages'][0].artifact['product_id'], 
                                                                ItemName="", 
                                                                ItemQuantity=result['messages'][0].artifact['quantity'], 
                                                                ItemUnit=result['messages'][0].artifact['unit'], 
                                                                EntryNumber=1)
                    ProductSuggestionListData = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                    OptionListData = []
                    Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistantData, Function=FunctionData, BasketFunctionParameters=BasketFunctionParametersData, ProductSuggestionList=ProductSuggestionListData, OptionList=OptionListData)
                    return Output
                else:
                    VoiceAssistantData = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                    FunctionData = ""
                    BasketFunctionParametersData = BasketItemsModel(ItemKey="", 
                                                                ItemName="", 
                                                                ItemQuantity=-1, 
                                                                ItemUnit="adet", 
                                                                EntryNumber=0)
                    ProductSuggestionListData = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                    OptionListData = []
                    Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistantData, Function=FunctionData, BasketFunctionParameters=BasketFunctionParametersData, ProductSuggestionList=ProductSuggestionListData, OptionList=OptionListData)
                    return Output
            elif result['messages'][0].name == "remove_product_from_cart":
                VoiceAssistant = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                Function = "basketupdate"
                BasketFunctionParameters = BasketItemsModel(ItemKey=result['messages'][0].artifact['product_id'], 
                                                            ItemName="", 
                                                            ItemQuantity=0,
                                                            ItemUnit=result['messages'][0].artifact['unit'], 
                                                            EntryNumber=0)
                ProductSuggestionList = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                OptionList = []
                Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistant, Function=Function, BasketFunctionParameters=BasketFunctionParameters, ProductSuggestionList=ProductSuggestionList, OptionList=OptionList)
                return Output
            elif result['messages'][0].name == "create_restock_notification_request":
                VoiceAssistant = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                Function = "restock_notification"
                BasketFunctionParameters = BasketItemsModel(ItemKey=result['messages'][0].artifact['product_id'], 
                                                            ItemName="", 
                                                            ItemQuantity=result['messages'][0].artifact['quantity'],
                                                            ItemUnit="adet", 
                                                            EntryNumber=0)
                ProductSuggestionList = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                OptionList = []
                Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistant, Function=Function, BasketFunctionParameters=BasketFunctionParameters, ProductSuggestionList=ProductSuggestionList, OptionList=OptionList)
                return Output
            elif result['messages'][0].name == "change_quantity_in_cart":
                if result['messages'][0].artifact['sub_condition'] in ['no_product','same_quantity','reduce_fail']:
                    VoiceAssistantData = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                    FunctionData = ""
                    BasketFunctionParametersData = BasketItemsModel(ItemKey="", 
                                                                ItemName="", 
                                                                ItemQuantity=-1, 
                                                                ItemUnit="adet", 
                                                                EntryNumber=0)
                    ProductSuggestionListData = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                    OptionListData = []
                    Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistantData, Function=FunctionData, BasketFunctionParameters=BasketFunctionParametersData, ProductSuggestionList=ProductSuggestionListData, OptionList=OptionListData)
                    return Output
                if result['messages'][0].artifact['sub_condition'] == 'reduce_success':
                    VoiceAssistantData = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                    FunctionData = "basketupdate"
                    BasketFunctionParametersData = BasketItemsModel(ItemKey=result['messages'][0].artifact['product_id'], 
                                                                ItemName="", 
                                                                ItemQuantity=result['messages'][0].artifact['quantity'], 
                                                                ItemUnit=result['messages'][0].artifact['unit'], 
                                                                EntryNumber=0)
                    ProductSuggestionListData = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                    OptionListData = []
                    Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistantData, Function=FunctionData, BasketFunctionParameters=BasketFunctionParametersData, ProductSuggestionList=ProductSuggestionListData, OptionList=OptionListData)
                    return Output
                else:
                    VoiceAssistant = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                    Function = "basketupdate"
                    BasketFunctionParameters = BasketItemsModel(ItemKey=result['messages'][0].artifact['product_id'], 
                                                                ItemName="", 
                                                                ItemQuantity=0,
                                                                ItemUnit=result['messages'][0].artifact['unit'], 
                                                                EntryNumber=0)
                    ProductSuggestionList = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                    OptionList = []
                    Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistant, Function=Function, BasketFunctionParameters=BasketFunctionParameters, ProductSuggestionList=ProductSuggestionList, OptionList=OptionList)
                    return Output     
            elif result['messages'][0].name == "get_cart_details":
                VoiceAssistant = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                Function = "showbasket"
                BasketFunctionParameters = BasketItemsModel(ItemKey=result['messages'][0].artifact['product_id'], 
                                                            ItemName="", 
                                                            ItemQuantity=0,
                                                            ItemUnit=result['messages'][0].artifact['unit'], 
                                                            EntryNumber=0)
                ProductSuggestionList = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                OptionList = []
                Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistant, Function=Function, BasketFunctionParameters=BasketFunctionParameters, ProductSuggestionList=ProductSuggestionList, OptionList=OptionList)
                return Output               
            elif result['messages'][0].name == "empty_cart":
                VoiceAssistant = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                Function = "emptybasket"
                BasketFunctionParameters = BasketItemsModel(ItemKey="", ItemName="", ItemQuantity=-1, ItemUnit="adet", EntryNumber=0)
                ProductSuggestionList = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                OptionList = []
                Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistant, Function=Function, BasketFunctionParameters=BasketFunctionParameters, ProductSuggestionList=ProductSuggestionList, OptionList=OptionList)
                return Output
            elif result['messages'][0].name == "redirect_to_payment":
                VoiceAssistant = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                Function = "ödemeyegeç"
                BasketFunctionParameters = BasketItemsModel(ItemKey="", ItemName="", ItemQuantity=-1, ItemUnit="adet", EntryNumber=0)
                ProductSuggestionList = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                OptionList = []
                Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistant, Function=Function, BasketFunctionParameters=BasketFunctionParameters, ProductSuggestionList=ProductSuggestionList, OptionList=OptionList)

            elif result['messages'][0].name == "continue_shopping":
                VoiceAssistant = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                Function = "continueshopping"
                BasketFunctionParameters = BasketItemsModel(ItemKey="", ItemName="", ItemQuantity=-1, ItemUnit="adet", EntryNumber=0)
                ProductSuggestionList = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                OptionList = []
                Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistant, Function=Function, BasketFunctionParameters=BasketFunctionParameters, ProductSuggestionList=ProductSuggestionList, OptionList=OptionList)           
            elif result['messages'][0].name == "get_product_related_campaigns":
                return {"cart": cart, "messages": result['messages'][0].content, "product_id": result['messages'][0].artifact['product_id']}

            elif result['messages'][0].name == "retrieve_product_list":
                if result['messages'][0].artifact['sub_condition'] == "no_match":
                    VoiceAssistant = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped=result['messages'][0].artifact['mapped_output'])
                    Function = "listitems"
                    BasketFunctionParameters = BasketItemsModel(ItemKey="", ItemName="", ItemQuantity=-1, ItemUnit="adet", EntryNumber=0)
                    ProductSuggestionList = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                    OptionList = []
                    Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistant, Function=Function, BasketFunctionParameters=BasketFunctionParameters, ProductSuggestionList=ProductSuggestionList, OptionList=OptionList)
                elif result['messages'][0].artifact['sub_condition'] in ["direct_match_wout_quantity", "direct_match_with_quantity"]:
                    VoiceAssistant = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped=result['messages'][0].artifact['mapped_output'])
                    Function = "listitems"
                    BasketFunctionParameters = BasketItemsModel(ItemKey="", ItemName="", ItemQuantity=-1, ItemUnit="adet", EntryNumber=0)
                    ProductSuggestionList = [ProductSuggestionModel(ItemKey=result['messages'][0].artifact['product_id'], LineNumber=0)]
                    OptionList = []
                    Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistant, Function=Function, BasketFunctionParameters=BasketFunctionParameters, ProductSuggestionList=ProductSuggestionList, OptionList=OptionList)        
                    
                else:
                    VoiceAssistant = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped=result['messages'][0].artifact['mapped_output'])
                    Function = "listitems"
                    BasketFunctionParameters = BasketItemsModel(ItemKey="", ItemName="", ItemQuantity=-1, ItemUnit="adet", EntryNumber=0)
                    ProductSuggestionList = [ProductSuggestionModel(ItemKey=a, LineNumber=b) for a,b in result['messages'][0].artifact['product_suggestion']]
                    OptionList = []
                    Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistant, Function=Function, BasketFunctionParameters=BasketFunctionParameters, ProductSuggestionList=ProductSuggestionList, OptionList=OptionList)            
                    
            else:
                VoiceAssistantData = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
                FunctionData = ""
                BasketFunctionParametersData = BasketItemsModel(ItemKey="", ItemName="", ItemQuantity=-1, ItemUnit="adet", EntryNumber=0)
                ProductSuggestionListData = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
                OptionListData = []
                Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistantData, Function=FunctionData, BasketFunctionParameters=BasketFunctionParametersData, ProductSuggestionList=ProductSuggestionListData, OptionList=OptionListData)
                        
        except:
            VoiceAssistantData = VoiceOutputModel(VoiceOutput=TurkishStr(result['messages'][0].content), VoiceUrl=voiceurl,VoiceOutputMapped="")
            FunctionData = ""
            BasketFunctionParametersData = BasketItemsModel(ItemKey="", ItemName="", ItemQuantity=-1, ItemUnit="adet", EntryNumber=0)
            ProductSuggestionListData = [ProductSuggestionModel(ItemKey="", LineNumber=0)]
            OptionListData = []
            Output = ResponseModel(SessionID=session_id, VoiceAssistant=VoiceAssistantData, Function=FunctionData, BasketFunctionParameters=BasketFunctionParametersData, ProductSuggestionList=ProductSuggestionListData, OptionList=OptionListData)
    return Output
    
def kontrol_ve_degistir(metin):  
    kelimeler = {"rixy istiyorum": "rixy marka ürün istiyorum" ,
                 "popçik istiyorum": "popçik marka ürün istiyorum"
                 # Eklemek istediğiniz diğer cümle ve değişiklikleri buraya ekleyebilirsiniz  
                }  
      
    for kelime, yeni_kelime in kelimeler.items():  
        if kelime in metin:  
            metin = metin.replace(kelime, yeni_kelime)  
      
    return metin  