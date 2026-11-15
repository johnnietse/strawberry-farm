FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-forecast.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# FORECAST=0 skips torch and Chronos (smaller image; the forecast falls back to persistence)
ARG FORECAST=1
RUN if [ "$FORECAST" = "1" ]; then \
      pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-forecast.txt; \
    fi

# plant model, controller, biology engine and the trained policy (models/led_policy.npz)
COPY . .

CMD ["python", "controller.py"]
