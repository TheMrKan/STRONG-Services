FROM python:3.12-slim

WORKDIR /app
COPY . /app


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip
RUN pip install -r requirements.txt


RUN apt update && apt install git -y
RUN pip install git+https://github.com/TheMrKan/lava_api


RUN mkdir -p /app/logs/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]