## Wavesurfer.js Integration Roadmap for thePodcaster

This document outlines the steps to integrate Wavesurfer.js into thePodcaster application, providing both frontend display and a path for backend/batch audio visualization.

### 1. Frontend Integration (Displaying Waveforms in the UI)

   a. **Include Wavesurfer.js Library:**
      - **Option 1 (CDN):** Add the following script tag to your main HTML file (e.g., `index.html` or relevant template):
        ```html
        <script src="https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.min.js"></script>
        <!-- Optional: Add plugins similarly, e.g., Spectrogram -->
        <script src="https://unpkg.com/wavesurfer.js@7/dist/plugins/spectrogram.min.js"></script>
        ```
      - **Option 2 (NPM/ESM):** If you have a JavaScript build process:
        ```bash
        npm install wavesurfer.js
        # or
        yarn add wavesurfer.js
        ```
        Then import in your JavaScript:
        ```javascript
        import WaveSurfer from 'wavesurfer.js';
        import SpectrogramPlugin from 'wavesurfer.js/dist/plugins/spectrogram.min.js'; // Example plugin
        ```

   b. **Add HTML Markup:**
      - In your HTML, create a container element where the waveform will be rendered:
        ```html
        <div id="waveform"></div>
        <!-- Optional: Add controls -->
        <button id="playPauseBtn">Play/Pause</button>
        ```

   c. **Initialize Wavesurfer.js:**
      - In your frontend JavaScript, initialize Wavesurfer.js:
        ```javascript
        document.addEventListener('DOMContentLoaded', function () {
          const wavesurfer = WaveSurfer.create({
            container: '#waveform',
            waveColor: 'rgb(200, 0, 200)',
            progressColor: 'rgb(100, 0, 100)',
            url: '/path/to/your/audiofile.mp3', // Replace with actual audio path
            // Optional: Add plugins
            // plugins: [
            //   SpectrogramPlugin.create({
            //     container: '#wave-spectrogram', // A separate div for spectrogram
            //     labels: true,
            //   }),
            // ],
          });

          wavesurfer.on('ready', function () {
            console.log('Waveform is ready!');
          });

          // Optional: Link to play/pause button
          const playPauseBtn = document.getElementById('playPauseBtn');
          if (playPauseBtn) {
            playPauseBtn.onclick = function () {
              wavesurfer.playPause();
            };
          }

          wavesurfer.on('play', () => { if(playPauseBtn) playPauseBtn.textContent = 'Pause'; });
          wavesurfer.on('pause', () => { if(playPauseBtn) playPauseBtn.textContent = 'Play'; });

        });
        ```
      - Ensure the audio URL is accessible by the frontend.

### 2. Backend/Batch Export (Generating Waveform Images/Videos)

   This is for generating visuals without a live browser session, useful for thumbnails or automated video clips. The recommended approach is using a headless browser like Puppeteer.

   a. **Setup a Node.js Helper Service/Script:**
      - Create a new directory for this service (e.g., `waveform-generator`).
      - Initialize a Node.js project: `npm init -y`
      - Install Puppeteer: `npm install puppeteer`

   b. **Create a Puppeteer Script (e.g., `generate-waveform.js`):**
      ```javascript
      const puppeteer = require('puppeteer');
      const fs = require('fs');

      async function generateWaveformImage(audioUrl, outputImagePath, options = {}) {
        const browser = await puppeteer.launch();
        const page = await browser.newPage();

        // Create a simple HTML page content with Wavesurfer.js
        // Note: audioUrl needs to be accessible by Puppeteer (e.g., local file path or public URL)
        const htmlContent = `
          <html>
            <head>
              <script src="https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.min.js"></script>
            </head>
            <body>
              <div id="waveform" style="width:1200px; height:300px;"></div>
              <script>
                const wavesurfer = WaveSurfer.create({
                  container: '#waveform',
                  waveColor: '${options.waveColor || 'violet'}',
                  progressColor: '${options.progressColor || 'purple'}',
                  url: '${audioUrl}',
                  width: 1200, // Explicit width for consistent image size
                  height: 300, // Explicit height
                  barWidth: ${options.barWidth || 2},
                  barGap: ${options.barGap || 1},
                  responsive: false, // Important for consistent sizing in headless
                });
                // Resolve a promise when wavesurfer is ready and rendered
                window.wavesurferReady = new Promise(resolve => wavesurfer.on('ready', resolve));
                // Resolve another promise when drawing is fully complete (after interaction or seek)
                window.wavesurferRendered = new Promise(resolve => wavesurfer.on('redraw', resolve));
              </script>
            </body>
          </html>
        `;

        await page.setContent(htmlContent, { waitUntil: 'networkidle0' });

        // Wait for Wavesurfer to be fully ready and drawn
        await page.evaluate(async () => {
            await window.wavesurferReady;
            // Potentially seek or interact if needed for specific rendering states
            // For a static image, 'ready' might be enough, but 'redraw' after initial draw is safer.
            // Calling wavesurfer.drawBuffer() explicitly ensures it's drawn.
            await new Promise(resolve => setTimeout(resolve, 500)); // Extra safety wait
        });
        
        const waveformElement = await page.$('#waveform');
        if (waveformElement) {
          await waveformElement.screenshot({ path: outputImagePath });
          console.log(`Waveform image saved to ${outputImagePath}`);
        } else {
          console.error('Waveform element not found.');
        }

        await browser.close();
      }

      // Example usage:
      // generateWaveformImage('file:///path/to/your/local/audio.mp3', 'waveform.png');
      // generateWaveformImage('https://www.example.com/audio.mp3', 'waveform.png');
      ```
      *Note:* The `exportImage()` function was part of Wavesurfer.js v6 and is planned for v7. Once available, it might offer a more direct way to get the image data than taking a screenshot of the div. The Puppeteer screenshot method is a reliable alternative.

   c. **Integration with thePodcaster Backend (e.g., Celery Task):**
      - Your existing Python backend (e.g., a Celery worker) would call this Node.js script.
      - This can be done via a shell command: `node /path/to/waveform-generator/generate-waveform.js --audioUrl <url_or_path> --output <output_path>`
      - Ensure the Node.js script is executable and has Node installed in the environment where it's called.

### 3. Docker Considerations

   a. **Frontend (Nginx):**
      - Wavesurfer.js (client-side library) will be served by your existing Nginx container that handles the static frontend. No major changes are needed here other than ensuring the JS/HTML files are in the right place.

   b. **Backend/Batch Export (Node.js/Puppeteer Service):**
      - If you implement the Node.js script for batch exports, it's best to containerize it.
      - Create a `Dockerfile` for the `waveform-generator`:
        ```dockerfile
        FROM node:18-slim

        # Install Puppeteer dependencies
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
        RUN npm install --only=production

        COPY . .

        # Set PUPPETEER_EXECUTABLE_PATH to the installed Chromium
        ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

        CMD [ "node", "generate-waveform.js" ]
        ```
      - Add this new service to your `docker-compose.yml`.
      - The Celery worker container might need access to call this Node service (e.g., via network or shared volume if passing file paths).

### 4. Customization and Advanced Features

   - **Styling:** Wavesurfer.js can be extensively styled using its options (waveColor, progressColor, etc.) or CSS variables if you prefer more dynamic theming.
   - **Plugins:** Explore plugins for Spectrograms, Timeline, Regions, Minimap, etc., as needed. Each plugin has its own initialization.
   - **Interactivity:** Refer to Wavesurfer.js documentation for its rich API to control playback, seek, zoom, and respond to events.

This roadmap provides a comprehensive guide to get started. Depending on the specific needs of thePodcaster, some steps might be prioritized or adjusted.
