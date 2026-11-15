FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

# Cloudflare Containers requires a linux/amd64 image. FUSE is used to keep
# SFW's project library in Cloudflare R2 instead of ephemeral container disk.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl fuse3 util-linux tar \
    && rm -rf /var/lib/apt/lists/*

ARG TIGRISFS_VERSION=1.2.1
RUN curl -fL "https://github.com/tigrisdata/tigrisfs/releases/download/v${TIGRISFS_VERSION}/tigrisfs_${TIGRISFS_VERSION}_linux_amd64.tar.gz" \
      -o /tmp/tigrisfs.tar.gz \
    && tar -xzf /tmp/tigrisfs.tar.gz -C /usr/local/bin/ \
    && rm /tmp/tigrisfs.tar.gz \
    && chmod +x /usr/local/bin/tigrisfs

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY cloudflare/start.sh /usr/local/bin/sfw-start

EXPOSE 8501
CMD ["sh", "/usr/local/bin/sfw-start"]
