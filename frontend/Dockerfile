# [Input] Consume frontend package.json/source tree, nginx template, and runtime entrypoint.
# [Output] Build the Vite SPA and serve it at the nginx root.
# [Pos] deployment image spec in frontend/
# [Sync] 2026-06-12: add configurable npm mirror build arg for faster China builds.
# [Sync] 2026-06-14: pass VITE_PUBLIC_SITE_URL into Vite build for static SEO metadata.
# [Sync] 2026-06-15: remove /ink-and-memory/ deployment prefix; copy build output to nginx root.

ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG VITE_PUBLIC_SITE_URL=http://localhost/

# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM node:22-alpine AS builder
ARG NPM_REGISTRY
ARG VITE_PUBLIC_SITE_URL
ENV VITE_PUBLIC_SITE_URL="${VITE_PUBLIC_SITE_URL}"

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

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
