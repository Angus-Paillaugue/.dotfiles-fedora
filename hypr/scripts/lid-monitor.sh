#!/bin/bash

LID_PATH="/proc/acpi/button/lid/LID0/state"
MONITOR_NAME="eDP-1"

if [[ ! -f "$LID_PATH" ]]; then
  echo "Lid path $LID_PATH not found. Exiting."
  exit 1
fi

while true; do
  LID_STATE=$(grep -o open "$LID_PATH")

  if [[ "$LID_STATE" == "open" ]]; then
    # Re-enable internal display``
    hyprctl keyword monitor "$MONITOR_NAME,preferred,auto,1"

    # Wait a bit for monitor to become active
    sleep 1

    # Move all open windows to internal monitor
    window_ids=$(hyprctl clients -j | jq -r '.[].id')
    echo "$window_ids"
    for wid in $window_ids; do
      hyprctl dispatch movetomonitor "$MONITOR_NAME" "$wid"
    done

  else
    # Disable internal display on lid close
    hyprctl keyword monitor "$MONITOR_NAME,disable"
  fi

  sleep 1
done
