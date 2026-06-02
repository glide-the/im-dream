# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

# ── Stage 2: serve ──────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Custom entrypoint: runs envsubst with *only* ${BACKEND_URL} so nginx
# runtime variables ($host, $proxy_host, etc.) are not accidentally replaced.
COPY nginx.conf.template /etc/nginx/templates/ink.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY --from=builder /app/dist /usr/share/nginx/html/ink-and-memory

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
