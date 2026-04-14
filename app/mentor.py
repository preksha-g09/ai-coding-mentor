from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

llm = OllamaLLM(model="llama3.1", temperature=0.3)

REVIEW_PROMPT = PromptTemplate(
    input_variables=["code", "language", "past_mistakes", "mode"],
    template="""
You are a senior software engineer.

FIRST:
Carefully analyze ONLY the current code.

IMPORTANT RULES:
- Do NOT assume mistakes from past sessions.
- Use past mistakes ONLY if clearly relevant.
- If code is correct → say: "This code is production-ready."
- Do NOT invent issues.
- If no issues → write: "ISSUES: None — code is clean."

MODE: {mode}

MODE INSTRUCTIONS:

roast:
- Be brutally honest
- Call out bad practices harshly

mentor:
- Explain WHY things are wrong
- Teach clearly

speed:
- Max 5 bullet points
- No long explanations

security:
- ONLY talk about vulnerabilities

arch:
- Focus on design and scalability

tests:
- Suggest test cases and edge cases

PAST CONTEXT:
{past_mistakes}

CODE:
{code}

OUTPUT FORMAT:

1. OVERALL
2. ISSUES
3. IMPROVEMENTS
4. SCORE (0–100)
5. WEAK SPOT DETECTED
"""
)

def calculate_score(review_text: str) -> int:
    score = 100
    text = review_text.lower()

    if "error" in text:
        score -= 30
    if "inefficient" in text:
        score -= 15
    if "bad" in text:
        score -= 10
    if "no docstring" in text:
        score -= 5
    if "no type" in text:
        score -= 5

    return max(score, 0)


def review_code(code: str, language: str = "Python", past_mistakes: str = "None yet", mode: str = "mentor") -> str:
    chain = REVIEW_PROMPT | llm

    response = chain.invoke({
        "code": code,
        "language": language,
        "past_mistakes": past_mistakes,
        "mode": mode
    })

    return response