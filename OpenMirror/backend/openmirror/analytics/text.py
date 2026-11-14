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

# English function words plus chat fillers and common romanised Hindi/Telugu
# fillers. These carry little topical meaning, so they are excluded from topic
# extraction. The list is intentionally visible and editable.
STOPWORDS = frozenset(
    """
a about above after again against all also am an and any are aren't as at be because been before being
below between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down
during each few for from further had hadn't has hasn't have haven't having he he'd he'll he's her here
here's hers herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself
let's me more most mustn't my myself no nor not of off on once only or other ought our ours ourselves
out over own same shan't she she'd she'll she's should shouldn't so some such than that that's the their
theirs them themselves then there there's these they they'd they'll they're they've this those through
to too under until up very was wasn't we we'd we'll we're we've were weren't what what's when when's
where where's which while who who's whom why why's with won't would wouldn't you you'd you'll you're
you've your yours yourself yourselves
im ive id dont didnt doesnt cant wont isnt thats whats youre ill
just like get got go going gonna wanna will would one also really much still even well now then today
tomorrow yesterday tonight time know think want need make see say said tell told come came take back
yes yeah yep yup yea ya nope nah ok okay okk okie k kk sure fine good great nice cool right alright
haha hahaha hehe lol lmao rofl hmm hmmm hm ohh oh ah ahh uh um umm wow omg bro dude man yaar
hi hey hello bye thanks thank thx pls please sorry welcome morning night gn gm
u ur r n y pic pics msg msgs
true let agreed done makes sense definitely way check sure call free busy reached thing things something
anything maybe actually literally though already bit lot guess also wait thats there's yours mine
media omitted message deleted edited attached image video audio sticker gif document null
hai hain nahi nhi kya toh bhi mein aur haan han kar karo raha rahi rahe tha thi hoga kuch abhi bas
ka ki ke ko se na ho h ne par pe ye yeh wo woh vo kaise kaun kab kyun kyu accha acha theek thik
ra em enti ledu undi ani kuda inka avunu sare nenu nuvvu adi idi ela ekkada eppudu chala ante
    """.split()
)


def clean_body(text: str) -> str:
    """Remove the edited marker and invisible direction marks from a body."""
    return BIDI_RE.sub("", EDITED_MARKER_RE.sub("", text))


def tokenize(text: str) -> list[str]:
    text = URL_RE.sub(" ", clean_body(text)).lower()
    return [t.strip("'’") for t in TOKEN_RE.findall(text)]


def topic_terms(text: str) -> list[str]:
    return [t for t in tokenize(text) if len(t) >= 3 and t not in STOPWORDS]


def word_count(text: str) -> int:
    return len(tokenize(text))


def emojis(text: str) -> list[str]:
    return EMOJI_RE.findall(text)
