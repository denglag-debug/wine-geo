// make_pdf.js — делает PDF из готовых страниц сайта (после python3 build.py).
// Запуск из папки portal:   node tools/make_pdf.js
// Какие страницы печатать, генератор записал в site/static/pdf-jobs.json
// (это страницы, у которых в page.yaml в downloads стоит auto: true).
// Нужен Node.js и Playwright (браузер Chromium, которым управляет программа).
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const SITE = path.resolve(__dirname, '..', 'site');
const jobs = JSON.parse(fs.readFileSync(path.join(SITE, 'static', 'pdf-jobs.json'), 'utf8'));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const job of jobs) {
    await page.goto('file://' + path.join(SITE, job.html));
    await page.emulateMedia({ media: 'print' });          // включаем «печатные» стили (без меню и кнопок)
    await page.pdf({
      path: path.join(SITE, job.pdf),
      format: 'A4',
      printBackground: true,
      preferCSSPageSize: true,                            // поля берём из @page в style.css
      displayHeaderFooter: true,                          // внизу — название и номера страниц
      headerTemplate: '<span></span>',
      footerTemplate:
        '<div style="font-size:8px;color:#8c837b;width:100%;padding:0 13mm;display:flex;justify-content:space-between">' +
        '<span>' + job.title + ' · винная энциклопедия</span>' +
        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
    });
    console.log('PDF готов:', job.pdf);
  }
  await browser.close();
})();
