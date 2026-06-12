# [Input] Consume frontend package.json/source tree, nginx template, and runtime entrypoint.
# [Output] Build the Vite SPA and serve it under /ink-and-memory/ with nginx.
# [Pos] deployment image spec in frontend/
# [Sync] 2026-06-12: add configurable npm mirror build arg for faster China builds.

ARG NPM_REGISTRY=https://registry.npmmirror.com

# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM node:22-alpine AS builder
ARG NPM_REGISTRY

WORKDIR /app

COPY package.json ./
RUN npm config set registry "${NPM_REGISTRY}" \
    && npm install

COPY . .
RUN npm run build

# ── Stage 2: serve ──────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Custom entrypoint renders nginx proxy fallback and browser runtime API config.
COPY nginx.conf.template /etc/nginx/templates/ink.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY --from=builder /app/dist /usr/share/nginx/html/ink-and-memory

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
