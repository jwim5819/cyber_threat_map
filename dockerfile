FROM python:3.9-slim

WORKDIR /src

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN apt-get update && \
    apt-get install -y procps

CMD ["/src/start.sh"]