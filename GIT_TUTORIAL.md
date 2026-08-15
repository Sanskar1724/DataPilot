# Git Crash Course — taught with your real mistake

This file teaches git by walking through the exact situation you just lived
through with DataPilot, so every concept maps to something you actually did.

> TL;DR of the whole story:
> You created a branch from a **stale** commit, switched to it, and a bunch of
> files "disappeared". Nothing was deleted — git was showing you the *other*
> branch's version of the project. This guide makes that click forever.

---

## Part 0 — The mental model (read this first)

Git is a **time machine for text files**. It keeps snapshots of your project
called **commits**. Almost every scary git situation is explained by three simple
ideas:

```
YOUR FOLDER (working tree)
        │
        │  git add .          → stage changes (put them in the staging area)
        ▼
STAGING AREA (what will be in the next commit)
        │
        │  git commit -m "msg" → take a snapshot
        ▼
HISTORY (a chain of commits)
```

And on top of that sits the **branch**: a movable label pointing at one commit.
Switching branches = telling git "show me the project as it looked at THAT
commit, and let me continue working from there."

Everything in this guide = understanding those 4 boxes: **working tree, staging
area, history, branch.**

---

## Part 1 — The vocabulary, with the real commands

### 1.1 Repo / init
```powershell
git init              # turn this folder into a git project
git branch -M main    # rename the default branch to "main"
```
A **repo** is just the project folder + the hidden `.git/` folder that stores
all history. Every project (including DataPilot) starts with this.

### 1.2 Working tree vs staging area vs commit
```powershell
git status            # "what's different right now?" — your best friend
git add app/utils/    # stage a folder (pick it up for the next commit)
git add -A            # stage EVERYTHING (be careful — often too much)
git commit -m "feat(core): add logging setup"   # take the snapshot
```
- **Working tree** = files you see in Explorer/VSCode.
- **Staging area** = things you told git "this goes in the next commit".
- **Commit** = a permanent snapshot in history.

You committed 20+ times building DataPilot. Each commit is one "save point".

### 1.3 Commit messages
Good commit messages follow the `type(scope): summary` convention:
```powershell
feat(ui): add dashboard page      # new feature
fix(core): handle mixed date formats   # bug fix
docs: add architecture reference   # documentation
test(ai): cover parser validation  # tests
data: add cafe sales sample        # data files
chore: bump dependencies           # housekeeping
```
You followed exactly this style in your DataPilot history. It makes `git log`
read like a changelog.

### 1.4 Viewing history
```powershell
git log --oneline          # compact list of commits (most recent first)
git log --oneline --graph  # show the branching shape
git show <commit-id>       # see exactly what ONE commit changed
git show <commit-id> --stat  # just the file list + line counts
```
In your real history, `git log --oneline --graph` showed two branches that
splintered off — that's the picture of what went wrong.

---

## Part 2 — Branches (where it all went sideways)

### 2.1 What a branch is
A branch is a **sticky note stuck to a commit**. "main" points at the newest
commit of the main line. When you make a new commit, the sticky note moves
forward.

```powershell
git branch                  # list branches; "*" marks the current one
git branch my-feature       # create a sticky note at your current commit
git switch my-feature       # move to that branch (also: git checkout my-feature)
git switch -c new-branch    # create AND switch in one step
```

### 2.2 The critical rule you broke
> A branch only contains the history of the commit it started from **and
> everything before it** — never commits that were added to a *different*
> branch after the fork.

Concrete version of your mistake:

```
Commits that existed BEFORE the fork:  ✓ present on BOTH branches
Commits added on main AFTER the fork:  ✗ INVISIBLE on the other branch
```

### 2.3 Your real mistake, step by step

```powershell
# 1. You were on "main", history looked like:
#    ... 31ff795 (Update README)  →  ab85670 (cli)  →  5ebdd7a (complete workflow)
#    ^ these two last commits added app/utils/, scripts/, samples/, etc.

# 2. You created a new branch from origin/main = the OLD commit 31ff795:
git switch -c day7-only origin/main
#            ^          ^^^^^^^^^^
#            |          |_ "start from origin/main's position"
#            |             which was 31ff795 — BEFORE the cli/workflow commits!
#            |
#            +_ this brand-new sticky note now sits at 31ff795

# 3. Switching to day7-only told git: "show me the project AT 31ff795"
#    → app/utils, scripts/, test_loader.py, extra samples … were NOT in that
#      commit → git removed them from your folder.
```

The files were **not deleted from the repo**. They still existed on `main`.
They just weren't in the history your new branch pointed at.

### 2.4 How you got them back

```powershell
# Copy specific files from another branch into the current working folder:
git restore --source=main --worktree -- app/utils scripts tests/test_loader.py
#        ^^^^ ^^^^^^        ^^^^^^^^    ^^
#        take from main →   worktree   → these paths

# Alternative: throw away your current work and take a branch's ENTIRE state:
git reset --hard main
```

---

## Part 3 — The recovery commands (in general)

### 3.1 `git restore` — bring back files (safe)
```powershell
git restore <file>                       # discard uncommitted changes to a file
git restore --staged <file>              # unstage a file (keep the changes)
git restore --source=<commit/branch> <file>   # copy a file from another point in history
```
This is what fixed your project. It's **read-only on history** — it never
rewrites commits, only your working folder / staging area.

### 3.2 `git checkout` / `git switch` — move between branches or commits
```powershell
git switch main              # go back to the main line
git switch -c new-branch     # new branch from current position
```
`checkout` is the older spelling; `switch` is clearer. Both change what your
folder shows.

### 3.3 `git merge` — combine two histories
```powershell
git switch main             # go to the branch you want to receive the work
git merge day7-only         # fold day7-only's commits into main
```
A merge creates a "merge commit" joining the two lines. If both branches changed
the same lines differently, git asks you to resolve a **conflict** (you pick
which version to keep, then commit).

### 3.4 `git rebase` — move your branch on top of another (your recommended fix)
```powershell
git switch day7-only
git rebase main
# Replays your day7-only commits on top of main's LATEST commit.
# Result: the missing files appear (they come from main), and your 5 UI commits
# sit neatly on top — one straight line, no messy merge commit.
```
> When to use which: **rebase** = "I want my work based on the newest version".
> **merge** = "I want a record that two lines of work were combined."

---

## Part 4 — Remotes (GitHub)

```powershell
git remote -v                    # see your remotes
git remote add origin https://github.com/USER/datapilot.git  # add GitHub
git push -u origin main          # upload + remember where to push
git push                         # upload after the first time
git pull                         # download other people's/newer commits
git fetch                        # download but DON'T change your folder yet
```

The trap that bit you: **`origin/main` (on GitHub) was behind your local `main`**.
You branched from `origin/main`, trusting it was "the latest" — but it wasn't.
Local and remote can (and often do) drift apart. Always confirm with:

```powershell
git status                # shows: "Your branch is ahead/behind 'origin/main'"
git fetch origin
git log --oneline origin/main -3   # what does GitHub actually have?
```

---

## Part 5 — The golden rules (memorize these)

1. **`git status` before every scary action.** It tells you where you are,
   what's staged, and what's untracked. 90% of confusion dies here.
2. **A branch = a starting commit + only the commits after it on that line.**
   If files "vanish" after a switch, they were never in that branch — go look
   at the branch that had them.
3. **Very little is permanently lost.** Commits are nearly impossible to erase.
   If a commit ever existed, it's findable:
   ```powershell
   git reflog          # "the time machine log" — every move you made, in order
   git reflog --all    # including branch switches and remote updates
   ```
4. **Branch from the latest point** unless you have a reason not to:
   ```powershell
   git switch -c my-new-branch   # from your current HEAD (usually fine)
   # DON'T: git switch -c x origin/main  unless you're SURE origin is current
   ```
5. **Commit small, commit often, write clear messages.** Then `git log` tells
   the story, and `git bisect`/`git restore` become trivial.

---

## Part 6 — Cheat sheet

| Goal                                  | Command                                          |
|---------------------------------------|--------------------------------------------------|
| See state                              | `git status`                                     |
| Stage a file                           | `git add <file>`                                 |
| Stage everything                       | `git add -A`                                     |
| Commit                                 | `git commit -m "msg"`                            |
| List commits                           | `git log --oneline --graph`                      |
| Show a commit's changes                | `git show <id> --stat`                           |
| List branches                          | `git branch`                                     |
| Create + switch branch                 | `git switch -c <name>`                           |
| Switch branch                          | `git switch <name>`                              |
| Bring a file from another branch       | `git restore --source=<branch> --worktree -- <file>` |
| Discard uncommitted changes            | `git restore <file>`                             |
| Merge a branch into current            | `git merge <branch>`                             |
| Replay current branch on another       | `git rebase <branch>`                            |
| See every move you ever made           | `git reflog`                                     |
| Push to GitHub                         | `git push -u origin <branch>`                    |
| Get newer commits                      | `git pull`                                       |

---

## Your homework (5 min, do it in a throwaway folder)

```powershell
mkdir C:\Users\sansk\AppData\Local\Temp\opencode\gittest
cd C:\Users\sansk\AppData\Local\Temp\opencode\gittest
git init
Set-Content a.txt "v1"
git add a.txt; git commit -m "base"

Set-Content a.txt "v2 on main"
git commit -am "main commit"            # -a stages tracked changes too

git switch -c mybranch                  # branch from CURRENT commit (correct way)
Set-Content b.txt "hello"
git add b.txt; git commit -m "add b on mybranch"

git switch main                         # notice: b.txt "disappears"!
dir                                     # ← NOT deleted, just not on this branch
git switch mybranch                     # and b.txt is back

git switch main
git merge mybranch                      # fold it in — now b.txt is on main
dir
```

That exercise reproduces the exact "files disappeared / came back" feeling from
today — safely, in a scratch folder.
