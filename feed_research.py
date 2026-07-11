import json
import sys

STATE_FILE = "state.json"

def main():
    research_text = " ".join(sys.argv[1:])
    if not research_text:
        print("Usage: python3 feed_research.py \"paste Gemini's reply here\"")
        return

    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    state["knowledge"]["sources"].append(research_text)

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    print("Research saved to knowledge base. Run run.py next to have the agent use it.")

if __name__ == "__main__":
    main()