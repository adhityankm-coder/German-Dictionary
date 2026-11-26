import os
from typing import Literal
import httpx
from fastmcp import FastMCP

mcp = FastMCP("German Dictionary")

WIKTIONARY_API = "https://en.wiktionary.org/w/api.php"
MYMEMORY_API = "https://api.mymemory.translated.net/get"
USER_AGENT = "GermanDictionaryMCP/1.0 (personal language-learning project)"

async def fetch_wiktionary_extract(term: str) -> str:
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": 1,
        "exsectionformat": "plain",
        "redirects": 1,
        "titles": term,
    }
    async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(WIKTIONARY_API, params=params)
        response.raise_for_status()
        data = response.json()

    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    extract = page.get("extract", "")
    if not extract:
        return f"No Wiktionary entry was found for '{term}'. Try another spelling or ask Claude to explain the word from its language knowledge."
    return extract[:12000]

@mcp.tool
async def translate_text(
    text: str,
    direction: Literal["de-en", "en-de"] = "de-en"
) -> str:
    """Translate German to English or English to German using MyMemory's translation API.

    Use direction='de-en' for German to English and direction='en-de' for English to German.
    MyMemory has free daily usage limits; this is not unlimited translation.
    """
    text = text.strip()
    if not text:
        return "Please provide text to translate."
    if len(text.encode("utf-8")) > 450:
        return "This free translation endpoint accepts short segments only (maximum about 450 UTF-8 bytes per request). Split longer text into sentences."
    source, target = ("de", "en") if direction == "de-en" else ("en", "de")
    params = {"q": text, "langpair": f"{source}|{target}", "mt": "1"}
    contact_email = os.getenv("MYMEMORY_CONTACT_EMAIL", "").strip()
    if contact_email:
        params["de"] = contact_email

    async with httpx.AsyncClient(timeout=25.0, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(MYMEMORY_API, params=params)
        response.raise_for_status()
        data = response.json()

    if data.get("responseStatus") != 200:
        detail = data.get("responseDetails", "The translation service did not return a translation.")
        return f"Translation service message: {detail}"
    translated = data.get("responseData", {}).get("translatedText", "")
    if not translated:
        return "No translation was returned. Try a shorter phrase."
    return (
        f"Translation ({source} → {target}): {translated}\n"
        "Note: machine/translation-memory output can be imperfect. Check context, especially idioms and separable verbs."
    )

@mcp.tool
async def lookup_german_word(word: str) -> str:
    """Look up a German word in English Wiktionary. Useful for meanings, noun gender, plural, verb forms, usage and grammar notes."""
    word = word.strip()
    if not word:
        return "Please provide a German word."
    return await fetch_wiktionary_extract(word)

@mcp.tool
async def lookup_english_word(word: str) -> str:
    """Look up an English word in English Wiktionary, including German translations where available."""
    word = word.strip()
    if not word:
        return "Please provide an English word."
    return await fetch_wiktionary_extract(word)

@mcp.tool
async def get_verb_reference(infinitive: str) -> str:
    """Retrieve the Wiktionary reference entry for a German verb. Ask Claude to use it to explain Präsens, Präteritum, Perfekt, auxiliary verb and example usage. Wiktionary coverage varies."""
    infinitive = infinitive.strip()
    if not infinitive:
        return "Please provide a German verb infinitive."
    return await fetch_wiktionary_extract(infinitive)

@mcp.tool
async def explain_word_for_b1(word_or_phrase: str) -> str:
    """Retrieve a dictionary reference for a German word or phrase so Claude can explain it at B1 level, including synonyms, prepositions, cases and examples."""
    word_or_phrase = word_or_phrase.strip()
    if not word_or_phrase:
        return "Please provide a German word or phrase."
    return await fetch_wiktionary_extract(word_or_phrase)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    # Streamable HTTP endpoint is served at /mcp.
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
