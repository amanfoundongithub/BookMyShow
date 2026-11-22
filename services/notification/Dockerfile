FROM python:3.12-slim

WORKDIR /app

COPY libs/common /app/libs/common
RUN pip install --no-cache-dir /app/libs/common

COPY services/notification/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/notification/app /app/app

EXPOSE 8004

CMD ["python", "-m", "app.worker"]