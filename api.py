from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sys, os, json, httpx, asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from memory.store import save_session, get_past_mistakes, get_weakness_summary

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434/api/generate"

class ReviewRequest(BaseModel):
    code: str
    language: str
    mode: str

REVIEW_MODES = {
    "roast": (
        "You are doing a brutal code roast. Be sharp and direct. "
        "Call out EVERY flaw with phrases like 'this will break because', 'never do this'. "
        "Every criticism MUST include a concrete fix."
    ),
    "mentor": (
        "You are a patient senior mentor. Explain WHY behind every suggestion. "
        "Use analogies. Praise what works before addressing issues. "
        "Write as if teaching a junior developer who is eager to learn."
    ),
    "speed": (
        "MAXIMUM brevity. Output ONLY bullet points. "
        "No sentences. No explanations. Max 6 bullets. Each bullet under 10 words."
    ),
    "security": (
        "You are a penetration tester. ONLY look for: injection vulnerabilities, "
        "unsafe inputs, missing auth checks, exposed secrets, insecure defaults, data leaks. "
        "Ignore style and performance entirely unless they cause security issues."
    ),
    "arch": (
        "You are a software architect. ONLY evaluate: SOLID violations, "
        "design pattern opportunities, coupling, cohesion, scalability concerns. "
        "Ignore syntax, style, and minor bugs unless they indicate architectural problems."
    ),
    "tests": (
        "You are a QA engineer. Suggest specific unit tests with function names and test cases. "
        "Point out untestable code. Cover: happy path, edge cases, error cases, boundaries."
    ),
}

def build_prompt(code, language, mode, past):
    mode_instr = REVIEW_MODES.get(mode, REVIEW_MODES["mentor"])
    return (
        f"You are a senior software engineer. {mode_instr}\n\n"
        f"Developer past weak spots (use only if relevant): {past}\n\n"
        f"Review this {language} code:\n"
        f"```{language.lower()}\n{code}\n```\n\n"
        "Respond in EXACTLY this markdown format:\n\n"
        "## Overall\n"
        "One sentence verdict.\n\n"
        "## Issues\n"
        "- **Issue name** (line X): what is wrong and why it matters\n\n"
        "## Improvements\n"
        "- **Fix**: concrete code suggestion\n\n"
        "## Fixed Code\n"
        f"```{language.lower()}\n"
        "[write the complete corrected version of the code here]\n"
        "```\n\n"
        "## Weak Spot Detected\n"
        "`topic-tag`\n"
    )

def extract_weak_spot(text):
    import re
    for line in text.lower().split("\n"):
        if "weak spot" in line:
            tag = re.sub(r'[`\(\)\*]', '', line.split(":")[-1])
            words = tag.strip().split()[:3]  # max 3 words
            return "-".join(words) if words else "general"
    return "general"

def score_from_review(text):
    bad = (
        text.lower().count("issue") +
        text.lower().count("problem") +
        text.lower().count("error") +
        text.lower().count("never") +
        text.lower().count("missing") +
        text.lower().count("vulnerability")
    )
    return max(25, min(95, 95 - bad * 6))

# Track active streams so we can cancel them
active_streams = {}

@app.post("/review/stream")
async def review_stream(req: ReviewRequest):
    past = get_past_mistakes(req.code)
    prompt = build_prompt(req.code, req.language, req.mode, past)
    stream_id = str(id(req))

    async def generate():
        full_text = []
        client = httpx.AsyncClient(timeout=300)
        active_streams[stream_id] = client

        try:
            async with client.stream("POST", OLLAMA_URL, json={
                "model": "llama3.1",
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 1024,
                    "num_ctx": 4096,
                    "top_p": 0.9,
                }
            }) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            full_text.append(token)
                            yield f"data: {json.dumps({'token': token})}\n\n"
                        if data.get("done"):
                            break
                    except Exception:
                        continue

            complete = "".join(full_text)
            spot  = extract_weak_spot(complete)
            score = score_from_review(complete)
            save_session(code=req.code, review=complete, weak_spot=spot)
            yield f"data: {json.dumps({'done': True, 'weak_spot': spot, 'score': score, 'past': past, 'stream_id': stream_id})}\n\n"

        except asyncio.CancelledError:
            yield f"data: {json.dumps({'cancelled': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            active_streams.pop(stream_id, None)
            await client.aclose()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "X-Stream-Id": stream_id,
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )

@app.post("/review/cancel/{stream_id}")
async def cancel_stream(stream_id: str):
    client = active_streams.get(stream_id)
    if client:
        await client.aclose()
        active_streams.pop(stream_id, None)
        return {"cancelled": True}
    return {"cancelled": False}

@app.get("/stats")
async def stats():
    summary = get_weakness_summary()
    return {
        "total": sum(summary.values()),
        "unique": len(summary),
        "heatmap": sorted(summary.items(), key=lambda x: -x[1])[:6]
    }

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")