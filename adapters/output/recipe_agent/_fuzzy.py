from adapters.output.recipe_agent._logger import log as logger
from rapidfuzz import fuzz, process


def _make_fuzzy_matcher(threshold: int):
    def fuzzy_match(name: str, candidates: list[dict]) -> dict | None:
        if not candidates:
            return None
        names = [c["name"] for c in candidates]
        result = process.extractOne(name, names, scorer = fuzz.WRatio)
        if result and result[1] >= threshold:
            matched = next(c for c in candidates if c["name"] == result[0])
            logger.debug(f"  fuzzy name={name!r} → MATCH {result[0]!r} score={result[1]} uuid={matched['uuid']}")
            return matched
        best_name = result[0] if result else "—"
        best_score = result[1] if result else 0
        logger.debug(f"  fuzzy name={name!r} → no match (best={best_name!r} score={best_score})")
        return None

    return fuzzy_match
