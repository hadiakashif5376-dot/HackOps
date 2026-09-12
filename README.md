# HackOps 🚀

HackOps is a modular Streamlit MVP that turns messy hackathon participant profiles and a project idea into a balanced four-person squad and a practical 48-hour execution plan.

## What it does

1. Parses messy participant bios into structured JSON profiles.
2. Analyzes a hackathon project idea into MVP capabilities and roles.
3. Embeds participant profiles with `all-MiniLM-L6-v2`.
4. Builds a local FAISS semantic-search index.
5. Retrieves relevant candidates.
6. Forms a complementary 4-person team.
7. Evaluates project capability coverage and team fit.
8. Generates a structured 48-hour sprint roadmap using Groq `openai/gpt-oss-120b`.

## Architecture

```text
Participant Bios ──> Profile Parser ──> Structured Profiles
                                             │
                                             ▼
                                      Embeddings + FAISS
                                             │
Project Idea ──────> Project Analyzer ───────┤
                                             ▼
                                      Team Matcher
                                             │
                                             ▼
                                      Team Balance
                                             │
                                             ▼
                                      Sprint Planner
                                             │
                                             ▼
                                        Streamlit UI
```

## Project structure

```text
HackOps/
├── app.py
├── mock_data.py
├── profile_parser.py
├── project_analyzer.py
├── vector_store.py
├── team_matcher.py
├── team_balance.py
├── sprint_planner.py
├── prompts.py
├── utils.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Each module has one primary responsibility to support SRP, separation of concerns, loose coupling and high cohesion.

## Requirements

- Python 3.10–3.12 recommended
- A Groq API key
- Internet access on first run so Sentence Transformers can download `all-MiniLM-L6-v2`

## Setup

### 1. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Groq

Copy `.env.example` to `.env`:

Windows:

```bash
copy .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Then put your real key in `.env`:

```env
GROQ_API_KEY=your_real_key
```

Never commit `.env` to GitHub.

### 4. Run

```bash
streamlit run app.py
```

The browser should open the Streamlit application.

## Demo

The app starts with built-in mock participants and a sample hackathon project.

Click:

```text
Build HackOps Team
```

The workflow runs from profile parsing through sprint generation.

To test your own data, uncheck **Use built-in mock data**, enter a project idea, and provide at least four participant blocks.

## AI responsibilities

Groq is used for:

- Messy bio interpretation
- Project requirement analysis
- Sprint-plan generation

## Python responsibilities

Python handles:

- Streamlit UI
- Input validation
- Embedding orchestration
- FAISS indexing/search
- Team selection logic
- Team coverage scoring
- JSON parsing and validation
- Workflow orchestration

## FAISS

FAISS is used locally with normalized vectors and inner-product similarity. No hosted vector database is required.

## Structured JSON

AI modules request JSON and parse the response before it moves to the next workflow stage. The final application also exposes the complete structured result as a downloadable JSON file.

## GitHub URL note

The MVP accepts a GitHub field in the profile data model, but it does not scrape GitHub repositories. This keeps the first version focused and avoids introducing GitHub API authentication/rate-limit complexity. A future GitHub connector can populate the same profile-parser input without changing the rest of the architecture.

## Streamlit Cloud deployment

1. Push these files to a GitHub repository.
2. Create a Streamlit Cloud app from the repository.
3. Select `app.py` as the main file.
4. Add the secret:

```toml
GROQ_API_KEY = "your_real_key"
```

The application code reads the same environment variable, so it works with both `.env` locally and Streamlit secrets/environment configuration.

## Limitations of the MVP

- Team formation uses deterministic Python scoring after semantic retrieval; it is not a global optimization solver.
- GitHub URLs are stored but not scraped.
- FAISS is in-memory during the Streamlit session.
- The embedding model is downloaded on first use.
- Team-fit scoring is a heuristic and should be treated as decision support, not an objective measurement.

## Future enhancements

- GitHub API integration
- Persistent participant database
- Persistent FAISS index
- Multi-team optimization
- Skill-level weighting
- Availability/time-zone constraints
- Judge rubric matching
- Automatic GitHub repository creation
- Task tracking and teammate collaboration
