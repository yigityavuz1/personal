import requests

params = {
    "ILAN_ID": "96B889AE-CFDC-497B-920A-970FF861C6D4",
    "KULLANICI_ID": "48D689C9-7A92-436D-3D48-08D9DAD35B22",
    "ROL_SORUMLULUK_BASLIK": "Bu sorumluklar için “Mutlulukla BendeO!”  diyorsan;",
    "ROL_SORUMLULUK_METIN": """Satış hedeflerine paralel olarak sorumlu olunan satış operasyonunun etkin şekilde yürütülmesine destek olmak, "
                            Satış listelerinin hazırlanması ve ilgili yöneticilere raporlamak, 
                            Müşterilerin ihtiyaçlarını anlayıp uygun dağıtım modellerini önermek,
                            Satış sonrası ihtiyaçlarının karşılamak, 
                            Sorumlu olduğu satış bölgesinde faaliyet gösteren birimlere satış & müşteri ilişkileri konusunda destek olmak.""",
    "ARANILAN_NITELIKLER_BASLIK": "Aranılan Nitelikler",
    "ARANILAN_NITELIKLER_METIN": """Üniversitelerin ilgili bölümlerinden mezun, 
    Sektör deneyimli olan, Takım çalışmasına yatkın, 
    İletişim becerilerinde güçlü, 
    Problem çözme ve karar verme becerisinde yüksek, 
    Müşteri/piyasa analizlerinde dikkatli, 
    Şirket hedef ve vizyonuna uygun hareket edebilen, 
    Seyahat engeli olmayan, 
    MS Office uygulamalarını etkin kullanabilen""",
    "ILETILME_TARIH": "2023-10-10 09:05:45.7095874"
}

gender_params = {
    "BASVURU_ID": "51D8C7A1-6BCE-4E9A-E2D7-08DBC94B4A21",
    "BASVURAN_AD": "İhsan Berk"
}

# Check bias
response = requests.post('https://localhost:80/check_bias/', json=params)
# Predict gender
# response = requests.post('http://localhost:5000/predict_gender/', json=gender_params)

print(response.json())
