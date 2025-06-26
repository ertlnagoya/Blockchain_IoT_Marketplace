# use alpine image for use build target x86_64-unknown-linux-musl as default
FROM rust:1-bullseye

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt
