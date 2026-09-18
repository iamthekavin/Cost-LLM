FROM python:3.11-slim

WORKDIR /app

COPY shared/ /shared/
RUN pip install --no-cache-dir /shared

COPY control-plane/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY control-plane/ .

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
