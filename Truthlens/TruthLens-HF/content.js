/**
 * TruthLens — content.js
 * ======================
 * Runs silently on every webpage.
 * Extracts article text when popup requests it.
 * Uses four progressive extraction strategies.
 */

// ── Message listener ─────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'extractText') {
    const text = extractText();
    sendResponse({
      text,
      wordCount: text.split(/\s+/).filter(w => w.length > 0).length
    });
  }
  return true;
});

// ── Main extraction ───────────────────────────────────────────
function extractText() {
  let text = '';

  // Strategy 1 — semantic article tags
  text = fromSemanticTags();
  if (sufficient(text)) return clean(text);

  // Strategy 2 — news site specific selectors
  text = fromNewsSelectors();
  if (sufficient(text)) return clean(text);

  // Strategy 3 — paragraph density
  text = fromDensity();
  if (sufficient(text)) return clean(text);

  // Strategy 4 — all paragraphs fallback
  text = fromParagraphs();
  return clean(text);
}

// ── Strategy 1: Semantic tags ─────────────────────────────────
function fromSemanticTags() {
  const sels = [
    'article',
    '[role="main"]',
    'main',
    '.article-body',
    '.article-content',
    '.story-body',
    '.post-content',
    '.entry-content',
    '.content-body',
    '#article-body',
    '#main-content',
  ];
  for (const s of sels) {
    const el = document.querySelector(s);
    if (el) {
      const t = fromElement(el);
      if (sufficient(t)) return t;
    }
  }
  return '';
}

// ── Strategy 2: News site selectors ──────────────────────────
function fromNewsSelectors() {
  const sels = [
    '[data-component="text-block"]',   // BBC
    '.article-body-commercial-selector', // Guardian
    '.article__content',                // CNN
    '.article-body__content',           // Reuters
    '.StoryBodyCompanionColumn',        // NYT
    '.article__body',
    '.post-body',
    '.story-content',
    '.news-body',
    '.content-article',
    '.paragraph',
  ];
  for (const s of sels) {
    const els = document.querySelectorAll(s);
    if (els.length > 0) {
      const t = Array.from(els).map(e => e.innerText || e.textContent || '').join(' ');
      if (sufficient(t)) return t;
    }
  }
  return '';
}

// ── Strategy 3: Paragraph density ────────────────────────────
function fromDensity() {
  const skip = /nav|header|footer|sidebar|menu|comment|related|social|share|advert|cookie|promo/i;
  let best = null, bestScore = 0;

  document.querySelectorAll('div,section,main,article').forEach(el => {
    const id  = (el.id || '') + ' ' + (el.className || '');
    if (skip.test(id)) return;
    const paras = el.querySelectorAll('p');
    const len   = (el.innerText || '').length;
    const score = paras.length * 12 + len;
    if (score > bestScore && paras.length >= 3) {
      bestScore = score;
      best = el;
    }
  });

  return best ? fromElement(best) : '';
}

// ── Strategy 4: All paragraphs ────────────────────────────────
function fromParagraphs() {
  return Array.from(document.querySelectorAll('p'))
    .map(p => p.innerText || p.textContent || '')
    .filter(t => t.trim().length > 30)
    .join(' ');
}

// ── Extract text from element ─────────────────────────────────
function fromElement(el) {
  const clone = el.cloneNode(true);
  ['script','style','nav','header','footer','aside',
   'form','button','figure','figcaption'].forEach(tag => {
    clone.querySelectorAll(tag).forEach(c => c.remove());
  });
  return clone.innerText || clone.textContent || '';
}

// ── Helpers ───────────────────────────────────────────────────
function sufficient(text) {
  return text && text.trim().split(/\s+/).filter(w => w).length >= 50;
}

function clean(text) {
  return text.replace(/\s+/g,' ').replace(/\n{3,}/g,'\n\n').trim().slice(0, 10000);
}
