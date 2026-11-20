import json

from vi_core.results import safe_decision

if __name__ == "__main__":
    print(
        json.dumps(
            {
                "mode": "simulation",
                "camera": "fake",
                "plc": "fake",
                "decision": safe_decision(None).value,
                "message": "No model loaded. No hardware output written.",
            }
        )
    )
