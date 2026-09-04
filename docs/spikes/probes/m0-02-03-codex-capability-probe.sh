#!/usr/bin/env bash

set -euo pipefail

codex_bin="$(command -v codex)"
codex_version="$("$codex_bin" --version)"
codex_semver="${codex_version#codex-cli }"
probe_dir="$(mktemp -d /tmp/devharness-m0-codex.XXXXXX)"
probe_workspace="$probe_dir/workspace"
app_server_pid=""
pipe_fd_open=0

cleanup() {
  if test "$pipe_fd_open" = 1; then
    exec 3>&-
    pipe_fd_open=0
  fi
  if test -n "$app_server_pid" && kill -0 "$app_server_pid" 2>/dev/null; then
    kill "$app_server_pid" 2>/dev/null || true
    wait "$app_server_pid" 2>/dev/null || true
  fi
  case "$probe_dir" in
    /tmp/devharness-m0-codex.*) find "$probe_dir" -depth -delete ;;
    *) printf 'probe_cleanup_refused=%s\n' "$probe_dir" >&2 ;;
  esac
}
trap cleanup EXIT

mkdir -p "$probe_workspace"

"$codex_bin" --help > "$probe_dir/codex-help.txt"
"$codex_bin" app-server --help > "$probe_dir/app-server-help.txt"
"$codex_bin" -C "$probe_workspace" -c 'analytics.enabled=false' \
  app-server generate-json-schema --out "$probe_dir/schema" >/dev/null
mkfifo "$probe_dir/app-server-input"
"$codex_bin" -C "$probe_workspace" -c 'analytics.enabled=false' app-server --listen stdio:// \
  < "$probe_dir/app-server-input" \
  > "$probe_dir/app-server-initialize.jsonl" \
  2> "$probe_dir/app-server-initialize.stderr" &
app_server_pid="$!"
exec 3> "$probe_dir/app-server-input"
pipe_fd_open=1
printf '%s\n' '{"id":1,"method":"initialize","params":{"clientInfo":{"name":"devharness-m0-probe","version":"0.0.0"},"capabilities":{"experimentalApi":false}}}' >&3

handshake_seen=0
for _ in $(seq 1 100); do
  if jq -e 'select(.id == 1 and .result.platformFamily and .result.platformOs)' \
    "$probe_dir/app-server-initialize.jsonl" >/dev/null 2>&1; then
    handshake_seen=1
    break
  fi
  if ! kill -0 "$app_server_pid" 2>/dev/null; then
    break
  fi
  sleep 0.05
done

exec 3>&-
pipe_fd_open=0
if wait "$app_server_pid"; then
  app_server_exit=0
else
  app_server_exit="$?"
fi
app_server_pid=""
test "$handshake_seen" = 1
test "$app_server_exit" = 0

for command in app-server mcp plugin features sandbox debug; do
  rg -q "^[[:space:]]+${command}[[:space:]]" "$probe_dir/codex-help.txt"
done

rg -q '"thread/read"' "$probe_dir/schema/ClientRequest.json"
rg -q '"item/commandExecution/requestApproval"' "$probe_dir/schema/ServerRequest.json"
rg -q '"serverRequest/resolved"' "$probe_dir/schema/ServerNotification.json"
rg -q '"hook/started"' "$probe_dir/schema/ServerNotification.json"
rg -q '"hook/completed"' "$probe_dir/schema/ServerNotification.json"
rg -q '"instructionSources"' "$probe_dir/schema/v2/ThreadStartResponse.json"
rg -q '"instructionSources"' "$probe_dir/schema/v2/ThreadResumeResponse.json"
jq -e --arg semver "$codex_semver" 'select(
  .id == 1 and
  (.result.userAgent | contains("Codex Desktop/" + $semver)) and
  .result.platformFamily == "unix" and
  .result.platformOs == "macos"
)' "$probe_dir/app-server-initialize.jsonl" >/dev/null

printf 'codex_path=%s\n' "$codex_bin"
printf 'codex_version=%s\n' "$codex_version"
printf 'documented_command_help=passed (6)\n'
printf 'default_protocol_schema_generation=passed\n'
printf 'app_server_initialize_handshake=passed\n'
printf 'app_server_initialize_exit=%s\n' "$app_server_exit"
printf 'probe_cwd=disposable\n'
printf 'analytics_override=disabled\n'
printf 'thread_read_schema=present\n'
printf 'approval_request_and_resolution_schema=present\n'
printf 'instruction_sources_schema=present\n'
printf 'synchronous_hook_notifications_schema=present\n'
printf 'desktop_passive_live_attachment=unobserved\n'
printf 'active_config_source=unobserved\n'
printf 'default_global_config_loading=unobserved\n'
printf 'rules_hook_sandbox_approval_runtime=unobserved\n'
printf 'mcp_plugin_harmless_invocation=unobserved\n'
printf 'raw_evidence=temporary_and_removed_on_exit\n'
