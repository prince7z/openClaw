FROM nikolaik/python-nodejs:python3.11-nodejs20

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    lsof \
    psmisc \
 && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir uv

RUN corepack enable

WORKDIR /workspace