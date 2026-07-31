# Stage 1: Build & Development environment
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Dev stage (runs dev server with hot reload)
FROM builder AS dev
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# Production build stage
FROM builder AS prod-builder
RUN npm run build

# Production serve stage using Nginx
FROM nginx:1.25-alpine AS prod
COPY --from=prod-builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
