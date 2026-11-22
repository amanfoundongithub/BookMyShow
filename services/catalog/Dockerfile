FROM python:3.12-slim

WORKDIR /app

COPY libs/common /app/libs/common
RUN pip install --no-cache-dir /app/libs/common

COPY services/catalog/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/catalog/app /app/app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]