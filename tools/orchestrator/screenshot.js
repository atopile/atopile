#!/usr/bin/env node
const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const SCREENSHOT_DIR = '/tmp/orchestrator-screenshots';

async function takeScreenshot(url, name, options = {}) {
  // Ensure screenshot directory exists
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1400, height: 900 });

    console.log(`Navigating to ${url}...`);
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

    // Wait a bit for React to render
    await new Promise(r => setTimeout(r, 1000));

    // Click on agent if requested
    if (options.clickAgent) {
      console.log('Looking for agent card to click...');
      try {
        // Wait for agent cards to appear - they have the 'card' class
        await page.waitForSelector('.card', { timeout: 5000 });

        // Find agent cards
        const agentCards = await page.$$('.card.cursor-pointer');
        if (agentCards.length > 0) {
          console.log(`Found ${agentCards.length} agent cards`);

          // If agentName is specified, find the matching card
          let cardToClick = agentCards[agentCards.length - 1]; // Default to last card
          if (options.agentName) {
            for (const card of agentCards) {
              const text = await card.evaluate(el => el.textContent);
              if (text.includes(options.agentName)) {
                cardToClick = card;
                console.log(`Found matching agent: ${options.agentName}`);
                break;
              }
            }
          }

          await cardToClick.click();
          await new Promise(r => setTimeout(r, 2000)); // Wait for detail panel to load and fetch data
        } else {
          console.log('No agent cards found');
        }
      } catch (e) {
        console.log('Error clicking agent:', e.message);
      }
    }

    // Scroll handling
    if (options.scrollTop) {
      await page.evaluate(() => {
        const scrollable = document.querySelector('.output-stream');
        if (scrollable) {
          scrollable.scrollTop = 0;
        }
      });
      await new Promise(r => setTimeout(r, 500));
    } else if (options.scrollDown) {
      await page.evaluate(() => {
        const scrollable = document.querySelector('.output-stream');
        if (scrollable) {
          scrollable.scrollTop = scrollable.scrollHeight;
        }
      });
      await new Promise(r => setTimeout(r, 500));
    }

    const screenshotPath = path.join(SCREENSHOT_DIR, `${name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });

    console.log(`Screenshot saved to: ${screenshotPath}`);
    return screenshotPath;
  } finally {
    await browser.close();
  }
}

async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'main';
  const agentName = args[1]; // Optional agent name to click on
  const url = 'http://localhost:5174';

  try {
    switch (command) {
      case 'main':
        await takeScreenshot(url, 'orchestrator-main');
        break;
      case 'agent':
        await takeScreenshot(url, 'orchestrator-agent-detail', { clickAgent: true, agentName });
        break;
      case 'agent-top':
        await takeScreenshot(url, 'orchestrator-agent-top', { clickAgent: true, agentName, scrollTop: true });
        break;
      case 'agent-scroll':
        await takeScreenshot(url, 'orchestrator-agent-scrolled', { clickAgent: true, agentName, scrollDown: true });
        break;
      default:
        // Treat as custom name
        await takeScreenshot(url, command);
    }
  } catch (err) {
    console.error('Error taking screenshot:', err.message);
    process.exit(1);
  }
}

main();
