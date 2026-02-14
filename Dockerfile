FROM node:18-alpine

WORKDIR /app

# Cache bust: 2026-02-14-23-45
COPY . .

# Debug: List files
RUN ls -la /app/

EXPOSE 3000

CMD ["node", "server.js"]