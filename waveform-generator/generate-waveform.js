const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Simple command line argument parsing
const args = process.argv.slice(2).reduce((acc, arg) => {
  const [key, value] = arg.split('=');
  if (key && value) {
    acc[key.replace(/^--/, '')] = value;
  }
  return acc;
}, {});

const audioUrl = args.audioUrl;
const outputImagePath = args.outputImagePath;

if (!audioUrl || !outputImagePath) {
  console.error('Usage: node generate-waveform.js --audioUrl=<url_or_path> --outputImagePath=<path>');
  process.exit(1);
}

async function generateWaveformImage(audioUrl, outputImagePath, options = {}) {
  // Determine if audioUrl is a local file path
  const isLocalFile = !audioUrl.startsWith('http://') && !audioUrl.startsWith('https://');
  let pageUrl = audioUrl;
  if (isLocalFile) {
    // Puppeteer needs a file:// URL for local files
    pageUrl = 'file://' + path.resolve(audioUrl);
  }

  console.log(`Launching Puppeteer for audio: ${pageUrl} -> output: ${outputImagePath}`);

  const browser = await puppeteer.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage', // Often needed in Docker
      '--font-render-hinting=none' // May improve consistency
    ]
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720 });


  const htmlContent = `
    <html>
      <head>
        <style>body { margin: 0; }</style>
        <script src="https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.min.js"></script>
      </head>
      <body>
        <div id="waveform" style="width:1200px; height:300px; background-color: ${options.backgroundColor || 'transparent'};"></div>
        <script>
          const wavesurfer = WaveSurfer.create({
            container: '#waveform',
            waveColor: '${options.waveColor || 'violet'}',
            progressColor: '${options.progressColor || 'purple'}',
            url: '${pageUrl}', // Use the potentially modified pageUrl
            width: 1200,
            height: 300,
            barWidth: ${options.barWidth || 2},
            barGap: ${options.barGap || 1},
            responsive: false,
            backend: 'MediaElement', // Try MediaElement backend for broader compatibility in Puppeteer
          });
          window.wavesurferReady = new Promise(resolve => wavesurfer.on('ready', resolve));
          window.wavesurferError = new Promise((_, reject) => wavesurfer.on('error', reject));
          // If using exportImage in future, it would be:
          // wavesurfer.on('ready', async () => {
          //   const dataUrl = await wavesurfer.exportImage('image/png');
          //   document.body.setAttribute('data-imagedata', dataUrl);
          //   resolve();
          // });
        </script>
      </body>
    </html>
  `;

  try {
    await page.setContent(htmlContent, { waitUntil: 'domcontentloaded' });
    
    // Wait for Wavesurfer to be ready or error out
    await Promise.race([
        page.evaluate(() => window.wavesurferReady),
        page.evaluate(() => window.wavesurferError).then(err => Promise.reject(err))
    ]);

    // Additional wait for rendering, if necessary.
    // For static images, 'ready' should be sufficient.
    // Consider a small delay or specific rendering event if issues arise.
    await page.waitForTimeout(500); // Wait for 500ms for rendering to settle

    const waveformElement = await page.$('#waveform');
    if (waveformElement) {
      await waveformElement.screenshot({ path: outputImagePath });
      console.log(`Waveform image saved to ${outputImagePath}`);
    } else {
      console.error('Waveform element not found.');
      throw new Error('Waveform element not found');
    }
  } catch (error) {
    console.error('Error during waveform generation:', error);
    // Capture a screenshot of the page for debugging
    const errorScreenshotPath = outputImagePath.replace(path.extname(outputImagePath), '-error.png');
    await page.screenshot({ path: errorScreenshotPath });
    console.log(`Error screenshot saved to ${errorScreenshotPath}`);
    throw error; // Re-throw to signal failure
  } finally {
    await browser.close();
  }
}

(async () => {
    try {
        await generateWaveformImage(audioUrl, outputImagePath);
    } catch (e) {
        console.error("Script execution failed:", e);
        process.exit(1);
    }
})();
