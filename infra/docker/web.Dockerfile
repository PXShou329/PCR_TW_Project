FROM node:24.18.0-bookworm-slim AS dependencies

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/api-client/package.json ./packages/api-client/package.json
COPY packages/ui/package.json ./packages/ui/package.json
RUN npm ci --ignore-scripts

FROM dependencies AS build
COPY apps/web ./apps/web
COPY packages/api-client ./packages/api-client
COPY packages/ui ./packages/ui
RUN npm run build:web

FROM node:24.18.0-bookworm-slim AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /nonexistent --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build --chown=10001:10001 /app/apps/web/.next/standalone ./
COPY --from=build --chown=10001:10001 /app/apps/web/.next/static ./apps/web/.next/static

USER 10001:10001
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
