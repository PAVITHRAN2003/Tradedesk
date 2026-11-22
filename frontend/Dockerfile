# Stage 1: build the React app. This stage has Node, which we need only to build.
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
RUN npm run build               # produces /app/dist (plain HTML, JS, CSS)

# Stage 2: the final image is just nginx plus the built files, with no Node or source code.
FROM nginx:1.27-alpine
ENV BACKEND_URL=http://backend:8000
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80