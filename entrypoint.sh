#!/bin/sh

PORT=${PORT:-8080}
SERVICE_TYPE=${SERVICE_TYPE:-fastapi}

if [ "$SERVICE_TYPE" = "streamlit" ]; then
  echo "Starting Streamlit on port $PORT"
  exec streamlit run app.py \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.headless true
else
  echo "Starting FastAPI on port $PORT"
  exec uvicorn services.fastapi.api:app \
    --host 0.0.0.0 \
    --port "$PORT"
fi

