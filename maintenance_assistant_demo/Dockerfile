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

LABEL maintainer="ahmet.kutlu@kocdigital.com" \
      version="1.0" \
      description="KD-Maintenance-Assistant"


# 
WORKDIR /code

RUN apt-get update
RUN apt-get install -y curl gnupg
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl -sSL https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql17

COPY --from=builder /opt/venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# 
COPY ./ /code/

# 
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]