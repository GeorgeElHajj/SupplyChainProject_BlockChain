# React Frontend Dockerfile
FROM node:18-slim as build

WORKDIR /app

# Disable Rollup native binaries (fixes the error)
ENV ROLLUP_SKIP_NODE_NATIVE=true

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
