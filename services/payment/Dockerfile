FROM python:3.12-slim

WORKDIR /app

COPY libs/common /app/libs/common
RUN pip install --no-cache-dir /app/libs/common

COPY services/payment/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/payment/app /app/app

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]