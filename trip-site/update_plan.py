import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-haiku-4-5-20251001"  # cheap default; bump to claude-sonnet-5 if quality needs it
MAX_TOKENS = 3000
MAX_SEARCHES_PER_RUN = 3  # hard ceiling if any enrichment request needs search

PLAN_FILE = "plan.json"
FEEDBACK_FILE = "feedback.json"


def build_prompt(plan, plain_feedback, enrichment_requests):
    parts = [f"""You maintain a trip itinerary as structured JSON for a travel-planning website.

Current plan:
{json.dumps(plan, indent=2)}
"""]

    if plain_feedback:
        parts.append(f"""
General feedback to incorporate (reasoning only, no research needed):
{json.dumps(plain_feedback, indent=2)}
""")

    if enrichment_requests:
        parts.append(f"""
Specific enrichment requests - use web search to find real, current, specific answers for these:
{json.dumps(enrichment_requests, indent=2)}
Only search for what's explicitly requested here. Do not go looking for anything else.
""")

    parts.append(f"""
Your job:
1. Update the plan based on the feedback/requests above - only change what they actually address. Don't invent unrelated content.
2. Keep every stop's "lat" and "lon" fields intact and accurate. If you add a new stop, include real, correct latitude/longitude.
3. Keep "stops" as short, distinct entries - one place per entry, 1-2 sentence notes each. If enrichment adds recommendations (hotels, cafes, etc.), add them as a short "recommendations" list on that stop, not a paragraph.
4. Update "open_questions" to reflect what's genuinely still undecided.
5. Set "last_updated" to today's date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.
6. Respond ONLY with the full updated plan JSON, nothing else - no preamble, no markdown fences.
""")

    return "\n".join(parts)


def main():
    with open(PLAN_FILE) as f:
        plan = json.load(f)

    with open(FEEDBACK_FILE) as f:
        feedback_list = json.load(f)

    if not feedback_list:
        print("No new feedback to process. Exiting without calling the API.")
        return

    # Split feedback into plain (cheap) vs enrichment (needs search)
    plain_feedback = [f for f in feedback_list if not (isinstance(f, dict) and f.get("type") == "enrichment_request")]
    enrichment_requests = [f for f in feedback_list if isinstance(f, dict) and f.get("type") == "enrichment_request"]

    prompt = build_prompt(plan, plain_feedback, enrichment_requests)

    kwargs = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }

    # Only attach web search, and only if there's an actual enrichment request
    if enrichment_requests:
        kwargs["tools"] = [{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": MAX_SEARCHES_PER_RUN
        }]

    response = client.messages.create(**kwargs)

    text_block = next((b for b in response.content if b.type == "text"), None)
    if text_block is None:
        print("No text block in response.")
        return

    raw_text = text_block.text.strip().replace("```json", "").replace("```", "").strip()

    try:
        updated_plan = json.loads(raw_text)
    except json.JSONDecodeError:
        print("Could not parse response as JSON. Raw output:")
        print(raw_text)
        return

    with open(PLAN_FILE, "w") as f:
        json.dump(updated_plan, f, indent=2)

    # Clear processed feedback so it isn't reapplied next run
    with open(FEEDBACK_FILE, "w") as f:
        json.dump([], f)

    used_search = bool(enrichment_requests)
    print(f"Plan updated. Plain feedback items: {len(plain_feedback)}. Enrichment requests: {len(enrichment_requests)}. Web search used: {used_search}")
    print(f"New summary: {updated_plan.get('summary', '(no summary field)')}")


if __name__ == "__main__":
    main()