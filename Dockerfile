# syntax=docker/dockerfile:1.7
# AiGovOps Policy Foundry -- one container: API + dashboard + OPA. Multi-arch (amd64, arm64).
# Build:  docker build -t policy-foundry .        Run: docker run -p 8000:8000 policy-foundry

FROM node:22-bookworm-slim AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
COPY api/foundry/assets/parity /src/api/foundry/assets/parity
RUN npm run build

FROM python:3.14-slim-bookworm AS runtime
ARG TARGETARCH
ARG OPA_VERSION=1.21.1
ARG OPA_SHA256_AMD64=668506eb17a2eaa1fce6cc0d1f42ef85125d4ac5bda5fc74d1152d0c77145031
ARG OPA_SHA256_ARM64=9a1f3625529c6f01240fe68286dde06aa0b23c5253da700ac48f4d943ff8a4de
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    OPA_BIN=/usr/local/bin/opa FOUNDRY_WEB_DIST=/app/web
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
 && arch="${TARGETARCH:-amd64}" \
 && if [ "$arch" = "arm64" ]; then sum="$OPA_SHA256_ARM64"; else sum="$OPA_SHA256_AMD64"; fi \
 && curl -fsSL -o /usr/local/bin/opa "https://github.com/open-policy-agent/opa/releases/download/v${OPA_VERSION}/opa_linux_${arch}_static" \
 && echo "${sum}  /usr/local/bin/opa" | sha256sum -c - \
 && chmod 0755 /usr/local/bin/opa \
 && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY api/pyproject.toml api/README.md ./
COPY api/app ./app
COPY api/foundry ./foundry
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home foundry
COPY --from=web /src/web/dist /app/web
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=2).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
