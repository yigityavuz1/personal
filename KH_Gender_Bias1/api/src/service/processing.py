import nltk
import re
import datetime
import pytz

import pandas as pd

import src.schemas as _schemas
from src import constants

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


async def preprocess(raw_text: str) -> list:
    # Keep only alphanumeric characters, whitespace and some special characters that can appear in job postings
    pattern = r'[^a-zA-ZışçöüğŞÇÖÜĞİ0-9-/().,:;%&<>#\s]'
    cleaned_text = re.sub(pattern, '', raw_text)
    sentences = cleaned_text.split('\n')
    sentences = [nltk.sent_tokenize(sent) for sent in sentences]
    sentences = [item for sublist in sentences for item in sublist]
    return sentences


def postprocess(biased_list: list, request_body: _schemas.GenderPredictInput) -> _schemas.GenderPredictOutput:
    response_schema = _schemas.CheckBiasOutput()
    response_schema.ILAN_ID = request_body.ILAN_ID
    response_schema.KULLANICI_ID = request_body.KULLANICI_ID
    df = pd.read_excel(constants.EXCEL_PATH)
    if biased_list:
        for biased_phrase in biased_list:
            biased_output = _schemas.DictBiasOutput()
            for k, v in biased_phrase.items():
                row = df.loc[df['Ayrımcı Dil İçeren Kelime'] == k]
                biased_output.AYRIMCI_IFADE = k
                biased_output.AYRIMCI_KISIM = v
                biased_output.AYRIMCI_IFADE_ONERI = row['Yerine Kullanılması Gereken Kelime'].values[0]
                biased_output.AYRIMCI_IFADE_KATEGORI = row['Ayrımcılık Grubu'].values[0]
                biased_output.AYRIMCI_IFADE_CINSIYET_BILGISI = row['Cinsiyet'].values[0]
                biased_output.AYRIMCI_IFADE_DERECESI = 1 if row['Ayrımcılık Derecesi'].values[
                                                                0].lower() == 'yüksek' else 0
                if biased_output.AYRIMCI_IFADE_CINSIYET_BILGISI == 'Erkek':
                    response_schema.AYRIMCI_IFADE_MASKULEN_ADET += 1
                elif biased_output.AYRIMCI_IFADE_CINSIYET_BILGISI == 'Kadın':
                    response_schema.AYRIMCI_IFADE_FEMINEN_ADET += 1
                response_schema.AYRIMCI_IFADELER.append(biased_output.model_copy())

    response_schema.HESAPLAMA_TARIHI = str(datetime.datetime.now(pytz.timezone('Europe/Istanbul')))

    return response_schema
