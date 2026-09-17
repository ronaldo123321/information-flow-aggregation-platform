FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV TZ=Asia/Shanghai
ENV PATH="/app/.venv/bin:$PATH"

RUN apt update && \
    apt install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y --no-install-recommends \
      python3.12 python3.12-venv python3.12-dev \
      ca-certificates curl build-essential && \
    rm -rf /usr/bin/python /usr/bin/python3 && \
    ln -s /usr/bin/python3.12 /usr/bin/python && \
    ln -s /usr/bin/python3.12 /usr/bin/python3 && \
    /usr/bin/python3.12 -m ensurepip --upgrade && \
    /usr/bin/python3.12 -m pip install --upgrade pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.txt && \
    /app/.venv/bin/pip install twitter-cli

COPY . /app

EXPOSE 8080

CMD ["/app/.venv/bin/python", "main.py"]
