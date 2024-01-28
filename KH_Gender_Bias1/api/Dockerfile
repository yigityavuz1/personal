# Builder Stage
FROM python:3.9 AS builder
 
WORKDIR /build
 
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
 
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
 
# Final Stage
FROM python:3.9-slim-bookworm
 
LABEL maintainer="zeynep.akant@ext.kocdigital.com" \
      version="1.0" \
      description="KD-KH-Ayrımcı-Dil"
 
WORKDIR /app
 
COPY --from=builder /opt/venv /opt/venv
 
# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"
COPY ./ ./

EXPOSE 80

CMD ["/opt/venv/bin/uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80", "--ssl-keyfile", "./ssl/kockariyerimkey_2024.pem", "--ssl-certfile", "./ssl/kockariyerimcert_2024.pem", "--ssl-keyfile-password", "Aa123456."]
