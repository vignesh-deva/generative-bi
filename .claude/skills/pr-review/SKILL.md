# PR Review

Fetch an open pull request from GitHub, perform a thorough code review, and post inline comments + a summary review directly on the PR.

## Trigger

Invoke this skill when the user wants to:
- Review a pull request before merging
- Get AI feedback on a PR
- Says things like "review PR", "review pull request", "review PR #42", "/pr-review"

## Instructions

### Step 1 — Identify the PR

If the user provided a PR number (e.g. `/pr-review 12`), use that.

Otherwise:
1. Get the current branch: `git branch --show-current`
2. Get the remote URL: `git remote get-url origin`
3. Parse the GitHub owner and repo from the remote URL
4. Find the open PR for the current branch using the GitHub API:

```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/{owner}/{repo}/pulls?state=open&head={owner}:{branch}" \
  | python -c "import sys,json; prs=json.load(sys.stdin); print(prs[0]['number'] if prs else 'none')"
```

If no PR is found, inform the user and stop.

Check that `GITHUB_TOKEN` is set in the environment. If missing, tell the user:
> "Set GITHUB_TOKEN in your .env or shell to allow GitHub API access."

### Step 2 — Fetch PR Data

Using the GitHub API, fetch:

**PR metadata:**
```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
```
Extract: title, body, base branch, head branch, author.

**PR diff (file changes):**
```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github.v3.diff" \
  "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
```

**Existing review comments (to avoid duplicates):**
```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"
```

### Step 3 — Analyse the Diff

Read the full diff carefully. For each changed file, evaluate:

**Code Quality**
- Logic errors, off-by-one errors, unhandled edge cases
- Redundant or dead code
- Functions that are too long or do too many things

**Security**
- SQL injection, command injection, XSS risks
- Hardcoded secrets or credentials
- Unvalidated user input reaching sensitive operations

**Performance**
- N+1 queries or unnecessary DB calls in loops
- Missing indexes hinted by query patterns
- Heavy operations on the hot path

**Architecture & Design**
- Does the change align with the existing patterns in the codebase?
- Are new abstractions justified or over-engineered?
- Is business logic leaking into the wrong layer?

**Project-Specific Checks (generative-bi)**
- Agent pipeline integrity: does the change break Classifier → RAG → SQL Agent → Validation → Insight flow?
- SSE streaming: are responses still streamed correctly?
- SQLite safety: no raw string interpolation in queries
- New backend folders missing from `backend/<folder>/README.md`

**Style & Maintainability**
- Unclear variable/function names
- Missing or misleading comments on non-obvious logic
- TODO/FIXME left in production code paths

### Step 4 — Draft Review Comments

For each issue found, create an **inline comment** with:
- `path`: the file path relative to repo root
- `position` or `line`: the line number in the diff where the issue is
- `body`: the comment text

Comment format:
```
**[severity]** Brief title

Explanation of the issue and why it matters.

```suggestion
// corrected code if applicable
```
```

Severity levels: `[critical]`, `[major]`, `[minor]`, `[nit]`

Only comment on lines that actually exist in the diff. Skip issues already covered by existing review comments.

Aim for: thorough but not noisy. 3–10 comments is healthy. Avoid nit-picking style for its own sake.

### Step 5 — Post Inline Comments

Post each inline comment to the PR review via GitHub API.

First, create a review in PENDING state:
```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews" \
  -d '{
    "commit_id": "{head_sha}",
    "event": "COMMENT",
    "body": "{summary}",
    "comments": [
      {
        "path": "backend/agents/sql_agent.py",
        "line": 42,
        "body": "**[major]** ..."
      }
    ]
  }'
```

The `head_sha` comes from the PR metadata fetched in Step 2.

### Step 6 — Write the Review Summary

The top-level review body should include:

```markdown
## PR Review — {PR title}

**Branch:** `{head}` → `{base}`
**Files changed:** N

### Summary
1–3 sentences on the overall quality and intent of the PR.

### What's Good
- Positive observations (be specific, not generic)

### Issues Found
| Severity | File | Issue |
|----------|------|-------|
| critical | `path/file.py` | Brief description |
| major    | `path/file.py` | Brief description |

### Recommendation
**Approve / Request Changes / Comment** — one sentence rationale.
```

### Step 7 — Report Back to User

After posting, tell the user:
```
PR #N reviewed.
Posted X inline comments + summary review.
URL: https://github.com/{owner}/{repo}/pull/{pr_number}
```

## Constraints

- Never approve a PR that has `[critical]` or `[major]` issues — use "REQUEST_CHANGES" event instead of "COMMENT"
- Never post duplicate comments on lines already reviewed
- Do not modify any source files during review
- If the diff is very large (>500 changed lines), focus on backend files first, then summarise frontend changes at a high level
- Requires `GITHUB_TOKEN` with `repo` scope in the environment
