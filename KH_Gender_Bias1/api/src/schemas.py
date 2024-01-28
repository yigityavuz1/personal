import pydantic as _pydantic
from typing import List


class CheckBiasInput(_pydantic.BaseModel):
    ILAN_ID: str
    KULLANICI_ID: str
    ROL_SORUMLULUK_BASLIK: str
    ROL_SORUMLULUK_METIN: str
    ARANILAN_NITELIKLER_BASLIK: str
    ARANILAN_NITELIKLER_METIN: str
    ILETILME_TARIH: str


class GenderPredictInput(_pydantic.BaseModel):
    BASVURU_ID: str
    BASVURAN_AD: str


class DictBiasOutput(_pydantic.BaseModel):
    AYRIMCI_KISIM: str = None
    AYRIMCI_IFADE: str = None
    AYRIMCI_IFADE_ONERI: str = None
    AYRIMCI_IFADE_KATEGORI: str = None
    AYRIMCI_IFADE_CINSIYET_BILGISI: str = None
    AYRIMCI_IFADE_DERECESI: int = None


class CheckBiasOutput(_pydantic.BaseModel):
    ILAN_ID: str = None
    KULLANICI_ID: str = None
    AYRIMCI_IFADELER: List[DictBiasOutput] = []
    AYRIMCI_IFADE_MASKULEN_ADET: int = 0
    AYRIMCI_IFADE_FEMINEN_ADET: int = 0
    HESAPLAMA_TARIHI: str = None


class GenderPredictOutput(_pydantic.BaseModel):
    BASVURU_ID: str = None
    BASVURAN_AD: str = None
    CINSIYET: str = None
    ORAN: float = 0.0
