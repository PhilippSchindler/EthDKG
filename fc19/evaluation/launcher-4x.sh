#!/bin/bash

cd ../client

export CONTRACT=$(python dkg.py deploy | tail -n1 | cut -d" " -f4)

i3-msg "workspace 7" &>/dev/null
i3-msg "split h" &>/dev/null

terminator -e 'bash -c "python dkg.py run 0 $CONTRACT; read -p \"press any key to exit...\""' &>/dev/null &
sleep 1

terminator -e 'bash -c "python dkg.py run 1 $CONTRACT; read -p \"press any key to exit...\""' &>/dev/null &
sleep 1

i3-msg "focus left" &>/dev/null
i3-msg "split v" &>/dev/null

# terminator -e 'bash -c "python dkg.py run 2 $CONTRACT; read -p \"press any key to exit...\""' &>/dev/null &
# terminator -e 'bash -c "python dkg.py run 2 $CONTRACT --abort-after-registration; read -p \"press any key to exit...\""' &>/dev/null &
terminator -e 'bash -c "python dkg.py run 2 $CONTRACT --send-invalid-shares 1; read -p \"press any key to exit...\""' &>/dev/null &
sleep 1

i3-msg "focus right" &>/dev/null
i3-msg "split v" &>/dev/null

# terminator -e 'bash -c "python dkg.py run 3 $CONTRACT; read -p \"press any key to exit...\""' &>/dev/null &
# terminator -e 'bash -c "python dkg.py run 3 $CONTRACT --abort-after-registration; read -p \"press any key to exit...\""' &>/dev/null &
terminator -e 'bash -c "python dkg.py run 3 $CONTRACT --send-invalid-shares 1 2; read -p \"press any key to exit...\""' &>/dev/null &
sleep 1
