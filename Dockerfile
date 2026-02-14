FROM node:18-alpine

WORKDIR /app

# Copy all files including data/ directory
COPY . .

# Install serve package globally
RUN npm install -g serve

# Expose port 3000
EXPOSE 3000

# Serve the app using npm start
CMD ["npm", "start"]
