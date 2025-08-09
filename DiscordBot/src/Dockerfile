FROM python:3.12-slim

WORKDIR /app
COPY . /app/src

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/src

RUN pip install --upgrade pip
RUN pip install -r src/requirements.txt
