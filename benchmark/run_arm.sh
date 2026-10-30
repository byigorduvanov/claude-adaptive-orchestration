#!/bin/zsh
# Headless run of one arm on one task: AB=<workdir> [EFFORT=high] [CLAUDE_BIN=...] run_arm.sh <task> <arm>
# Run it from the same cwd as the task expects. Background agents need the wait ceiling off or -p kills them after 600 s.
set -eu
task=$1 arm=$2
: ${AB:?}
SID=$(uuidgen | tr 'A-Z' 'a-z')
print -r -- "$SID" > "$AB/$task/$arm/session-id"
PROMPT=$(sed "s/{X}/$arm/g" "$AB/$task/PROMPT.md")
date -u +%FT%TZ > "$AB/$task/$arm/started"
env -i HOME=$HOME USER=$USER LOGNAME=${LOGNAME:-$USER} SHELL=/bin/zsh PATH=$PATH LANG=${LANG:-en_US.UTF-8} TMPDIR=$TMPDIR \
  SSH_AUTH_SOCK=${SSH_AUTH_SOCK:-} ${CLAUDE_CODE_OAUTH_TOKEN:+CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN} \
  CLAUDE_CONFIG_DIR="$AB/arms/$arm" CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 \
  "${CLAUDE_BIN:-$(command -v claude)}" -p "$PROMPT" --setting-sources user,local --effort "${EFFORT:-high}" \
  --session-id "$SID" --permission-mode bypassPermissions --output-format stream-json --verbose \
  > "$AB/$task/$arm/stream.jsonl" 2> "$AB/$task/$arm/stderr.log" < /dev/null
echo "EXIT=$? $task $arm"
[[ -s $AB/$task/$arm/stream.jsonl ]] || { echo "empty stream, see stderr.log"; exit 1; }
