# ── Valor Assist Frontend — Multi-stage Docker build ─────────────────
# Stage 1: Build the React app with Vite
# Stage 2: Serve with nginx (lightweight, production-grade)

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
