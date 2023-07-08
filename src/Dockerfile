FROM python:3.7.7-slim-buster

RUN  apt-get update && \
  apt-get install -y --no-install-recommends wget git default-mysql-client && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python3 -m spacy download en_core_web_sm

COPY . .

ENTRYPOINT [ "python", "-u", "mining.py" ]
