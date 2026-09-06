# [Input] Root frontend pnpm workspace/lock, package/config/source tree, and runtime entrypoint.
# [Output] Build and serve the canonical standalone Next Web Shell on the existing container port.
# [Pos] Default frontend deployment image; the Vite rollback is a separately verified immutable image.
# [Sync] 2026-09-06: build the sole locked pnpm workspace and serve the root standalone Next project.

ARG PNPM_REGISTRY=https://registry.npmmirror.com
ARG NODE_BUILD_MAX_OLD_SPACE_MB=1024

FROM node:22-alpine AS builder
ARG PNPM_REGISTRY
ARG NODE_BUILD_MAX_OLD_SPACE_MB
ENV NODE_OPTIONS="--max-old-space-size=${NODE_BUILD_MAX_OLD_SPACE_MB}"

WORKDIR /app

RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/mcp-apps-runtime/package.json ./packages/mcp-apps-runtime/package.json
RUN pnpm config set registry "${PNPM_REGISTRY}" \
    && pnpm install --frozen-lockfile

COPY . .
RUN pnpm run build:docker

FROM node:22-alpine AS runner
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=80

WORKDIR /app

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
