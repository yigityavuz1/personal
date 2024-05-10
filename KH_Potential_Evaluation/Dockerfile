# Builder Stage
FROM python:3.9 AS builder

WORKDIR /build

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org pypi.python.org" && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Final Stage
FROM python:3.9-slim-bookworm

LABEL maintainer="muhammed.cansiz@kocdigital.com" \
      version="1.0" \
      description="KD-KH-Pre-Assessment"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"
COPY ./ ./

EXPOSE 80

CMD ["/opt/venv/bin/uvicorn", "app:app", "--host", "0.0.0.0","--port", "80"]