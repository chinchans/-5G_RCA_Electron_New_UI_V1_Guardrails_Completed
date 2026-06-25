#!/usr/bin/env bash
#
# Transfer updated cu_simnovus.conf from machine 140 → machine 95.
#
# Run this script ON the source machine (tcs@10.138.77.140) after Test Deployment
# has written ~/Config/cu_simnovus.conf.
#
# Steps:
#   1. On 95: rename existing cu_simnovus.conf → cu_simnovus_backup.conf
#   2. SCP ~/Config/cu_simnovus.conf from 140 → 95 (same remote path & filename)
#
# Prerequisites:
#   - python3 + paramiko (pip install paramiko), or passwordless SSH keys
#   - Local file exists: $LOCAL_SOURCE
#
# Usage:
#   chmod +x transfer_cu_simnovus_140_to_95.sh
#   ./transfer_cu_simnovus_140_to_95.sh
#
# Optional overrides:
#   REMOTE_HOST=10.138.77.95 REMOTE_USER=tcs LOCAL_SOURCE=~/Config/cu_simnovus.conf ./transfer_cu_simnovus_140_to_95.sh

set -euo pipefail

# --- Source (140 machine – run script here) ---
LOCAL_SOURCE="${LOCAL_SOURCE:-$HOME/Config/cu_simnovus.conf}"

# --- Destination (95 machine) ---
REMOTE_USER="${REMOTE_USER:-tcs}"
REMOTE_HOST="${REMOTE_HOST:-10.138.77.95}"
REMOTE_PASSWORD="${REMOTE_PASSWORD:-tcs@12345}"
REMOTE_DIR="${REMOTE_DIR:-$HOME/chandu/5g_standalone_split8_v4_simnovus_cu_du_ue_2022_For_GenAI/5g_sa_split8_v4_simnovus_cu_usrp_oct_25_2022/targets/PROJECTS/GENERIC-NR-5GC/CONF}"
REMOTE_FILE="${REMOTE_FILE:-cu_simnovus.conf}"
REMOTE_BACKUP="${REMOTE_BACKUP:-cu_simnovus_backup.conf}"

REMOTE="${REMOTE_USER}@${REMOTE_HOST}"
REMOTE_PATH="${REMOTE_DIR}/${REMOTE_FILE}"
REMOTE_BACKUP_PATH="${REMOTE_DIR}/${REMOTE_BACKUP}"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { log "ERROR: $*"; exit 1; }

# Expand ~ in LOCAL_SOURCE if set literally
LOCAL_SOURCE="${LOCAL_SOURCE/#\~/$HOME}"

if [[ ! -f "$LOCAL_SOURCE" ]]; then
    die "Local file not found: $LOCAL_SOURCE (run Test Deployment Deploy first, or set LOCAL_SOURCE)"
fi

log "Source host: $(hostname) ($(whoami))"
log "Local file:  $LOCAL_SOURCE"
log "Remote:      $REMOTE"
log "Remote dir:  $REMOTE_DIR"
log "Remote file: $REMOTE_FILE"
log "Backup name: $REMOTE_BACKUP"
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/../Frontend/cu_simnovus_transfer.py"

if [[ ! -f "$PY_SCRIPT" ]]; then
    die "Python transfer script not found: $PY_SCRIPT"
fi

CONFIG_JSON=$(python3 -c "import json,os; print(json.dumps({
    'local_source': os.path.expanduser('${LOCAL_SOURCE}'),
    'remote_user': '${REMOTE_USER}',
    'remote_host': '${REMOTE_HOST}',
    'remote_password': '${REMOTE_PASSWORD}',
    'remote_dir': os.path.expanduser('${REMOTE_DIR}'),
    'remote_file': '${REMOTE_FILE}',
    'remote_backup': '${REMOTE_BACKUP}',
}))")

log "Transferring via paramiko (password auth) ..."
RESULT=$(python3 "$PY_SCRIPT" "$CONFIG_JSON") || die "Transfer failed"
echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"

log "Done."
log "  Local:  $LOCAL_SOURCE"
log "  Remote: ${REMOTE}:${REMOTE_PATH}"
