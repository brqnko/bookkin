FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git openssh-client ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy

WORKDIR /workspace

CMD ["sleep", "infinity"]
