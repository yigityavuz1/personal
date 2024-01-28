# Koc Kariyerim Discriminatory Language Detection Project

## Overview

This project aims to detect discriminatory language within job postings, providing a tool for HR professionals to ensure fair and inclusive job advertisements. The project utilizes OpenAI's GPT-4 and is implemented as a FastAPI application within a Docker container.

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started)

### Running the Application

1. Clone the repository:

   ```bash
   git clone https://azuredevops.kocsistem.com.tr/tfs/KocDigitalCollection/AI_Business_Solutions/_git/KH_Gender_Bias
   ```

2. Navigate to the `api` folder:

   ```bash
   cd api
   ```

3. Build and run the Docker container:

   ```bash
   docker-compose up --build
   ```

   This command will build the Docker image and start the FastAPI application.

### Sending Requests

To test the discriminatory language detection, you can use the provided `sample_request.py` script. Modify the script as needed for your specific input.

```bash
python sample_request.py
```

This script sends a request to the endpoint running inside the Docker container.

## API Documentation

### Endpoint

- Endpoint URL: `http://localhost:5000/check_bias`

### Request

- Method: `POST`
- Content-Type: `application/json`

Example Request Body:

```json
{
  "ILAN_ID": "96B889AE-CFDC-497B-920A-970FF861C6D4",
  "KULLANICI_ID": "48D689C9-7A92-436D-3D48-08D9DAD35B22",
  "ROL_SORUMLULUK_BASLIK": "Bu sorumluklar için “Mutlulukla BendeO!”  diyorsan;",
  "ROL_SORUMLULUK_METIN": "Satış hedeflerine paralel olarak sorumlu olunan satış operasyonunun etkin şekilde yürütülmesine destek olmak, Satış listelerinin hazırlanması ve ilgili yöneticilere raporlamak, Müşterilerin ihtiyaçlarını anlayıp uygun dağıtım modellerini önermek, Satış sonrası ihtiyaçlarının karşılamak, Sorumlu olduğu satış bölgesinde faaliyet gösteren birimlere satış & müşteri ilişkileri konusunda destek olmak.",
  "ARANILAN_NITELIKLER_BASLIK": "Aranılan Nitelikler",
  "ARANILAN_NITELIKLER_METIN": "Üniversitelerin ilgili bölümlerinden mezun, Sektör deneyimli olan, Takım çalışmasına yatkın, İletişim becerilerinde güçlü, Problem çözme ve karar verme becerisinde yüksek, Müşteri/piyasa analizlerinde dikkatli, Şirket hedef ve vizyonuna uygun hareket edebilen, Seyahat engeli olmayan, MS Office uygulamalarını etkin kullanabilen",
  "ILETILME_TARIH": "2023-11-18 17:31:45.350810+03:00"
}
```

### Response

The API will respond with a JSON object containing the result of the discriminatory language detection.

Example Response:

```json
{
  "ILAN_ID": "96B889AE-CFDC-497B-920A-970FF861C6D4",
  "KULLANICI_ID": "48D689C9-7A92-436D-3D48-08D9DAD35B22",
  "AYRIMCI_IFADELER": [
    {
      "AYRIMCI_KISIM": "İletişim becerilerinde güçlü",
      "AYRIMCI_IFADE": "güçlü",
      "AYRIMCI_IFADE_ONERI": "yetenekli",
      "AYRIMCI_IFADE_KATEGORI": "Cinsiyet",
      "AYRIMCI_IFADE_CINSIYET_BILGISI": "Erkek"
    },
    {
      "AYRIMCI_KISIM": "müşteri/piyasa analizlerinde dikkatli",
      "AYRIMCI_IFADE": "dikkatli",
      "AYRIMCI_IFADE_ONERI": "titiz",
      "AYRIMCI_IFADE_KATEGORI": "Cinsiyet",
      "AYRIMCI_IFADE_CINSIYET_BILGISI": "Kadın"
    },
    {
      "AYRIMCI_KISIM": "seyahat engeli olmayan",
      "AYRIMCI_IFADE": "seyahat engeli",
      "AYRIMCI_IFADE_ONERI": "seyahat edebilen",
      "AYRIMCI_IFADE_KATEGORI": "Beden",
      "AYRIMCI_IFADE_CINSIYET_BILGISI": "Nötr"
    }
  ],
  "AYRIMCI_IFADE_MASKULEN_ADET": 1,
  "AYRIMCI_IFADE_FEMINEN_ADET": 1,
  "HESAPLAMA_TARIHI": "2023-11-18 17:31:47.350810+03:00"
}
```