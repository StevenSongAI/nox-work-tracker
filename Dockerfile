FROM node:18-alpine

WORKDIR /app

# Copy all files
COPY . .

# Expose port
EXPOSE 3000

# Start the server
CMD ["node", "server.js"]
