from mod.client import ModerationUnavailable, categories, flagged, suggest_reply


def review(comment: str) -> dict:
    try:
        bad = flagged(comment)
    except ModerationUnavailable as e:
        return {"status": "pending", "reason": str(e)}
    if bad:
        return {"status": "hidden", "categories": categories(comment)}
    return {"status": "visible", "reply": suggest_reply(comment)}
