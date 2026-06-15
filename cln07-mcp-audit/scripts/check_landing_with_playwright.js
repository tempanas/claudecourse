"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

const projectRoot = path.resolve(__dirname, "..");
const screenshotPath = path.join(
  projectRoot,
  "temp",
  "consultation-landing-screenshot.png"
);
const localUrl = process.env.LANDING_URL || "http://127.0.0.1:8080";
const fileUrl = `file://${path.join(projectRoot, "index.html")}`;

function loadPlaywright() {
  const candidates = [
    "playwright",
    path.join(
      os.homedir(),
      ".cache",
      "codex-runtimes",
      "codex-primary-runtime",
      "dependencies",
      "node",
      "node_modules",
      "playwright"
    ),
  ];

  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch (error) {
      if (error.code !== "MODULE_NOT_FOUND") {
        throw error;
      }
    }
  }

  throw new Error(
    "Playwright не найден. Запустите скрипт в desktop Codex или установите пакет playwright."
  );
}

function getBrowserLaunchOptions() {
  const browserCandidates = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  ];
  const executablePath = browserCandidates.find((candidate) =>
    fs.existsSync(candidate)
  );

  return executablePath ? { headless: true, executablePath } : { headless: true };
}

async function openLanding(page) {
  try {
    const response = await page.goto(localUrl, {
      waitUntil: "domcontentloaded",
      timeout: 5000,
    });

    if (response && response.ok()) {
      return localUrl;
    }
  } catch (error) {
    console.log(`Локальный сервер недоступен: ${localUrl}`);
  }

  await page.goto(fileUrl, {
    waitUntil: "domcontentloaded",
    timeout: 5000,
  });
  return fileUrl;
}

async function main() {
  const { chromium } = loadPlaywright();
  fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });

  const browser = await chromium.launch(getBrowserLaunchOptions());
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];

  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(message.text());
    }
  });

  page.on("pageerror", (error) => {
    errors.push(error.message);
  });

  try {
    const openedUrl = await openLanding(page);
    const checks = [
      "Запись на консультацию тарифа Бизнес",
      "Для кого эта страница",
      "Когда нужна консультация",
      "Что подготовить перед заявкой",
      "Как проходит процесс",
      "Бесплатная или платная",
      "Сформировать заявку",
    ];

    const results = [];
    for (const text of checks) {
      const found = (await page.getByText(text, { exact: true }).count()) > 0;
      results.push({ text, found });
    }

    await page.screenshot({
      path: screenshotPath,
      fullPage: true,
    });

    const failed = results.filter((result) => !result.found);
    console.log(`Открыта страница: ${openedUrl}`);
    console.log(`Скриншот: ${screenshotPath}`);
    console.log(`Ключевые тексты: ${results.length - failed.length}/${results.length}`);
    console.log(`Ошибки страницы: ${errors.length}`);

    if (failed.length > 0) {
      console.error(
        `Не найдены тексты: ${failed.map((result) => result.text).join(", ")}`
      );
      process.exitCode = 1;
    } else if (errors.length > 0) {
      console.error(errors.join("\n"));
      process.exitCode = 1;
    } else {
      console.log("Результат: проверка пройдена.");
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`Ошибка проверки: ${error.message}`);
  process.exitCode = 1;
});
