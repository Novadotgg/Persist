FROM node:22-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.25-alpine as runner

COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration if needed, otherwise default config works
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
