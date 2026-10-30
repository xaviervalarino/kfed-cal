"""Exploration only: read Monty Bar's weekly flyer image with Claude Haiku and save the events it finds.

Writes probe/out/monty/: flyer.png, response.json (the events), usage.json (tokens and cost).
Skips quietly when ANTHROPIC_API_KEY is not set.
"""

import base64
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper.fetch import Fetcher  # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "monty"
MODEL = "claude-haiku-5-5"
PRICE = {"input": 0.10, "output": 0.50}  # dollars per million tokens
FLYER = re.compile(r"https://montybar\.com/wp-content/uploads/[\w/]+/MONTY-weekly-[\d-]+?(?:-\d+x\d+)?\.(?:png|jpe?g)")

SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "Start time as HH:MM (24-hour), or empty if not shown"},
                    "title": {"type": "string", "description": "Main event or act name, as written"},
                    "details": {"type": "string", "description": "All other text for this event, verbatim"},
                },
                "required": ["date", "time", "title", "details"],
                "additionalProperties": False,
            },
        },
        "unplaced_text": {"type": "string", "description": "Flyer text not tied to a specific day, verbatim"},
    },
    "required": ["events", "unplaced_text"],
    "additionalProperties": False,
}

PROMPT = f"""This is the weekly events flyer for Monty Bar, a bar in Los Angeles. Today is {date.today()}.
List every event on the flyer, one entry per event. Use the year of the week shown on the flyer.
Copy text exactly as written. Do not guess: if a day has no event, leave it out.
Keep all text that belongs to an event (support acts, DJs, "performing live", prices, ages) in its details.
Put any text you cannot tie to one event in unplaced_text."""


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set: skipping the Monty flyer probe")
        return
    import anthropic

    OUT.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher()
    urls = FLYER.findall(fetcher.get("https://montybar.com/").text)
    if not urls:
        print("No weekly flyer image found on montybar.com")
        return
    url = re.sub(r"-\d+x\d+(?=\.\w+$)", "", urls[0])  # full size, not a thumbnail
    image = fetcher.get(url)
    (OUT / "flyer.png").write_bytes(image.content)
    media_type = image.headers.get("content-type", "image/png").split(";")[0]

    response = anthropic.Anthropic().messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                         "data": base64.standard_b64encode(image.content).decode()}},
            {"type": "text", "text": PROMPT},
        ]}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    result = {"flyer": url, **json.loads(text)}
    (OUT / "response.json").write_text(json.dumps(result, indent=2))
    usage = response.usage
    cost = (usage.input_tokens * PRICE["input"] + usage.output_tokens * PRICE["output"]) / 1e6
    (OUT / "usage.json").write_text(json.dumps({"model": MODEL, "input_tokens": usage.input_tokens,
                                                "output_tokens": usage.output_tokens, "dollars": cost}, indent=2))
    print(f"Flyer {url}: {len(result['events'])} events, {usage.input_tokens} in / {usage.output_tokens} out "
          f"tokens, ${cost:.5f}")
    for e in result["events"]:
        print(f"  {e['date']} {e['time'] or '--:--'} {e['title']} | {e['details'][:120]}")
    if result["unplaced_text"]:
        print(f"  unplaced: {result['unplaced_text'][:200]}")


if __name__ == "__main__":
    main()
