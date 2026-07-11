import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ---- Toggles for testing/debugging ----
USE_WEB_SEARCH = False
MODEL = "claude-haiku-4-5-20251001"  # cheap model for debugging; switch to "claude-sonnet-5" for real runs
MAX_TOKENS = 4000
# ----------------------------------------

STATE_FILE = "state.json"

def main():
    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    # Build a slimmed-down view for the prompt: drop the full log,
    # rely on conversation.summary to carry history forward instead.
    state_for_prompt = {k: v for k, v in state.items() if k != "log"}

    system_prompt = f"""You are a trip-planning agent helping plan a budget trip through Eastern Europe and the Balkans.
You maintain state across daily runs, but you do NOT see the full history log - only the current state below, where "conversation.summary" is your memory of everything that's happened so far.

Current state:
{json.dumps(state_for_prompt, indent=2)}

Your job today:
1. Reason about what you already know to move the plan forward.
2. Update "candidates" and "ruled_out" if you learned something new.
3. Only set "research_needed" if ALL of these are true:
   - The gap is something you cannot reasonably estimate or reason about (e.g. exact current prices, live timetables, visa rules that change), NOT general knowledge you already have.
   - Answering it would actually change a decision right now - not just "nice to know."
   - It hasn't already been answered in "knowledge.sources" above - check first.
   If ANY of these fail, set "research_needed" to null. Default to null.
4. Ask ONE sharp, specific question that would help narrow down the trip plan.
5. IMPORTANT: rewrite "conversation.summary" to be a tight, current summary of the whole plan so far - decisions made, open questions, key constraints. This replaces the old summary entirely; it's the only memory that carries forward, so don't lose anything important.
6. Respond ONLY with valid JSON matching this exact shape, nothing else. Preserve every key from the current state (goal, preferences, conversation, knowledge, candidates, ruled_out, open_question, your_last_answer) in "updated_state", only changing what you update:
{{
  "updated_state": {{ ...the full updated state object, preserving all existing keys... }},
  "research_needed": "a self-contained prompt to paste into Gemini, or null - see rules above",
  "question_for_user": "your one question here",
  "summary": "1-2 sentence summary of what you did this run, for the local log only"
}}"""

    kwargs = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": system_prompt}],
    }

    if USE_WEB_SEARCH:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

    response = client.messages.create(**kwargs)

    text_block = next((b for b in response.content if b.type == "text"), None)

    if text_block is None:
        print("No text block found in response. Raw response:")
        print(response.content)
        return

    raw_text = text_block.text.strip().replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        print("Could not parse response as JSON. Raw output:")
        print(raw_text)
        return

    # Re-attach the full log (kept locally, never sent to the API) and append today's entry
    parsed["updated_state"]["log"] = state.get("log", [])
    parsed["updated_state"]["log"].append({
        "date": datetime.now(timezone.utc).isoformat(),
        "summary": parsed["summary"],
        "question_asked": parsed["question_for_user"]
    })

    with open(STATE_FILE, "w") as f:
        json.dump(parsed["updated_state"], f, indent=2)

    print(f"=== Model: {MODEL} | Web search: {USE_WEB_SEARCH} ===")
    print("=== Today's update ===")
    print(parsed["summary"])
    if parsed.get("research_needed"):
        print("\n=== Paste this into Gemini/ChatGPT (free) ===")
        print(parsed["research_needed"])
    print("\n=== Question for you ===")
    print(parsed["question_for_user"])

if __name__ == "__main__":
    main()