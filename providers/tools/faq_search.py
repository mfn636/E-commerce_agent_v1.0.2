from typing import Optional, List

from domain.loader import load_faq
from domain.models.faq import FaqItem

FAQ: List[FaqItem] = load_faq()


def search_faq(
    query: Optional[str] = None,
    category: Optional[str] = None,
) -> List[FaqItem]:
    results = []

    for entry in FAQ:

        if category:
            if category not in entry.category:
                continue

        if query:
            text = entry.question + entry.answer
            keywords = _extract_keywords(query)
            if not any(kw in text for kw in keywords):
                continue

        results.append(entry)

    return results


def _extract_keywords(text: str) -> List[str]:
    result = [text]
    for i in range(len(text) - 1):
        chunk = text[i:i+2]
        chunk = chunk.strip(" ?？！!，,。.")
        if chunk and len(chunk) == 2:
            result.append(chunk)
    
    return result
