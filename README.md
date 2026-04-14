# AI Coding Mentor

> A local LLM-powered code reviewer with persistent memory — it remembers your past mistakes and gets smarter about your weak spots over time.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square)
![LangChain](https://img.shields.io/badge/LangChain-0.3-orange?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector--db-purple?style=flat-square)
![Llama](https://img.shields.io/badge/Llama_3.1-8B_local-red?style=flat-square)

## Overview

This project is a local LLM-powered code review system designed to provide personalized and context-aware feedback.

Unlike conventional tools, it incorporates a persistent memory mechanism using a vector database (ChromaDB). Each review session is embedded and stored, enabling the system to retrieve semantically similar past interactions using cosine similarity. This allows the model to identify recurring patterns in coding mistakes and provide more tailored feedback over time.

## Architecture

```
User submits code
       ↓
Embed code with sentence-transformers (all-MiniLM-L6-v2)
       ↓
ChromaDB similarity search → retrieve top-3 past mistakes
       ↓
Build prompt: mode instruction + past context + code
       ↓
Stream to Llama 3.1 8B via Ollama (direct HTTP, no overhead)
       ↓
SSE stream → frontend renders markdown token by token
       ↓
Extract weak spot tag → save session to ChromaDB
       ↓
Update weakness heatmap + score ring
```

## Features

- **6 review modes** — each with a genuinely different prompt personality
  -  Roast me — brutal honesty, no sugarcoating
  -  Mentor — explains the *why*, uses analogies
  - Speed — bullets only, max 6 lines
  - Security — penetration tester mindset, vulns only
  - Architecture — SOLID principles, design patterns
  - Tests — suggests unit tests with specific function names

- **Persistent RAG memory** — ChromaDB + sentence-transformers stores every session as a 384-dimensional embedding. Retrieves semantically similar past mistakes before each review.

- **Streaming output** — tokens stream directly from Ollama via HTTP SSE. No LangChain overhead on the critical path — ~3-5s to first token.

- **Fixed code output** — every review includes a corrected version of your code

- **Weakness heatmap** — visual tracker of recurring patterns across all sessions

- **Code quality score** — 0-100 score computed from review content, displayed as an animated SVG ring

- **Abort mid-generation** — stop button cancels the HTTP stream and cleans up server-side

- **Export PDF** — clean print-formatted review with original + fixed code

- **8 languages** — Python, JavaScript, TypeScript, Java, C++, Go, Rust, Swift

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Llama 3.1 8B via Ollama |
| Agent framework | LangChain 0.3 |
| Vector database | ChromaDB (persistent local) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Backend | FastAPI + uvicorn |
| Streaming | Server-Sent Events (SSE) |
| Frontend | Vanilla HTML/CSS/JS (no framework) |
| Fonts | Fraunces (serif) + Geist + Geist Mono |

## Project structure

```
ai-coding-mentor/
├── api.py                 ← FastAPI server, streaming endpoint, Ollama integration
├── app/
│   └── mentor.py          ← LLM chain (used in CLI mode)
├── memory/
│   ├── store.py           ← ChromaDB save/retrieve/heatmap logic
│   └── embedder.py        ← sentence-transformers wrapper
├── frontend/
│   ├── index.html         ← Landing page with 3D crystalline animation
│   └── app.html           ← Main app UI
├── main.py                ← CLI entry point for testing
└── requirements.txt
```

## Setup

**Prerequisites:** Python 3.11+, [Ollama](https://ollama.com) installed

```bash
# 1. Clone
git clone https://github.com/preksha-g09/ai-coding-mentor
cd ai-coding-mentor

# 2. Install Llama 3.1
ollama pull llama3.1

# 3. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run
uvicorn api:app --reload --port 8000

# 6. Open
# http://localhost:8000
```

## How the memory works

When you submit code:
1. The review text is embedded into a 384-dimensional vector using `all-MiniLM-L6-v2`
2. Stored in ChromaDB with metadata: `{weak_spot, timestamp, language}`
3. Next submission triggers a cosine similarity search — top 3 most relevant past sessions retrieved
4. Those past mistakes are injected into the system prompt before Llama reviews your code

This means the mentor becomes more personalised the more you use it.






