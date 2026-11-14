#!/bin/bash
# Fork-only sampler for the parallel-instances experiment.
#
# Every 5 seconds appends one CSV row to "$1/samples.csv": CPU split over the
# last 4 seconds, load average, memory pages by state (MB), swap in use, and
# the number, summed RSS and summed %CPU of the Flet app processes and of the
# python processes. Every 30 seconds it also saves a screenshot of the display
# to "$1/screen-<n>.jpg" and appends the eight processes that use the most CPU
# to "$1/top-processes.txt".
#
# Runs until it is killed.

dir="$1"
out="$dir/samples.csv"
mkdir -p "$dir"
echo "ts,cpu_user,cpu_sys,cpu_idle,load1,free_mb,active_mb,inactive_mb,wired_mb,compressed_mb,swap_used_mb,flet_n,flet_rss_mb,flet_cpu,py_n,py_rss_mb,py_cpu" > "$out"

n=0
while true; do
  # `top -l 2 -s 4` doubles as the 4 s wait; the second sample covers it.
  cpu=$(top -l 2 -n 0 -s 4 2>/dev/null | grep "CPU usage" | tail -1 \
    | sed -E 's/.*: ([0-9.]+)% user, ([0-9.]+)% sys, ([0-9.]+)% idle.*/\1,\2,\3/')
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  load=$(sysctl -n vm.loadavg | awk '{print $2}')
  mem=$(vm_stat | awk '
    /page size of/ {ps=$8}
    /Pages free/ {free=$3}
    /Pages active/ {active=$3}
    /Pages inactive/ {inactive=$3}
    /Pages wired down/ {wired=$4}
    /Pages occupied by compressor/ {comp=$5}
    END {m=ps/1048576; printf "%.0f,%.0f,%.0f,%.0f,%.0f", free*m, active*m, inactive*m, wired*m, comp*m}')
  swap=$(sysctl -n vm.swapusage | sed -E 's/.*used = ([0-9.]+)M.*/\1/')
  procs=$(ps -axo rss=,pcpu=,comm= | awk '
    $3 ~ /\/Flet$/ {flet_n++; flet_rss+=$1; flet_cpu+=$2}
    $3 ~ /[Pp]ython/ {py_n++; py_rss+=$1; py_cpu+=$2}
    END {printf "%d,%.0f,%.1f,%d,%.0f,%.1f", flet_n, flet_rss/1024, flet_cpu, py_n, py_rss/1024, py_cpu}')
  echo "$ts,$cpu,$load,$mem,$swap,$procs" >> "$out"
  n=$((n + 1))
  if [ $((n % 6)) -eq 0 ]; then
    screencapture -x -t jpg "$dir/screen-$(printf '%03d' $((n / 6))).jpg" 2>/dev/null || true
    {
      echo "== $ts"
      ps -axo pcpu=,rss=,comm= | sort -rn | head -8
    } >> "$dir/top-processes.txt"
  fi
  sleep 1
done
