FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        fonts-noto-cjk \
        libnss3 \
        libatk-bridge2.0-0 \
        libdrm2 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpango-1.0-0 \
        libcairo2 \
        libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir \
        openpyxl>=3.1.0 \
        playwright>=1.40.0 \
        pytest>=7.4.0 \
        pytest-cov>=4.1.0 \
        tqdm>=4.65.0 \
        psutil>=5.9.0 \
        requests>=2.31.0 \
        jsonschema>=4.20.0 \
        Appium-Python-Client>=3.0.0 \
    && playwright install chromium \
    && playwright install-deps chromium

COPY . /app/

COPY docker/config.docker.json /app/config/config.json

RUN mkdir -p /app/logs /app/screenshots /app/sandbox/cases /app/sandbox/results

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["idle"]
