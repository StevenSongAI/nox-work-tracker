FROM node:18-alpine

WORKDIR /app

# Cache bust: 2026-02-14-23-30
COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
