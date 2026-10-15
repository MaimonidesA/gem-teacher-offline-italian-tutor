"""Bounded teaching notes and explicit feedback, shared by storage and prompts."""
import json

NOTE_LIMITS = {"summary": 360, "next_step": 180}
LIST_LIMITS = {"facts": 4, "strengths": 3, "practice": 3}


def clean_notes(value):
    value = value if isinstance(value, dict) else {}
    result = {key: str(value.get(key, ""))[:limit].strip() for key, limit in NOTE_LIMITS.items()}
    for key, count in LIST_LIMITS.items():
        items = value.get(key, [])
        result[key] = list(dict.fromkeys(str(item).strip()[:120] for item in items if isinstance(item, str) and item.strip()))[:count] if isinstance(items, list) else []
    return result


def compact_notes(value, budget=1700):
    notes = clean_notes(value)
    # Compact the actual JSON, not an arbitrary string slice that can break it.
    while len(json.dumps(notes, ensure_ascii=False)) > budget:
        longest = max(LIST_LIMITS, key=lambda k: len(notes[k]))
        if notes[longest]:
            notes[longest].pop()
        elif notes["summary"] or notes["next_step"]:
            key = max(NOTE_LIMITS, key=lambda k: len(notes[k]))
            notes[key] = notes[key][:-30]
        else:
            break
    return notes


def clean_assessment(value, action, correction=""):
    if action != "reply":
        return None
    if not isinstance(value, dict):
        # Older transcripts have no phrase rating: don't manufacture one.
        return {"rating": None, "verdict": "unrated", "clarity": "unknown", "corrected": "",
                "explanation": correction[:500], "praise": ""}
    rating = value.get("rating")
    rating = min(5, max(0, rating)) if type(rating) is int else None
    verdict = value.get("verdict", "unrated")
    if verdict not in ("correct", "almost", "needs_work", "unclear", "unrated"):
        verdict = "unrated"
    clarity = value.get("clarity", "unknown")
    if clarity not in ("clear", "partly_clear", "unclear", "unknown"):
        clarity = "unknown"
    result = {"rating": rating, "verdict": verdict, "clarity": clarity,
              **{key: str(value.get(key, ""))[:500].strip() for key in ("corrected", "explanation", "praise")}}
    if verdict == "correct":
        result["corrected"] = ""
        result["rating"] = 5
    elif verdict in ("almost", "needs_work", "unclear") and rating is not None:
        result["rating"] = min(rating, {"almost": 4, "needs_work": 3, "unclear": 1}[verdict])
    return result


def segment_kind(segment, target=None, action="reply"):
    kind = segment.get("kind")
    if kind in ("dialogue", "instruction", "translation"):
        return kind
    if target and segment.get("language") != target:
        return "instruction" if action in ("english", "simplify", "hint") else "translation"
    return "dialogue"
