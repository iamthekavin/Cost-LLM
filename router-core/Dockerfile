FROM python:3.11-slim

WORKDIR /app

COPY shared/ /shared/
RUN pip install --no-cache-dir /shared

COPY router-core/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY router-core/ .

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
