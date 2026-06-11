import re

_FILLER_PATTERNS = [
    re.compile(p)
    for p in [
        r"那我猜",
        r"[!！]{2,}",
        r"[0-9]{2,}$",
        r"^[?？]{2,}$",
        r"^[。，.]+$",
        r"^[哈嘿哎啊哦嗯呀诶嗨哟噢]+$",
        r"^[emEm]{2,}$",
        r"^\d+$",
    ]
]

_EMOTICON_REGEX = re.compile(
    r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
    r"\u2600-\u26FF\u2700-\u27BF]"
)
_PUNCT_REGEX = re.compile(
    r"[!！?？。，,\.、：:；;…~～（）()【】\[\]《》\"\"''\"\"''—\-+=\/\\|@#$%^&*◇◆○●◎☆★△▲▽▼□■▷▶◁◀…·‥¨´]"
)

_CJK_RANGE = re.compile(r"^[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+$")


def clean_danmaku(raw: str) -> dict:
    text = raw.strip()
    text = _EMOTICON_REGEX.sub("", text)
    text = _PUNCT_REGEX.sub("", text)

    for pat in _FILLER_PATTERNS:
        text = pat.sub("", text).strip()

    if not text:
        return {"valid": False, "word": "", "reason": "empty after cleaning"}

    if not _CJK_RANGE.match(text):
        return {
            "valid": False,
            "word": text,
            "reason": "contains non-CJK after cleaning",
        }

    return {"valid": True, "word": text}
