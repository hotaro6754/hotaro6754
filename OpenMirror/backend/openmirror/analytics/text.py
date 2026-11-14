"""Lightweight, explainable text utilities: tokenisation, stopwords, emoji."""

from __future__ import annotations

import re

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
EDITED_MARKER_RE = re.compile(r"\s*‎?<This message was edited>\s*$")
BIDI_RE = re.compile("[‎‏‪-‮⁦-⁩﻿]")

# Letters in any script, including Indic combining marks (U+0900–U+0DFF).
TOKEN_RE = re.compile(r"(?:[^\W\d_]|[ऀ-෿])(?:[^\W_]|[ऀ-෿]|['’])*")
EMOJI_RE = re.compile(
    "[\U0001f300-\U0001f5ff\U0001f600-\U0001f64f\U0001f680-\U0001f6ff\U0001f900-\U0001f9ff"
    "\U0001fa70-\U0001faff☀-⛿✀-➿❤]"
)

from openmirror.analytics.stopwords import STOPWORDS  # noqa: E402

# Letters repeated 3+ times ("haaaa", "hiiii") are collapsed to two.
ELONGATION_RE = re.compile(r"(.)\1{2,}")


def clean_body(text: str) -> str:
    """Remove the edited marker and invisible direction marks from a body."""
    return BIDI_RE.sub("", EDITED_MARKER_RE.sub("", text))


def tokenize(text: str) -> list[str]:
    text = URL_RE.sub(" ", clean_body(text)).lower()
    return [ELONGATION_RE.sub(r"\1\1", t.strip("'’")) for t in TOKEN_RE.findall(text)]


def _is_stopword(t: str) -> bool:
    # "reyy", "nahhh" and "raaa" should match "rey", "nah" and "raa".
    return t in STOPWORDS or re.sub(r"(.)\1+", r"\1", t) in STOPWORDS


def topic_terms(text: str) -> list[str]:
    return [t for t in tokenize(text) if len(t) >= 3 and not _is_stopword(t)]


def word_count(text: str) -> int:
    return len(tokenize(text))


def emojis(text: str) -> list[str]:
    return EMOJI_RE.findall(text)
