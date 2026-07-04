"""
Text Preprocessor
=================
Identical preprocessing to training pipeline.
This file must stay in sync with the notebook's clean_text function.
Any change here must also be made in the notebook.
"""

import re
import nltk
import urllib.request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

# Download required NLTK data
nltk.download("stopwords", quiet=True)
nltk.download("wordnet",   quiet=True)
nltk.download("omw-1.4",  quiet=True)

from nltk.corpus import stopwords
from nltk.stem   import WordNetLemmatizer

# Initialise once at module level for efficiency
_stop_words  = set(stopwords.words("english"))
_lemmatizer  = WordNetLemmatizer()


def clean_text(text: str) -> str:
    """
    Full text preprocessing pipeline.
    MUST be identical to the notebook's clean_text function.

    Steps:
      1. Handle non-string input
      2. Lowercase conversion
      3. URL removal
      4. HTML tag removal
      5. Source marker removal (Reuters, AP, AFP, CNN)
      6. Punctuation and number removal
      7. Whitespace normalisation
      8. Stopword removal
      9. Lemmatisation
    """
    if not isinstance(text, str):
        return ""

    # Lowercase
    text = text.lower()

    # Remove URLs
    text = re.sub(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|"
        r"[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        "", text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove source markers
    text = re.sub(
        r"\(reuters\)|\(ap\)|\(afp\)|\(cnn\)",
        "", text)

    # Remove punctuation and numbers
    text = re.sub(r"[^a-zA-Z\s]", " ", text)

    # Normalise whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Tokenise, remove stopwords, lemmatise
    words = text.split()
    words = [
        _lemmatizer.lemmatize(w)
        for w in words
        if w not in _stop_words and len(w) > 2
    ]

    return " ".join(words)


class _ArticleExtractor(HTMLParser):
    """
    Simple HTML parser that extracts readable text
    from article tags, paragraphs, and headings.
    """

    def __init__(self):
        super().__init__()
        self.text_parts   = []
        self.skip_tags    = {
            "script", "style", "nav", "header",
            "footer", "aside", "form", "button",
            "meta", "link", "noscript"
        }
        self.capture_tags = {
            "p", "article", "h1", "h2", "h3",
            "h4", "span", "div", "li", "blockquote"
        }
        self._current_skip  = False
        self._skip_depth    = 0
        self._capturing     = False

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self._current_skip = True
            self._skip_depth   = 1
        elif tag in self.capture_tags and not self._current_skip:
            self._capturing = True

    def handle_endtag(self, tag):
        if self._current_skip:
            if tag in self.skip_tags:
                self._skip_depth -= 1
                if self._skip_depth <= 0:
                    self._current_skip = False
        elif tag in self.capture_tags:
            self._capturing = False

    def handle_data(self, data):
        if not self._current_skip and self._capturing:
            stripped = data.strip()
            if len(stripped) > 20:
                self.text_parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self.text_parts)


def fetch_url_text(url: str,
                   timeout: int = 10,
                   max_chars: int = 50000) -> str:
    """
    Fetches article text from a URL.
    Extracts readable content from HTML.
    Returns empty string if fetch fails.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        req      = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=timeout)
        html     = response.read().decode("utf-8", errors="ignore")

        # Limit HTML size
        html = html[:max_chars]

        # Extract text
        parser = _ArticleExtractor()
        parser.feed(html)
        text = parser.get_text()

        # Fallback: extract all text between tags
        if len(text.split()) < 20:
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()

        return text[:10000]  # Cap at 10,000 characters

    except (URLError, HTTPError, Exception):
        return ""


def validate_text(text: str) -> tuple:
    """
    Validates input text.
    Returns (is_valid, error_message).
    """
    if not text or not text.strip():
        return False, "Text cannot be empty."

    word_count = len(text.split())

    if word_count < 10:
        return False, (
            f"Text too short ({word_count} words). "
            f"Please provide at least 10 words.")

    if word_count > 10000:
        return True, None   # Accept but will be truncated

    return True, None
