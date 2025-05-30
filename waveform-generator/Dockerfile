FROM node:18-slim

RUN apt-get update && apt-get install -y \
    chromium \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libasound2 \
    libxshmfence-dev \
    libxfixes-dev \
    libxrandr2 \
    libxcomposite1 \
    libpangocairo-1.0-0 \
    libgbm-dev \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY package*.json ./
# Install all dependencies, including devDependencies if puppeteer is there
RUN npm install 

COPY . .

ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
# Make script executable if needed, though node will run it
# RUN chmod +x generate-waveform.js 

# Default command can be empty if script is called with arguments
# CMD [ "node", "generate-waveform.js" ]
ENTRYPOINT [ "node", "generate-waveform.js" ]
