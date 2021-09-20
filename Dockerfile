FROM python:3
ENV PYTHONUNBUFFERED 1
WORKDIR /home

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y iputils-ping openssh-client nano

COPY ./ajax ./ajax
COPY ./find_desc ./find_desc
COPY ./find_description_web ./find_description_web
COPY ./templates ./templates
COPY ./static ./static
COPY ./config .
COPY ./manage.py .
COPY ./requirements.txt .
COPY ./db.sqlite3 .