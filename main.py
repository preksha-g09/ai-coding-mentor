from app.mentor import review_code
from memory.store import save_session, get_past_mistakes, get_weakness_summary
import re

def extract_weak_spot(review_text: str) -> str:
    """Pull the weak spot tag out of the LLM's review."""
    lines = review_text.lower().split("\n")
    for line in lines:
        if "weak spot" in line:
            # grab everything after the colon
            parts = line.split(":")
            if len(parts) > 1:
                return parts[1].strip()[:40].rstrip(")")
    return "general"

test_code = """
def calc(l):
    s = 0
    result = []
    for i in range(len(l)):
        s = s + l[i]
        result.append(s)
    return result

data = [1,2,3,4,5]
print(calc(data))
"""

print("=" * 50)
print("AI CODING MENTOR — CODE REVIEW")
print("=" * 50)
print()

# Step 1: fetch relevant past mistakes BEFORE reviewing
print("Checking memory for past mistakes...")
past_mistakes = get_past_mistakes(test_code)
print(f"Past context: {past_mistakes[:100]}...")
print()

# Step 2: review the code WITH memory context
review = review_code(
    code=test_code,
    language="Python",
    past_mistakes=past_mistakes
)

print(review)
print()

# Step 3: extract weak spot and save this session to memory
weak_spot = extract_weak_spot(review)
save_session(code=test_code, review=review, weak_spot=weak_spot)

# Step 4: show weakness summary so far
print()
print("=" * 50)
print("YOUR WEAKNESS HEATMAP SO FAR:")
summary = get_weakness_summary()
for spot, count in sorted(summary.items(), key=lambda x: -x[1]):
    bar = "█" * count
    print(f"  {spot:<30} {bar} ({count})")
print("=" * 50)