FROM python:3.11-slim

WORKDIR /app

COPY shared/ /shared/
RUN pip install --no-cache-dir /shared

COPY benchmark/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY benchmark/ .

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
