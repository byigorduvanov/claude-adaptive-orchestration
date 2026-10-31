#!/usr/bin/env python3
"""Run critical-reviewer against known incidents, without its memory, on the terminal claude login."""
import datetime, json, os, re, shutil, subprocess, sys, tempfile

HOME = os.path.expanduser("~")
ROOT = f"{HOME}/.claude/evals/critical-reviewer"
SETTINGS = '{"enabledPlugins":{"claude-mem@thedotmack":false}}'


def claude(args, prompt, cwd):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE_CODE_", "CLAUDE_EFFORT", "ANTHROPIC_"))}
    r = subprocess.run(["claude", "-p", prompt, "--settings", SETTINGS, "--no-session-persistence", "--output-format", "text", *args],
                       cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout + r.stderr


def reviewer_definition():
    text = open(f"{HOME}/.claude/agents/critical-reviewer.md").read()
    body = text.split("---", 2)[2].strip()
    body = re.sub(r"Check the change against the failure classes in your memory\..*?\n\n", "", body, flags=re.S)
    return {"reviewer": {"description": "Reviews a critical change", "prompt": body, "model": "opus", "effort": "medium", "disallowedTools": ["Edit", "Write", "NotebookEdit"]}}


def run_case(case, out):
    repo = os.path.expanduser(case["repo"])
    tmp = tempfile.mkdtemp(prefix="mr-eval-")
    try:
        subprocess.run(f'git -C "{repo}" archive {case["base"]} | tar -x -C "{tmp}"', shell=True, check=True)
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
        subprocess.run("git add -A && git -c user.name=e -c user.email=e@e commit -qm base", shell=True, cwd=tmp, check=True)
        if case.get("patch"):
            subprocess.run(["git", "apply", f"{ROOT}/cases/{case['id']}/{case['patch']}"], cwd=tmp, check=True)
        prompt = f"Use the reviewer subagent on this change in the current directory. Focus: {case['focus']}. `git diff` shows any uncommitted change. Return its findings as they are."
        code, report = claude(["--model", "opus", "--effort", "medium", "--agents", json.dumps(reviewer_definition()), "--permission-mode", "bypassPermissions"], prompt, tmp)
        open(f"{out}/{case['id']}.md", "w").write(report)
        judge = f"A code review report follows. Did it identify this specific defect: {case['expect']}\nAnswer on the first line PASS or FAIL, then one sentence quoting the report.\n\n<report>\n{report[:30000]}\n</report>"
        _, verdict = claude(["--model", "haiku", "--tools", ""], judge, tmp)
        return code, verdict.strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ids = sys.argv[1:] or sorted(os.listdir(f"{ROOT}/cases"))
    out = f"{ROOT}/runs/{datetime.datetime.now():%Y-%m-%d_%H%M}"
    os.makedirs(out, exist_ok=True)
    passed = 0
    for i in ids:
        case = json.load(open(f"{ROOT}/cases/{i}/case.json"))
        code, verdict = run_case(case, out)
        ok = code == 0 and verdict.upper().startswith("PASS")
        passed += ok
        print(f"{i}: {'PASS' if ok else 'FAIL'} exit={code} | {verdict.splitlines()[0][:80] if verdict else ''} | {' '.join(verdict.splitlines()[1:])[:200]}", flush=True)
    print(f"{passed}/{len(ids)} passed, reports in {out}")
    sys.exit(0 if passed == len(ids) else 1)


if __name__ == "__main__":
    main()
