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

# Build the production bundle
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
