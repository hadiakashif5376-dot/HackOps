PROFILE_PROMPT = """
Parse this hackathon participant into structured JSON.

Name: {name}
Bio: {bio}
GitHub: {github}

Return exactly this shape:
{{
  "primary_role": "one concise role",
  "skills": ["skill1", "skill2"],
  "experience_level": "Beginner|Intermediate|Advanced",
  "interests": ["interest1"],
  "preferences": ["preference1"]
}}

Rules:
- Extract only information supported by the bio/GitHub text.
- Do not invent technologies.
- Normalize obvious synonyms.
- Keep skills concise.
"""

PROJECT_PROMPT = """
Analyze this hackathon idea for a realistic 48-hour MVP.

Project idea:
{project_idea}

Return exactly this JSON shape:
{{
  "summary": "one or two sentence summary",
  "mvp_goal": "focused MVP goal",
  "required_roles": ["AI/ML", "Backend", "Frontend", "Product/UI"],
  "required_skills": ["Python", "APIs", "React"],
  "critical_capabilities": ["AI", "Backend", "Frontend", "UI/UX"],
  "priorities": [
    {{"capability": "AI", "priority": "High"}},
    {{"capability": "Backend", "priority": "High"}}
  ]
}}

Rules:
- Focus on what is necessary to build a demoable MVP.
- Do not over-engineer.
- Required roles should be useful for team formation.
"""

SPRINT_PROMPT = """
Create a practical 48-hour hackathon sprint plan from the following structured data.

PROJECT:
{project}

TEAM:
{team}

TEAM BALANCE:
{balance}

Return exactly this JSON shape:
{{
  "overview": "short strategy",
  "phases": [
    {{
      "time_window": "Hour 0-2",
      "title": "Kickoff & Scope",
      "goal": "goal",
      "tasks": [
        {{
          "owner": "person name",
          "task": "specific task",
          "deliverable": "concrete output"
        }}
      ]
    }}
  ],
  "milestones": [
    {{
      "time": "Hour 16",
      "deliverable": "working integrated prototype"
    }}
  ],
  "demo_checklist": [
    "Test happy path",
    "Prepare 2-minute demo"
  ]
}}

Rules:
- Cover the full 48 hours.
- Give every team member meaningful ownership.
- Keep the MVP focused.
- Include integration, testing, deployment and demo preparation.
- Do not assign tasks unrelated to a person's skills.
- Use realistic time boxes.
"""
