FROM node:24-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24-alpine AS builder
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
ARG VITE_BUNNY_OPTIMIZER_ENABLED=false
ENV VITE_BUNNY_OPTIMIZER_ENABLED=$VITE_BUNNY_OPTIMIZER_ENABLED
RUN npm run build

FROM nginx:1.29-alpine AS production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD wget -q --spider http://127.0.0.1:3000/ || exit 1
