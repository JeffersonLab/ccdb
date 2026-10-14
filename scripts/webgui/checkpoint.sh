#!/usr/bin/env bash
# Save and restore checkpoints of the CCDB working tree without touching git history.
#
#   checkpoint.sh save <NN-name> [gate-result]   write <space>/checkpoints/<NN-name>.patch + .tgz, add an INDEX.md row
#   checkpoint.sh restore <NN-name>              return the working tree to that checkpoint
#
# A checkpoint is the diff of tracked files against HEAD plus a tar of untracked, non-ignored
# files. The workspace and the program plan file are never part of a checkpoint, and restore
# never touches them.
#
# Settings (environment variables):
#   CCDB_SPACE or CKPT_SPACE   the workspace directory; checkpoints go to <space>/checkpoints/ (required)
#   CKPT_PLAN                  the program plan file, relative to the repository (optional, for example ccdb-webgui.md)
#   CKPT_REPO                  the repository (default: the checkout this script lives in)
set -euo pipefail

REPO=${CKPT_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
SPACE=${CKPT_SPACE:-${CCDB_SPACE:-}}
PLAN=${CKPT_PLAN:-}
[ -n "$SPACE" ] || { echo "no workspace: set CCDB_SPACE (or CKPT_SPACE) to the workspace directory"; exit 1; }
DIR=$SPACE/checkpoints
INDEX=$DIR/INDEX.md
SPACE_REL=$(realpath --relative-to="$REPO" "$SPACE")
EXCLUDES=(":(exclude)$SPACE_REL")
[ -n "$PLAN" ] && EXCLUDES+=(":(exclude)$PLAN")

# Untracked files outside the workspace, NUL-separated. grep exits 1 on no match, hence || true.
untracked_list() {
    git -C "$REPO" ls-files -z --others --exclude-standard | grep -zv "^$SPACE_REL/" || true
}

# Data rows of INDEX.md: checkpoint names start with a digit, the header row starts with "name".
index_names() {
    [ -f "$INDEX" ] && grep '^| [0-9]' "$INDEX" | awk -F'|' '{gsub(/ /, "", $2); print $2}' || true
}

save() {
    local name=$1 gate=${2:--}
    if [ -z "$(index_names)" ]; then
        # First save: a modified tracked file other than the plan is someone else's work — stop.
        local foreign
        foreign=$(git -C "$REPO" status --porcelain | awk -v plan="$PLAN" 'substr($0, 1, 2) != "??" && substr($0, 4) != plan')
        if [ -n "$foreign" ]; then
            echo "save refused: the working tree has changes that are not part of this work:"
            echo "$foreign"
            exit 1
        fi
    fi
    mkdir -p "$DIR"
    git -C "$REPO" diff --binary HEAD -- . "${EXCLUDES[@]}" > "$DIR/$name.patch"
    untracked_list | tar -C "$REPO" --null -T - -czf "$DIR/$name.tgz"
    [ -f "$INDEX" ] || printf '# Checkpoints\n\n| name | time | gate |\n|---|---|---|\n' > "$INDEX"
    printf '| %s | %s | %s |\n' "$name" "$(date -Iseconds)" "$gate" >> "$INDEX"
    echo "saved $name: patch $(wc -c < "$DIR/$name.patch") bytes, $(untracked_list | tr -cd '\0' | wc -c) untracked files, gate $gate"
}

restore() {
    local name=$1
    [ -f "$DIR/$name.patch" ] && [ -f "$DIR/$name.tgz" ] || { echo "no checkpoint named $name in $DIR"; exit 1; }
    local newest
    newest=$(index_names | tail -n 1)
    git -C "$REPO" checkout -- . "${EXCLUDES[@]}"
    echo "restored tracked files to HEAD (except ${PLAN:-no plan file} and $SPACE_REL/)"
    local removed=0
    if [ -n "$newest" ] && [ -f "$DIR/$newest.tgz" ]; then
        while IFS= read -r file; do
            if [ -f "$REPO/$file" ]; then
                rm -f "$REPO/$file"
                rmdir -p --ignore-fail-on-non-empty "$(dirname "$REPO/$file")" 2>/dev/null || true
                removed=$((removed + 1))
            fi
        done < <(tar -tzf "$DIR/$newest.tgz")
    fi
    echo "removed $removed untracked files listed in newest checkpoint $newest"
    # git apply rejects an empty patch file, and a checkpoint with no tracked changes has one.
    if [ -s "$DIR/$name.patch" ]; then
        git -C "$REPO" apply --binary "$DIR/$name.patch"
    fi
    tar -C "$REPO" -xzf "$DIR/$name.tgz"
    echo "applied $name: patch $(wc -c < "$DIR/$name.patch") bytes, $(tar -tzf "$DIR/$name.tgz" | wc -l) untracked files"
}

case ${1:-} in
    save)    [ $# -ge 2 ] || { echo "usage: $0 save <NN-name> [gate-result]"; exit 1; }; save "$2" "${3:-}" ;;
    restore) [ $# -eq 2 ] || { echo "usage: $0 restore <NN-name>"; exit 1; }; restore "$2" ;;
    *)       echo "usage: $0 save <NN-name> [gate-result] | restore <NN-name>"; exit 1 ;;
esac
