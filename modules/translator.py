"""Translator module — language pair state for real-time translation mode."""

_from_lang = ""
_to_lang   = ""

# Maps display name → (ISO code, edge-tts voice name)
LANGUAGES: dict[str, tuple[str, str]] = {
    "English":    ("en", "en-US-AriaNeural"),
    "French":     ("fr", "fr-FR-DeniseNeural"),
    "Spanish":    ("es", "es-ES-ElviraNeural"),
    "German":     ("de", "de-DE-KatjaNeural"),
    "Italian":    ("it", "it-IT-ElsaNeural"),
    "Japanese":   ("ja", "ja-JP-NanamiNeural"),
    "Korean":     ("ko", "ko-KR-SunHiNeural"),
    "Chinese":    ("zh", "zh-CN-XiaoxiaoNeural"),
    "Portuguese": ("pt", "pt-BR-FranciscaNeural"),
    "Arabic":     ("ar", "ar-SA-ZariyahNeural"),
    "Hindi":      ("hi", "hi-IN-SwaraNeural"),
    "Russian":    ("ru", "ru-RU-SvetlanaNeural"),
    "Dutch":      ("nl", "nl-NL-ColetteNeural"),
    "Bengali":    ("bn", "bn-IN-TanishaaNeural"),
}

LANG_NAMES = list(LANGUAGES.keys())


def is_active() -> bool:
    return bool(_from_lang and _to_lang)


def get_from_lang() -> str:
    return _from_lang


def get_to_lang() -> str:
    return _to_lang


def get_tts_voice(lang_name: str) -> str:
    return LANGUAGES.get(lang_name, ("en", "en-US-AriaNeural"))[1]


def set_languages(from_lang: str, to_lang: str) -> None:
    global _from_lang, _to_lang
    _from_lang = from_lang
    _to_lang   = to_lang


def clear() -> None:
    global _from_lang, _to_lang
    _from_lang = ""
    _to_lang   = ""
