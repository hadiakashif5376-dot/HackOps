import json
import streamlit as st

from mock_data import MOCK_PARTICIPANTS, MOCK_PROJECT
from profile_parser import parse_participant
from project_analyzer import analyze_project
from vector_store import build_profile_index, search_candidates
from team_matcher import form_team
from team_balance import evaluate_team
from sprint_planner import generate_sprint_plan
from utils import validate_participants

st.set_page_config(page_title="HackOps", page_icon="🚀", layout="wide")

st.markdown("""
<style>
.block-container{max-width:1180px;padding-top:2rem;padding-bottom:4rem}
.h-title{font-size:2.1rem;font-weight:800;letter-spacing:-1px;margin-bottom:.1rem}
.h-sub{color:#667085;margin-bottom:1.6rem}
.stepper{display:flex;align-items:center;margin:.5rem 0 2rem}
.step-item{display:flex;align-items:center;flex:1}
.step-circle{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;border:1px solid #d0d5dd;background:#fff;color:#667085;flex-shrink:0}
.step-circle.active{background:#111827;color:#fff;border-color:#111827}
.step-circle.done{background:#12b76a;color:#fff;border-color:#12b76a}
.step-label{margin-left:8px;font-size:.78rem;font-weight:600;color:#667085;white-space:nowrap}
.step-label.active{color:#111827}.step-line{height:1px;background:#d0d5dd;flex:1;margin:0 10px}.step-line.done{background:#12b76a}
.card{border:1px solid #eaecf0;border-radius:14px;padding:1rem 1.1rem;background:#fff;margin-bottom:.7rem}
.pname{font-weight:700;font-size:1rem}.meta{color:#667085;font-size:.86rem;line-height:1.45}
.badge{display:inline-block;padding:.25rem .6rem;border-radius:999px;background:#f2f4f7;color:#344054;font-size:.8rem;font-weight:700}
.role{color:#475467;font-size:.88rem;font-weight:600}
.role-badge{display:inline-block;padding:.15rem .55rem;border-radius:999px;font-size:.72rem;font-weight:700;margin-left:.4rem;vertical-align:middle}
.role-badge.leader{background:#fef3c7;color:#92400e}
.role-badge.member{background:#eef2ff;color:#3730a3}
</style>
""", unsafe_allow_html=True)


def init_state():
    defaults = {
        "step": 1, "project_idea": "", "participants": [],
        "result": None, "analysis_complete": False, "use_mock": False,
        "participant_role_choice": "Member",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_workflow():
    st.session_state.step = 1
    st.session_state.project_idea = ""
    st.session_state.participants = []
    st.session_state.result = None
    st.session_state.analysis_complete = False
    st.session_state.participant_role_choice = "Member"


def stepper(current):
    steps = [("01", "PARTICIPANTS"), ("02", "MATCH"),
             ("03", "BALANCE"), ("04", "LAUNCH")]
    html = '<div class="stepper">'
    for i, (num, label) in enumerate(steps, 1):
        cls = "done" if i < current else ("active" if i == current else "")
        txt = "✓" if i < current else num
        lcls = "active" if i == current else ""
        html += f'<div class="step-item"><div><div class="step-circle {cls}">{txt}</div><div class="step-label {lcls}">{label}</div></div>'
        if i < len(steps):
            html += f'<div class="step-line {"done" if i < current else ""}"></div>'
        html += '</div>'
    st.markdown(html + '</div>', unsafe_allow_html=True)


def get_leader():
    for p in st.session_state.participants:
        if p.get("role") == "leader":
            return p
    return None


def participant_card(i, p):
    name = p.get("name", "Unnamed")
    bio = p.get("bio", "") or "No bio provided"
    github = p.get("github", "")
    is_leader = p.get("role") == "leader"
    role_badge = f'<span class="role-badge {"leader" if is_leader else "member"}">{"👑 Leader" if is_leader else "🙋 Member"}</span>'
    c1, c2 = st.columns([5, 1])
    with c1:
        link = f"<br>🔗 {github}" if github else ""
        st.markdown(
            f'<div class="card"><div class="pname">👤 {name}{role_badge}</div><div class="meta">{bio}{link}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        if st.button("Remove", key=f"remove_{i}", use_container_width=True):
            removed = st.session_state.participants.pop(i)
            if removed.get("role") == "leader":
                st.session_state.project_idea = ""
            st.rerun()


init_state()

st.markdown('<div class="h-title">🚀 HackOps</div>', unsafe_allow_html=True)
st.markdown('<div class="h-sub">AI-powered hackathon team formation and 48-hour launch planning</div>', unsafe_allow_html=True)
stepper(st.session_state.step)

with st.sidebar:
    st.markdown("### HackOps")
    st.caption("Build a balanced 4-person hackathon team.")
    mock = st.checkbox("Use built-in demo data", value=st.session_state.use_mock)
    if mock != st.session_state.use_mock:
        st.session_state.use_mock = mock
        if mock:
            demo_participants = [dict(p) for p in MOCK_PARTICIPANTS]
            if demo_participants:
                demo_participants[0].setdefault("role", "leader")
                demo_participants[0]["project_idea"] = MOCK_PROJECT
                for p in demo_participants[1:]:
                    p.setdefault("role", "member")
            st.session_state.project_idea = MOCK_PROJECT
            st.session_state.participants = demo_participants
            st.session_state.result = None
            st.session_state.analysis_complete = False
            st.session_state.step = 1
            st.session_state.participant_role_choice = "Member"
        else:
            reset_workflow()
    if st.button("↻ Start over", use_container_width=True):
        reset_workflow()
        st.rerun()

# STEP 1 — PARTICIPANTS
if st.session_state.step == 1:
    st.markdown("## 01 — Participants")
    st.write("Add every hacker separately. Mark one participant as the **Leader** — "
              "the leader provides the hackathon project idea, which every member can see below.")
    count = len(st.session_state.participants)
    st.markdown(f'<span class="badge">{count} / 4 minimum participants</span>', unsafe_allow_html=True)

    leader = get_leader()
    st.markdown("### Project idea")
    if leader and st.session_state.project_idea.strip():
        st.markdown(
            f'<div class="card"><b>🚀 Project idea — set by {leader.get("name", "the Leader")}</b>'
            f'<br><span class="meta">{st.session_state.project_idea}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No project idea yet. Add a **Leader** below to set the hackathon project idea — members will see it here.")

    st.divider()
    st.markdown("### Add participant")

    leader_exists = leader is not None
    role_options = ["Member", "Leader"] if not leader_exists else ["Member"]
    if leader_exists:
        st.caption(f"'{leader.get('name', 'A leader')}' is already the team leader. New participants join as members.")
    if st.session_state.participant_role_choice not in role_options:
        st.session_state.participant_role_choice = "Member"
    role_choice = st.radio("Participant type *", role_options, horizontal=True, key="participant_role_choice")

    with st.form("participant_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Name *", placeholder="e.g. Hadia")
        with c2:
            github = st.text_input("GitHub URL (optional)", placeholder="https://github.com/username")
        bio = st.text_area("Bio / skills *", height=120,
                           placeholder="e.g. Frontend developer with React, JavaScript and Streamlit experience.")
        idea = ""
        if role_choice == "Leader":
            st.markdown("---")
            idea = st.text_area(
                "Hackathon project idea * (as the team leader)", height=140,
                placeholder="Example: Build an AI-powered daily footstep counter that tracks walking activity and gives simple insights."
            )
        add = st.form_submit_button("＋ Add Participant", type="primary", use_container_width=True)

    if add:
        if not name.strip():
            st.error("Please enter the participant's name.")
        elif not bio.strip() and not github.strip():
            st.error("Add a bio/skills description or a GitHub URL.")
        elif role_choice == "Leader" and not idea.strip():
            st.error("As the team leader, please provide the hackathon project idea.")
        else:
            participant = {
                "name": name.strip(),
                "bio": bio.strip(),
                "github": github.strip(),
                "role": "leader" if role_choice == "Leader" else "member",
            }
            if role_choice == "Leader":
                participant["project_idea"] = idea.strip()
                st.session_state.project_idea = idea.strip()
                st.session_state.participant_role_choice = "Member"
            st.session_state.participants.append(participant)
            st.success(f"{name.strip()} added successfully.")
            st.rerun()

    st.divider()
    st.markdown("### Your participants")
    if not st.session_state.participants:
        st.markdown('<div class="card"><b>No participants added yet.</b><br><span class="meta">Add at least 4 participants (including one Leader) to form a team.</span></div>', unsafe_allow_html=True)
    else:
        for i, p in enumerate(st.session_state.participants):
            participant_card(i, p)

    st.divider()
    ready = count >= 4 and bool(st.session_state.project_idea.strip())
    c1, _ = st.columns([1, 1])
    with c1:
        if st.button("Continue →", type="primary", disabled=not ready, use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    if count < 4:
        n = 4 - count
        st.warning(f"Add {n} more participant{'s' if n != 1 else ''} to continue.")
    elif not st.session_state.project_idea.strip():
        st.warning("Add a team Leader with a project idea to continue.")

# STEP 2 — AI MATCH
elif st.session_state.step == 2:
    st.markdown("## 02 — AI Match")
    st.write("HackOps combines AI profile understanding, semantic search and complementary-role scoring.")
    if not st.session_state.analysis_complete:
        st.markdown('<div class="card"><b>Ready to build the team?</b><br><span class="meta">This runs profile parsing, project analysis, FAISS search, team matching, balance evaluation and sprint planning.</span></div>', unsafe_allow_html=True)
        if st.button("🚀 Build HackOps Team", type="primary", use_container_width=True):
            try:
                participants = st.session_state.participants
                validate_participants(participants)
                progress = st.progress(0)
                status = st.empty()
                status.write("1/7 Understanding participant profiles...")
                profiles = [parse_participant(p) for p in participants]
                progress.progress(15)
                status.write("2/7 Analyzing project requirements...")
                project = analyze_project(st.session_state.project_idea)
                progress.progress(30)
                status.write("3/7 Creating semantic profile index...")
                index, indexed_profiles = build_profile_index(profiles)
                progress.progress(45)
                status.write("4/7 Searching for relevant candidates...")
                candidates = search_candidates(index, indexed_profiles, project, top_k=min(len(indexed_profiles), 10))
                progress.progress(60)
                status.write("5/7 Forming complementary 4-person team...")
                team = form_team(candidates, project, team_size=4)
                progress.progress(75)
                status.write("6/7 Evaluating team balance...")
                balance = evaluate_team(team, project)
                progress.progress(88)
                status.write("7/7 Generating 48-hour launch plan...")
                sprint = generate_sprint_plan(team, project, balance)
                progress.progress(100)
                st.session_state.result = {"project": project, "profiles": profiles, "candidates": candidates, "team": team, "balance": balance, "sprint": sprint}
                st.session_state.analysis_complete = True
                status.success("HackOps team formation completed.")
                st.rerun()
            except Exception as exc:
                st.error(f"HackOps could not complete the analysis: {exc}")
    else:
        team = st.session_state.result["team"]
        st.success("Your recommended 4-person squad is ready.")
        st.markdown("### Recommended squad")
        for i, member in enumerate(team, 1):
            c1, c2 = st.columns([1, 5])
            with c1: st.markdown(f"### {i:02d}")
            with c2:
                name = member.get("name", "Unnamed")
                role = member.get("assigned_role") or member.get("primary_role", "Team Member")
                skills = member.get("skills", [])
                reason = member.get("selection_reason", "")
                st.markdown(f"**{name}**")
                st.markdown(f'<div class="role">{role}</div>', unsafe_allow_html=True)
                if skills: st.caption(" • ".join(skills[:8]))
                if reason: st.write(reason)
            st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Change participants", use_container_width=True):
                st.session_state.analysis_complete = False
                st.session_state.result = None
                st.session_state.step = 1
                st.rerun()
        with c2:
            if st.button("View team balance →", type="primary", use_container_width=True):
                st.session_state.step = 3
                st.rerun()

# STEP 3 — TEAM BALANCE
elif st.session_state.step == 3:
    st.markdown("## 03 — Team Balance")
    st.write("Understand the team's coverage, strengths and remaining gaps.")
    if not st.session_state.result:
        st.warning("Build a team first.")
        if st.button("Go to AI Match →", type="primary"): st.session_state.step = 2; st.rerun()
    else:
        balance = st.session_state.result["balance"]
        overall = balance.get("overall_score", balance.get("fit_score", 0))
        coverage = balance.get("coverage_score", 0)
        diversity = balance.get("role_diversity_score", 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Overall team fit", f"{overall:.0f}/100")
        c2.metric("Capability coverage", f"{coverage:.0f}/100")
        c3.metric("Role diversity", f"{diversity:.0f}/100")
        st.divider()
        left, right = st.columns(2)
        with left:
            st.markdown("### ✅ Strengths")
            for x in balance.get("strengths", []) or ["No specific strengths returned."]: st.success(str(x))
        with right:
            st.markdown("### ⚠️ Gaps")
            gaps = balance.get("gaps", [])
            if gaps:
                for x in gaps: st.warning(str(x))
            else: st.success("No major capability gaps detected.")
        st.divider()
        if st.button("Generate 48-hour launch plan →", type="primary", use_container_width=True): st.session_state.step = 4; st.rerun()
        if st.button("← Back to match", use_container_width=True): st.session_state.step = 2; st.rerun()

# STEP 4 — LAUNCH
else:
    st.markdown("## 04 — 48-Hour Launch")
    st.write("Your team is formed. HackOps now turns the idea into an execution plan.")
    if not st.session_state.result:
        st.warning("Build and evaluate a team first.")
    else:
        result = st.session_state.result
        project, sprint = result["project"], result["sprint"]
        st.markdown("### Project")
        st.markdown(f'<div class="card"><b>{project.get("summary", "Hackathon project")}</b><br><br><span class="meta">MVP Goal: {project.get("mvp_goal", "Not specified")}</span></div>', unsafe_allow_html=True)
        st.markdown("### 48-hour roadmap")
        for phase in sprint.get("phases", []) or []:
            title = phase.get("title", phase.get("name", "Phase"))
            timebox = phase.get("timebox", "")
            with st.expander(f"{title}{' — ' + timebox if timebox else ''}", expanded=True):
                if phase.get("objective"): st.markdown(f"**Objective:** {phase['objective']}")
                for task in phase.get("tasks", []) or []:
                    if isinstance(task, dict):
                        text = f"- **{task.get('task', 'Task')}**"
                        if task.get("owner"): text += f" — Owner: {task['owner']}"
                        if task.get("deliverable"): text += f" — Deliverable: {task['deliverable']}"
                        st.markdown(text)
                    else: st.markdown(f"- {task}")
        st.divider()
        st.markdown("### Milestones")
        for m in sprint.get("milestones", []) or []:
            if isinstance(m, dict):
                text = f"**{m.get('name', 'Milestone')}**"
                if m.get("target_time"): text += f" — {m['target_time']}"
                if m.get("deliverable"): text += f"<br><span class='meta'>{m['deliverable']}</span>"
                st.markdown(text, unsafe_allow_html=True)
            else: st.markdown(f"- {m}")
        st.divider()
        st.markdown("### 🎤 Demo-day checklist")
        for i, item in enumerate(sprint.get("demo_checklist", []) or []): st.checkbox(str(item), key=f"demo_{i}")
        raw = {"project": project, "team": result["team"], "balance": result["balance"], "sprint": sprint}
        st.download_button("⬇ Download HackOps JSON", json.dumps(raw, indent=2, ensure_ascii=False), "hackops_result.json", "application/json", use_container_width=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Team balance", use_container_width=True): st.session_state.step = 3; st.rerun()
        with c2:
            if st.button("🚀 Start a new HackOps project", type="primary", use_container_width=True): reset_workflow(); st.rerun()
