import math
import re
from collections import Counter

MIN_CHARS = 220
MIN_SENTENCES = 3
MAX_SENTENCES = 4
RATIO = 0.3

CITATION = re.compile(r"\[\s*\d{1,3}\s*\]")
HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
SPLIT = re.compile(r"(?<=[.!?…])\s+(?=[A-ZА-ЯЁ0-9«\"(\[])")
WORD = re.compile(r"[A-Za-zА-Яа-яЁё]{3,}")
ABBREVIATIONS = (
    "г", "гг", "в", "вв", "млн", "млрд", "трлн", "тыс", "руб", "долл",
    "т.е", "т.д", "т.п", "др", "пр", "см", "им", "ул", "св", "рис", "стр",
    "напр", "etc", "vs", "mr", "mrs", "dr", "inc", "no",
)
STOPWORDS = frozenset(
    """
    это этот эта эти этого этой этом этих того тому тем там тут как так также
    или для при над под про без между через после перед чтобы если когда
    который которая которое которые которых которого которой которому
    был была было были быть будет есть нет его ее её их они она оно мне
    все всё всех всего еще ещё уже только очень более менее может могут
    чем что его себя свой свои своего года году годы лет
    the and for with that this from are was were has have had not but its
    his her they them their been will would can could into than then there
    """.split()
)


def _stem(word):
    word = word.lower().replace("ё", "е")
    return word[:5] if re.match(r"[а-я]", word) else word[:6]


def _clean(text):
    text = CITATION.sub("", text)
    text = HYPHEN_BREAK.sub(r"\1\2", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _split_sentences(text):
    pieces = SPLIT.split(text)
    merged = []
    for piece in pieces:
        if merged:
            tail = merged[-1].rstrip(".!?…").rsplit(" ", 1)[-1].lower()
            if tail in ABBREVIATIONS or (len(tail) == 1 and tail.isalpha()):
                merged[-1] = f"{merged[-1]} {piece}"
                continue
        merged.append(piece)
    return [s.strip() for s in merged if len(s.strip()) > 20]


def summarize(text: str) -> str:
    if len(text) < MIN_CHARS:
        return ""
    sentences = _split_sentences(_clean(text))
    if len(sentences) < MIN_SENTENCES:
        return ""
    stems = []
    for sentence in sentences:
        stems.append(
            [_stem(w) for w in WORD.findall(sentence) if w.lower() not in STOPWORDS]
        )
    freq = Counter(stem for row in stems for stem in row)
    if not freq:
        return ""
    peak = max(freq.values())
    scored = []
    for index, row in enumerate(stems):
        if not row:
            continue
        score = sum(freq[s] / peak for s in row) / math.sqrt(len(row))
        if index == 0:
            score *= 1.15
        scored.append((score, index))
    count = max(1, min(MAX_SENTENCES, round(len(sentences) * RATIO)))
    chosen = sorted(i for _, i in sorted(scored, reverse=True)[:count])
    return " ".join(sentences[i] for i in chosen)
