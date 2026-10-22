#!/usr/bin/env bash
#
# cleanup_old_logs.sh
#
# Stand-in for a pre-existing operational script that a team already runs
# by hand (e.g. via cron or SSH). Removes files older than a given number
# of days from a target directory and prints a single machine-readable
# summary line so a caller -- including Ansible -- can tell whether
# anything actually changed without having to scrape free-form output.
#
# Usage: cleanup_old_logs.sh <directory> <max_age_days>
#
# Exit codes:
#   0 - success (directory scanned, zero or more files removed)
#   1 - invalid arguments
#   2 - target directory does not exist
#   3 - one or more files could not be removed (permissions, etc.)

set -euo pipefail

usage() {
  echo "Usage: $0 <directory> <max_age_days>" >&2
  exit 1
}

[[ $# -eq 2 ]] || usage

target_dir="$1"
max_age_days="$2"

[[ "$max_age_days" =~ ^[0-9]+$ ]] || usage

if [[ ! -d "$target_dir" ]]; then
  echo "ERROR: directory '${target_dir}' does not exist" >&2
  exit 2
fi

removed_count=0
error_count=0

while IFS= read -r -d '' file; do
  if rm -f -- "$file"; then
    removed_count=$((removed_count + 1))
  else
    error_count=$((error_count + 1))
  fi
done < <(find "$target_dir" -type f -mtime "+${max_age_days}" -print0)

echo "SUMMARY files_removed=${removed_count} errors=${error_count}"

if [[ "$error_count" -gt 0 ]]; then
  exit 3
fi

exit 0
