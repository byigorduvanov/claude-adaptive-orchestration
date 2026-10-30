#!/bin/zsh
# Build two blind arm config dirs with a random old/new mapping (KEY.txt, never printed) and per-arm task dirs.
# Usage: AB=<workdir> OLD_CONFIG=<dir> NEW_CONFIG=<dir> TASKS="t1 t2" setup_arms.sh
# Each config dir holds CLAUDE.md, settings.json and optionally agents/. Both arms share one copy of skills and memory,
# so the rules are the only difference. Claude-mem-style plugins stay off: their search can hold the answer key.
set -eu
AB=${AB:?} OLD_CONFIG=${OLD_CONFIG:?} NEW_CONFIG=${NEW_CONFIG:?} TASKS=${TASKS:?}
# Claude Code keys its project dir on the cwd, so run this from the directory the arms will run in, or set CWD_KEY.
CWD_KEY=${CWD_KEY:-$(print -rn -- "$PWD" | tr -c 'A-Za-z0-9' '-')}
[[ -e $AB/KEY.txt ]] && { echo "KEY.txt exists; refusing to rebuild"; exit 1; }
mkdir -p "$AB/arms"
if (( RANDOM % 2 )); then printf 'a=new\nb=old\n' > "$AB/KEY.txt"; else printf 'a=old\nb=new\n' > "$AB/KEY.txt"; fi
for arm in a b; do
  kind=$(grep "^$arm=" "$AB/KEY.txt" | cut -d= -f2)
  src=$OLD_CONFIG; [[ $kind == new ]] && src=$NEW_CONFIG
  D=$AB/arms/$arm
  mkdir -p "$D/projects/$CWD_KEY"
  cp "$src/CLAUDE.md" "$src/settings.json" "$D/"
  [[ -d $src/agents ]] && cp -R "$src/agents" "$D/agents"
  [[ -f $HOME/.claude.json ]] && cp "$HOME/.claude.json" "$D/.claude.json"
  [[ -d $HOME/.claude/skills ]] && cp -cR "$HOME/.claude/skills" "$D/skills"
  [[ -d $HOME/.claude/projects/$CWD_KEY/memory ]] && cp -cR "$HOME/.claude/projects/$CWD_KEY/memory" "$D/projects/$CWD_KEY/memory"
  python3 - "$D/settings.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["enabledPlugins"] = {k: False for k in d.get("enabledPlugins", {})}
json.dump(d, open(p, "w"), indent=2)
PY
  for t in ${=TASKS}; do mkdir -p "$AB/$t/$arm"; done
done
echo "arms ready in $AB/arms; give each task a PROMPT.md with {X} for the arm. Do not list arms/ while judging: agents/ gives the mapping away."
