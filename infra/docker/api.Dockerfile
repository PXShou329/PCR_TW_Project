FROM python:3.13.14-slim-bookworm AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements.txt ./requirements.txt
RUN python -m pip wheel --wheel-dir /wheels --requirement requirements.txt

FROM python:3.13.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api:/app/data_pipeline:/app/database

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /nonexistent --shell /usr/sbin/nologin app
COPY --from=build /wheels /wheels
COPY requirements.txt /requirements.txt
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels --requirement /requirements.txt \
    && rm -rf /wheels /requirements.txt

WORKDIR /app
COPY --chown=10001:10001 apps/api ./apps/api
COPY --chown=10001:10001 database ./database
COPY --chown=10001:10001 data_pipeline ./data_pipeline
COPY --chown=10001:10001 research_core ./research_core
COPY --chown=10001:10001 scripts/check_research_baseline.py ./scripts/check_research_baseline.py
COPY --chown=10001:10001 scripts/research_core_rp_a2_manifest.sha256 ./scripts/research_core_rp_a2_manifest.sha256
COPY --chown=10001:10001 scripts/research_core_rp_a3_manifest.sha256 ./scripts/research_core_rp_a3_manifest.sha256
COPY --chown=10001:10001 scripts/research_core_rp_a4_manifest.sha256 ./scripts/research_core_rp_a4_manifest.sha256
COPY --chown=10001:10001 scripts/research_core_rp_a5_manifest.sha256 ./scripts/research_core_rp_a5_manifest.sha256
COPY --chown=10001:10001 scripts/research_core_rp_b5_1_manifest.sha256 ./scripts/research_core_rp_b5_1_manifest.sha256
COPY --chown=10001:10001 scripts/research_core_rp_a6_0_manifest.sha256 ./scripts/research_core_rp_a6_0_manifest.sha256

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "pcr_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
