FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY api_keys.py ./
COPY opet_faiss_0213/ opet_faiss_0213/

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
