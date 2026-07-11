import json
import sys
from datetime import datetime, timezone

STATE_FILE = "state.json"

def main():
    answer_text = " ".join(sys.argv[1:])
    if not answer_text:
        print("Usage: python3 answer.py \"your answer here\"")
        return

    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    state["your_last_answer"] = answer_text
    state["conversation"]["last_user_message"] = answer_text
    state["conversation"]["pending_questions"] = []

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    print("Answer saved. Run run.py next to have the agent process it.")

if __name__ == "__main__":
    main()