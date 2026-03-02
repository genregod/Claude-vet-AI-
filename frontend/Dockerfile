# ── Valor Assist Frontend — Multi-stage Docker build ─────────────────
# Stage 1: Build the React + TypeScript app with Vite
# Stage 2: Serve with nginx (lightweight, production-grade)

FROM node:20-alpine AS build
WORKDIR /app

# Copy config files first for better caching
COPY package*.json ./
COPY tsconfig*.json ./
COPY vite.config.js ./
COPY tailwind.config.ts ./
COPY postcss.config.js ./
COPY components.json ./

# Install all dependencies (including dev dependencies for build)
RUN npm install

# Copy source code
COPY index.html ./
COPY src/ ./src/

# Optional API origin for deployed frontend (e.g., https://api.example.com)
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Build the production bundle
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
EXPOSE 80

# Default backend URL for docker-compose local development
ENV BACKEND_URL=backend:8000

# At runtime, substitute BACKEND_URL in the template (leaving nginx vars intact),
# then start nginx
CMD ["/bin/sh", "-c", "envsubst '${BACKEND_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
