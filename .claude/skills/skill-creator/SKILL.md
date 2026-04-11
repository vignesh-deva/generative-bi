# Skill Creator

A skill for creating, testing, and refining new Claude Code skills and workflows.

## Trigger

Use this skill when the user wants to:
- Create a new skill or workflow for Claude Code
- Build a `/slash-command` for their project
- Automate a recurring development task into a reusable skill
- Improve or iterate on an existing skill

## Core Workflow

Follow this structured loop when creating a skill:

### 1. Capture Intent
Before writing anything, understand:
- What should this skill do?
- When should it trigger (what user phrases invoke it)?
- What are the expected inputs and outputs?
- Does it need test cases?

### 2. Interview & Research
Ask targeted questions about:
- Edge cases and failure modes
- Input/output formats
- Success criteria
- Whether this should be project-scoped (`.claude/skills/`) or personal (`~/.claude/skills/`)

### 3. Write SKILL.md
Create the skill file at `.claude/skills/<skill-name>/SKILL.md` (project scope) or `~/.claude/skills/<skill-name>/SKILL.md` (personal scope).

Structure every SKILL.md with:
```markdown
# Skill Name

Brief description of what this skill does and when to use it.

## Trigger

Phrases and contexts that should invoke this skill.

## Instructions

Step-by-step instructions for Claude to follow.
Explain the *why* behind each step — LLMs respond better to reasoning than rigid rules.

## Output Format

What the final output should look like.
```

Key constraints:
- Keep it under 500 lines
- Use "pushy" trigger descriptions that encourage Claude to invoke the skill proactively
- Explain reasoning, not just rules

### 4. Create Test Cases
Draft 2–3 realistic prompts that should trigger the skill. Save to `evals/evals.json` if running formal evals.

### 5. Iterate Based on Feedback
- Generalize from feedback — don't overfit to specific examples
- Remove instructions that don't pull their weight
- Look for repeated patterns that could become reusable steps

## Skill File Location

| Scope    | Path                                      |
|----------|-------------------------------------------|
| Project  | `.claude/skills/<name>/SKILL.md`          |
| Personal | `~/.claude/skills/<name>/SKILL.md`        |

Skills are auto-discovered and live-reloaded — no restart needed after creating or editing.

## Output

After creating a skill:
1. Confirm the file path where it was written
2. Show the trigger phrases so the user knows how to invoke it
3. Suggest 1–2 test prompts to verify it works
