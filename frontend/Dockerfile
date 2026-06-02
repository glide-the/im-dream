# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --frozen-lockfile

COPY . .
RUN npm run build

# ── Stage 2: serve ──────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# nginx's built-in template engine: files in /etc/nginx/templates/*.template
# are processed with envsubst at container startup and written to
# /etc/nginx/conf.d/ with the .template suffix removed.
COPY nginx.conf.template /etc/nginx/templates/ink.conf.template

COPY --from=builder /app/dist /usr/share/nginx/html/ink-and-memory

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
