# Dockerfile for the FRONTEND service.
#
# Why a Dockerfile:
#  - Railway's nixpacks Node default is v18, but Next.js 16 needs Node 20+
#  - The build cache layer hits EBUSY trying to rmdir node_modules/.cache
#  - Dockerfile sidesteps both issues
#
# NEXT_PUBLIC_API_URL is needed at BUILD time (Next.js bakes it into the
# JS bundle). Railway exposes service env vars to Docker builds as ARGs.

FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY . .

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

CMD ["sh", "-c", "npm run start -- --hostname 0.0.0.0 --port ${PORT:-3000}"]
