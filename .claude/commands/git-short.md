# Commit (show only)

Look at the current changes and produce a single git command for add + commit.
Do NOT execute it. Just print it.

Steps:
1. Run `git diff` and `git status` to see what changed (read-only, don't stage anything).
2. Write a commit message that is short, concise, and to the point — one line, imperative mood (e.g. "Fix retry logic in tool calls").
3. Output exactly one line, the full command, ready to copy-paste:
4. I dont want a multiple line breakdown with "\" , I WANT SHORT AND CONCISE MESSAGE , no need for love story and NOT -M every fucking line

git add -A && git commit -m "<your message here>"

Nothing else. No explanation, no extra commentary, just that one line.