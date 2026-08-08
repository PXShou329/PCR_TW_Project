FROM python:3.13.14-slim-bookworm AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY apps/scheduler/pyproject.toml ./apps/scheduler/pyproject.toml
COPY apps/scheduler/src ./apps/scheduler/src
RUN python -m pip wheel --wheel-dir /wheels ./apps/scheduler

FROM python:3.13.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SCHEDULER_ENABLED=false \
    SHADOW_MODE=true \
    AUTO_PUBLISH=false

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /nonexistent --shell /usr/sbin/nologin app
COPY --from=build /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/* && rm -rf /wheels

USER 10001:10001
EXPOSE 8081
ENTRYPOINT ["pcr-scheduler"]
