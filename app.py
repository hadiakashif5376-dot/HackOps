import json
import streamlit as st

from mock_data import MOCK_PARTICIPANTS, MOCK_PROJECT
from profile_parser import parse_participant
from project_analyzer import analyze_project
from vector_store import build_profile_index, search_candidates
from team_matcher import form_team
from team_balance import evaluate_team
from sprint_planner import generate_sprint_plan
from utils import load_env, safe_json, validate_participants

load_env()

st.set_page_config(page_title="HackOps", page_icon="🚀", layout="wide")

st.title("🚀 HackOps")
st.subheader("AI Hackathon Team Formation & 48-Hour Launch Engine")
st.write("Turn messy participant profiles and a hackathon idea into a balanced 4-person team and an executable 48-hour plan.")

with st.sidebar:
    st.header("Demo / Input")
    use_mock = st.checkbox("Use built-in mock data", value=True)
    st.caption("For a real hackathon, add 4–20 participant profiles below.")

if use_mock:
    raw_participants = MOCK_PARTICIPANTS
    project_idea = MOCK_PROJECT
else:
    project_idea = st.text_area(
        "Hackathon project idea",
        placeholder="Example: Build an AI assistant that helps students discover and apply for scholarships.",
        height=120,
    )
    participant_text = st.text_area(
        "Participants",
        placeholder="One participant per block. Example:\nName: Ali\nBio: Python developer with ML and FastAPI experience.\n\nName: Sara\nBio: React frontend developer...",
        height=320,
    )
    raw_participants = []
    blocks = [b.strip() for b in participant_text.split("\n\n") if b.strip()]
    for i, block in enumerate(blocks, start=1):
        lines = block.splitlines()
        name = lines[0].replace("Name:", "").strip() if lines else f"Participant {i}"
        bio = "\n".join(lines[1:]).replace("Bio:", "").strip() if len(lines) > 1 else block
        raw_participants.append({"name": name, "bio": bio})

run = st.button("Build HackOps Team", type="primary", use_container_width=True)

if run:
    if not project_idea.strip():
        st.error("Please provide a project idea.")
        st.stop()

    if len(raw_participants) < 4:
        st.error("HackOps needs at least 4 participants.")
        st.stop()

    try:
        validate_participants(raw_participants)

        progress = st.progress(0)
        status = st.empty()

        status.write("1/7 Parsing participant profiles...")
        profiles = [parse_participant(p) for p in raw_participants]
        progress.progress(15)

        status.write("2/7 Analyzing project requirements...")
        project = analyze_project(project_idea)
        progress.progress(30)

        status.write("3/7 Creating local FAISS profile index...")
        index, metadata = build_profile_index(profiles)
        progress.progress(45)

        status.write("4/7 Retrieving relevant candidates...")
        candidates = search_candidates(index, metadata, project, top_k=min(len(profiles), 12))
        progress.progress(60)

        status.write("5/7 Forming complementary 4-person team...")
        team = form_team(candidates, project, team_size=4)
        progress.progress(72)

        status.write("6/7 Evaluating team coverage...")
        balance = evaluate_team(team, project)
        progress.progress(84)

        status.write("7/7 Generating 48-hour sprint...")
        sprint = generate_sprint_plan(team, project, balance)
        progress.progress(100)
        status.success("HackOps plan generated.")

        st.session_state["result"] = {
            "profiles": profiles,
            "project": project,
            "candidates": candidates,
            "team": team,
            "balance": balance,
            "sprint": sprint,
        }

    except Exception as exc:
        st.error(f"Could not complete the workflow: {exc}")
        st.exception(exc)

result = st.session_state.get("result")

if result:
    project = result["project"]
    team = result["team"]
    balance = result["balance"]
    sprint = result["sprint"]

    st.divider()
    st.header("01 — Project Understanding")
    st.write(project.get("summary", ""))
    c1, c2, c3 = st.columns(3)
    c1.metric("MVP goal", project.get("mvp_goal", "—"))
    c2.metric("Required roles", len(project.get("required_roles", [])))
    c3.metric("Critical capabilities", len(project.get("critical_capabilities", [])))

    with st.expander("Project requirements"):
        st.json(project)

    st.header("02 — Recommended 4-Person Squad")
    cols = st.columns(4)
    for col, member in zip(cols, team):
        with col:
            st.markdown(f"### {member.get('name', 'Member')}")
            st.write(f"**Role:** {member.get('assigned_role', member.get('primary_role', '—'))}")
            st.write(f"**Experience:** {member.get('experience_level', '—')}")
            st.write("**Skills:** " + ", ".join(member.get("skills", [])[:6]))
            st.caption(member.get("selection_reason", ""))

    st.header("03 — Team Balance")
    score = float(balance.get("overall_score", 0))
    st.metric("Overall Team Fit", f"{score:.0f}%")
    st.progress(max(0, min(100, int(score))))

    left, right = st.columns(2)
    with left:
        st.subheader("Coverage")
        for item in balance.get("coverage", []):
            status_icon = "✅" if item.get("covered") else "⚠️"
            st.write(f"{status_icon} **{item.get('capability')}** — {item.get('coverage_score', 0)}%")
    with right:
        st.subheader("Strengths & Gaps")
        for item in balance.get("strengths", []):
            st.write("✅ " + item)
        for item in balance.get("gaps", []):
            st.write("⚠️ " + item)

    with st.expander("Detailed balance JSON"):
        st.json(balance)

    st.header("04 — 48-Hour Sprint Roadmap")
    st.write(sprint.get("overview", ""))

    for phase in sprint.get("phases", []):
        st.subheader(f"{phase.get('time_window', '')} — {phase.get('title', '')}")
        st.write(phase.get("goal", ""))
        for task in phase.get("tasks", []):
            st.markdown(
                f"- **{task.get('owner', 'Team')}** — {task.get('task', '')} "
                f"→ `{task.get('deliverable', '')}`"
            )

    st.subheader("Milestones")
    for milestone in sprint.get("milestones", []):
        st.write(f"🏁 **{milestone.get('time', '')}:** {milestone.get('deliverable', '')}")

    st.subheader("Demo-Day Checklist")
    for item in sprint.get("demo_checklist", []):
        st.checkbox(item, key="demo_" + str(abs(hash(item))))

    st.subheader("Raw Structured JSON")
    st.download_button(
        "Download result JSON",
        data=json.dumps(result, indent=2, ensure_ascii=False),
        file_name="hackops_result.json",
        mime="application/json",
    )
    st.code(safe_json(result), language="json")
