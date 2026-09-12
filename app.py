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

TEAM_SIZE_MEMBERS = 3  # each team = 1 Leader + this many Members

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
.leader-card{border:2px solid #fbbf24;border-radius:14px;padding:1rem 1.1rem;background:#fffbeb;margin-bottom:.5rem}
.leader-crown{font-size:1.1rem}
.project-title{font-weight:800;font-size:1.05rem;margin-bottom:.15rem}
</style>
""", unsafe_allow_html=True)


def init_state():
    defaults = {
        "step": 1, "participants": [],
        "result": None, "analysis_complete": False, "use_mock": False,
        "participant_role_choice": "Member", "selected_team_idx": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_workflow():
    st.session_state.step = 1
    st.session_state.participants = []
    st.session_state.result = None
    st.session_state.analysis_complete = False
    st.session_state.participant_role_choice = "Member"
    st.session_state.selected_team_idx = 0


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


def get_leaders():
    return [p for p in st.session_state.participants if p.get("role") == "leader"]


def get_members():
    return [p for p in st.session_state.participants if p.get("role") != "leader"]


def participant_card(i, p):
    name = p.get("name", "Unnamed")
    bio = p.get("bio", "") or "No bio provided"
    github = p.get("github", "")
    is_leader = p.get("role") == "leader"
    role_badge = f'<span class="role-badge {"leader" if is_leader else "member"}">{"👑 Leader" if is_leader else "🙋 Member"}</span>'
    idea = p.get("project_idea", "")
    idea_html = f'<br><b>💡 Idea:</b> {idea}' if is_leader and idea else ""
    c1, c2 = st.columns([5, 1])
    with c1:
        link = f"<br>🔗 {github}" if github else ""
        st.markdown(
            f'<div class="card"><div class="pname">👤 {name}{role_badge}</div><div class="meta">{bio}{link}{idea_html}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        if st.button("Remove", key=f"remove_{i}", use_container_width=True):
            st.session_state.participants.pop(i)
            st.rerun()


init_state()

st.markdown('<div class="h-title">🚀 HackOps</div>', unsafe_allow_html=True)
st.markdown('<div class="h-sub">AI-powered hackathon team formation and 48-hour launch planning</div>', unsafe_allow_html=True)
stepper(st.session_state.step)

with st.sidebar:
    st.markdown("### HackOps")
    st.caption("Match multiple project Leaders with balanced 4-person teams.")
    mock = st.checkbox("Use built-in demo data", value=st.session_state.use_mock)
    if mock != st.session_state.use_mock:
        st.session_state.use_mock = mock
        if mock:
            demo_participants = [dict(p) for p in MOCK_PARTICIPANTS]
            if demo_participants:
                demo_participants[0]["role"] = "leader"
                demo_participants[0]["project_idea"] = MOCK_PROJECT
                for p in demo_participants[1:]:
                    p.setdefault("role", "member")
            st.session_state.participants = demo_participants
            st.session_state.result = None
            st.session_state.analysis_complete = False
            st.session_state.step = 1
            st.session_state.participant_role_choice = "Member"
            st.session_state.selected_team_idx = 0
        else:
            reset_workflow()
    if st.button("↻ Start over", use_container_width=True):
        reset_workflow()
        st.rerun()

# STEP 1 — PARTICIPANTS
if st.session_state.step == 1:
    st.markdown("## 01 — Participants")
    st.write("Add every hacker separately. Any number of participants can be a **Leader** — "
              f"each Leader pitches their own project idea and gets matched a team of {TEAM_SIZE_MEMBERS} Members.")
    count = len(st.session_state.participants)
    leaders = get_leaders()
    members = get_members()
    st.markdown(f'<span class="badge">{count} participants · {len(leaders)} Leader(s) · {len(members)} Member(s)</span>', unsafe_allow_html=True)

    st.markdown("### Projects")
    if leaders:
        for leader in leaders:
            st.markdown(
                f'<div class="leader-card"><div class="project-title">🚀 {leader.get("project_idea", "")[:140]}</div>'
                f'<span class="meta"><span class="leader-crown">👑</span> Led by <b>{leader.get("name", "Unknown")}</b></span></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No projects yet. Add a **Leader** below — their idea will appear here for everyone to see.")

    st.divider()
    st.markdown("### Add participant")
    st.caption("You can add as many Leaders as needed — each running their own project — plus a shared pool of Members.")
    role_choice = st.radio("Participant type *", ["Member", "Leader"], horizontal=True, key="participant_role_choice")

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
                "Hackathon project idea * (as a team leader)", height=140,
                placeholder="Example: Build an AI-powered daily footstep counter that tracks walking activity and gives simple insights."
            )
        add = st.form_submit_button("＋ Add Participant", type="primary", use_container_width=True)

    if add:
        if not name.strip():
            st.error("Please enter the participant's name.")
        elif not bio.strip() and not github.strip():
            st.error("Add a bio/skills description or a GitHub URL.")
        elif role_choice == "Leader" and not idea.strip():
            st.error("As a team leader, please provide the hackathon project idea.")
        else:
            participant = {
                "name": name.strip(),
                "bio": bio.strip(),
                "github": github.strip(),
                "role": "leader" if role_choice == "Leader" else "member",
            }
            if role_choice == "Leader":
                participant["project_idea"] = idea.strip()
            st.session_state.participants.append(participant)
            st.success(f"{name.strip()} added successfully.")
            st.rerun()

    st.divider()
    st.markdown("### Your participants")
    if not st.session_state.participants:
        st.markdown('<div class="card"><b>No participants added yet.</b><br><span class="meta">Add at least one Leader (with a project idea) and 3 Members to form a team.</span></div>', unsafe_allow_html=True)
    else:
        for i, p in enumerate(st.session_state.participants):
            participant_card(i, p)

    st.divider()
    ready = len(leaders) >= 1 and len(members) >= TEAM_SIZE_MEMBERS
    c1, _ = st.columns([1, 1])
    with c1:
        if st.button("Continue →", type="primary", disabled=not ready, use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    if not leaders:
        st.warning("Add at least one Leader with a project idea to continue.")
    elif len(members) < TEAM_SIZE_MEMBERS:
        n = TEAM_SIZE_MEMBERS - len(members)
        st.warning(f"Add {n} more Member{'s' if n != 1 else ''} to form a full team.")

# STEP 2 — AI MATCH
elif st.session_state.step == 2:
    st.markdown("## 02 — AI Match")
    st.write(f"HackOps runs one match per project. Each Leader is paired with the {TEAM_SIZE_MEMBERS} best-fit "
             "Members from the shared pool, using semantic search and complementary-skill scoring.")
    if not st.session_state.analysis_complete:
        st.markdown('<div class="card"><b>Ready to build the teams?</b><br><span class="meta">This runs profile parsing, per-project analysis, FAISS search, team matching, balance evaluation and sprint planning — once for every Leader\'s project.</span></div>', unsafe_allow_html=True)
        if st.button("🚀 Build HackOps Teams", type="primary", use_container_width=True):
            stage = "validating participants"
            try:
                participants = st.session_state.participants
                validate_participants(participants)

                progress = st.progress(0)
                status = st.empty()

                stage = "parsing participant profiles"
                status.write("Understanding participant profiles...")
                all_profiles = []
                for p in participants:
                    profile = parse_participant(p)
                    profile["role"] = p.get("role", "member")
                    if p.get("role") == "leader":
                        profile["project_idea"] = p.get("project_idea", "")
                    all_profiles.append(profile)
                progress.progress(15)

                leader_profiles = [p for p in all_profiles if p.get("role") == "leader"]
                member_pool = [p for p in all_profiles if p.get("role") != "leader"]

                teams = []
                skipped_projects = []
                total = max(1, len(leader_profiles))
                span = 80 / total

                for li, leader_profile in enumerate(leader_profiles, 1):
                    leader_name = leader_profile.get("name", "the Leader")
                    base = 15 + span * (li - 1)

                    stage = f"analyzing the project idea for {leader_name}"
                    status.write(f"Project {li}/{total}: analyzing {leader_name}'s idea...")
                    project = analyze_project(leader_profile.get("project_idea", ""))
                    progress.progress(int(base + span * 0.25))

                    if len(member_pool) < TEAM_SIZE_MEMBERS:
                        skipped_projects.append(leader_name)
                        continue

                    stage = f"matching members for {leader_name}"
                    status.write(f"Project {li}/{total}: matching Members for {leader_name}...")
                    index, indexed_profiles = build_profile_index(member_pool)
                    candidates = search_candidates(index, indexed_profiles, project, top_k=len(indexed_profiles))
                    progress.progress(int(base + span * 0.5))

                    chosen = form_team(candidates, project, team_size=TEAM_SIZE_MEMBERS)
                    chosen_names = {c.get("name") for c in chosen}
                    member_pool = [m for m in member_pool if m.get("name") not in chosen_names]

                    leader_member = dict(leader_profile)
                    leader_member["assigned_role"] = "Team Leader"
                    leader_member["selection_reason"] = "Team Leader — pitched and owns this project idea."
                    full_team = [leader_member] + chosen

                    stage = f"evaluating team balance for {leader_name}"
                    balance = evaluate_team(full_team, project)
                    progress.progress(int(base + span * 0.75))

                    stage = f"generating the launch plan for {leader_name}"
                    sprint = generate_sprint_plan(full_team, project, balance)
                    progress.progress(int(base + span))

                    teams.append({
                        "leader_name": leader_name,
                        "project": project,
                        "team": full_team,
                        "balance": balance,
                        "sprint": sprint,
                    })

                progress.progress(100)
                st.session_state.result = {
                    "teams": teams,
                    "leftover_members": member_pool,
                    "skipped_projects": skipped_projects,
                }
                st.session_state.analysis_complete = True
                st.session_state.selected_team_idx = 0
                status.success("HackOps finished matching all possible teams.")
                st.rerun()
            except Exception as exc:
                st.error(f"HackOps could not complete the analysis while {stage}: {exc}")
    else:
        result = st.session_state.result
        teams = result.get("teams", [])
        leftover = result.get("leftover_members", [])
        skipped = result.get("skipped_projects", [])

        if not teams:
            st.warning("No teams could be formed yet. Add more Members and try again.")
        else:
            st.success(f"{len(teams)} project team{'s' if len(teams) != 1 else ''} matched.")
            for t in teams:
                leader = t["team"][0]
                squad = t["team"][1:]
                st.markdown(
                    f'<div class="leader-card"><div class="project-title">🚀 {t["project"].get("summary", "Project")}</div>'
                    f'<span class="meta"><span class="leader-crown">👑</span> Leader: <b>{leader.get("name", "Unknown")}</b></span></div>',
                    unsafe_allow_html=True,
                )
                for i, member in enumerate(squad, 1):
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

        if leftover:
            if len(leftover) == 1:
                msg = (f"🌟 Great turnout! **{leftover[0].get('name', 'One participant')}** is still free after "
                       "matching. Maybe they'd like to pitch a project idea and step up as a Leader for the next team?")
            else:
                names = ", ".join(m.get("name", "Someone") for m in leftover)
                msg = (f"🌟 Great turnout! **{names}** are still free after matching. Maybe one of them would "
                       "like to pitch a project idea and step up as a Leader for the next team?")
            st.info(msg)

        if skipped:
            st.warning("Not enough Members were left to build a team for: " + ", ".join(skipped) +
                       ". Add more Members to cover every project.")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Change participants", use_container_width=True):
                st.session_state.analysis_complete = False
                st.session_state.result = None
                st.session_state.step = 1
                st.rerun()
        with c2:
            if st.button("View team balance →", type="primary", use_container_width=True, disabled=not teams):
                st.session_state.step = 3
                st.rerun()

# STEP 3 — TEAM BALANCE
elif st.session_state.step == 3:
    st.markdown("## 03 — Team Balance")
    st.write("Understand each project team's coverage, strengths and remaining gaps.")
    teams = (st.session_state.result or {}).get("teams", [])
    if not teams:
        st.warning("Build teams first.")
        if st.button("Go to AI Match →", type="primary"): st.session_state.step = 2; st.rerun()
    else:
        if len(teams) > 1:
            idx = st.selectbox(
                "Select a project team",
                options=list(range(len(teams))),
                index=min(st.session_state.selected_team_idx, len(teams) - 1),
                format_func=lambda i: f"👑 {teams[i]['leader_name']}'s project",
            )
            st.session_state.selected_team_idx = idx
        else:
            idx = 0
        t = teams[idx]

        balance = t["balance"]
        overall = balance.get("overall_score", 0)
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
    st.write("Each project team gets its own execution plan.")
    teams = (st.session_state.result or {}).get("teams", [])
    if not teams:
        st.warning("Build and evaluate teams first.")
    else:
        if len(teams) > 1:
            idx = st.selectbox(
                "Select a project team",
                options=list(range(len(teams))),
                index=min(st.session_state.selected_team_idx, len(teams) - 1),
                format_func=lambda i: f"👑 {teams[i]['leader_name']}'s project",
                key="launch_team_select",
            )
            st.session_state.selected_team_idx = idx
        else:
            idx = 0
        t = teams[idx]
        project, sprint = t["project"], t["sprint"]

        st.markdown("### Project")
        st.markdown(f'<div class="card"><b>{project.get("summary", "Hackathon project")}</b><br><br><span class="meta">MVP Goal: {project.get("mvp_goal", "Not specified")}</span></div>', unsafe_allow_html=True)
        st.markdown("### 48-hour roadmap")
        for phase in sprint.get("phases", []) or []:
            title = phase.get("title", phase.get("name", "Phase"))
            timebox = phase.get("timebox", phase.get("time_window", ""))
            with st.expander(f"{title}{' — ' + timebox if timebox else ''}", expanded=True):
                if phase.get("objective") or phase.get("goal"):
                    st.markdown(f"**Objective:** {phase.get('objective') or phase.get('goal')}")
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
                text = f"**{m.get('name', m.get('time', 'Milestone'))}**"
                if m.get("target_time"): text += f" — {m['target_time']}"
                if m.get("deliverable"): text += f"<br><span class='meta'>{m['deliverable']}</span>"
                st.markdown(text, unsafe_allow_html=True)
            else: st.markdown(f"- {m}")
        st.divider()
        st.markdown("### 🎤 Demo-day checklist")
        for i, item in enumerate(sprint.get("demo_checklist", []) or []): st.checkbox(str(item), key=f"demo_{idx}_{i}")
        raw = {"project": project, "team": t["team"], "balance": t["balance"], "sprint": sprint}
        st.download_button("⬇ Download this team's JSON", json.dumps(raw, indent=2, ensure_ascii=False), f"hackops_{t['leader_name']}.json", "application/json", use_container_width=True, key=f"download_{idx}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Team balance", use_container_width=True): st.session_state.step = 3; st.rerun()
        with c2:
            if st.button("🚀 Start a new HackOps project", type="primary", use_container_width=True): reset_workflow(); st.rerun()
