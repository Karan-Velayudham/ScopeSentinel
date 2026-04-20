FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy proxy code
COPY proxy.js ./

# Entrypoint wraps the command in the proxy
ENTRYPOINT ["node", "proxy.js"]
