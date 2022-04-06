#!/bin/bash

cd "$(dirname "$0")"
cd ..

###################################################################################
### WINDOW SETUP
###################################################################################

i3-msg "workspace 7" &>/dev/null
i3-msg "split h" &>/dev/null

sleep 0.1

i3-msg "kill" &>/dev/null && sleep 0.1
i3-msg "kill" &>/dev/null && sleep 0.1
i3-msg "kill" &>/dev/null && sleep 0.1
i3-msg "kill" &>/dev/null && sleep 0.1
i3-msg "kill" &>/dev/null && sleep 0.1
i3-msg "kill" &>/dev/null && sleep 0.1

terminator &>/dev/null &
sleep 0.5
D=$(xdotool search --pid $! | tail -n1)

terminator &>/dev/null &
sleep 0.5
N1=$(xdotool search --pid $! | tail -n1)

terminator &>/dev/null &
sleep 0.5
N2=$(xdotool search --pid $! | tail -n1)

i3-msg "focus left" &>/dev/null
i3-msg "focus left" &>/dev/null
i3-msg "split v" &>/dev/null

terminator &>/dev/null &
sleep 0.5
N3=$(xdotool search --pid $! | tail -n1)

i3-msg "focus right" &>/dev/null
i3-msg "split v" &>/dev/null

terminator &>/dev/null &
sleep 0.5
N4=$(xdotool search --pid $! | tail -n1)

i3-msg "focus right" &>/dev/null
i3-msg "split v" &>/dev/null

terminator &>/dev/null &
sleep 0.5
N5=$(xdotool search --pid $! | tail -n1)

i3-msg "workspace back_and_forth" &>/dev/null

###################################################################################
### MAIN SCRIPT
###################################################################################

read -p "Press enter to start contract deployment..."

i3-msg "[id=$D] focus" &> /dev/null
xdotool type 'python -m ethdkg deploy'
xdotool key Return

i3-msg "workspace back_and_forth" &>/dev/null
read -p "Press enter to start nodes... "

CONTRACT=$(cat ./logs/deployment.log | head -n8 | tail -n1 | cut -d" " -f8)
echo "Contract address: $CONTRACT"


i3-msg "[id=$N1] focus" &> /dev/null
xdotool type "python -m ethdkg run $CONTRACT --account-index 1"
xdotool key Return

i3-msg "[id=$N2] focus" &> /dev/null
xdotool type "python -m ethdkg run $CONTRACT --account-index 2"
xdotool key Return

i3-msg "[id=$N3] focus" &> /dev/null
xdotool type "python -m ethdkg run $CONTRACT --account-index 3"
xdotool key Return


i3-msg "[id=$D] focus" &> /dev/null
xdotool type 'ipython -i -c "from ethdkg import utils; w3 = utils.connect()"'
xdotool key Return
xdotool type "contract = utils.get_contract(\"ETHDKG\", \"$CONTRACT\")"
xdotool key Return


i3-msg "workspace back_and_forth" &>/dev/null
read -p "Press enter to start adversarial nodes... "

i3-msg "[id=$N4] focus" &> /dev/null
xdotool type "python -m ethdkg run $CONTRACT --account-index 4 --send-invalid-shares 0"
xdotool key Return

i3-msg "[id=$N5] focus" &> /dev/null
xdotool type "python -m ethdkg run $CONTRACT --account-index 5 --send-invalid-shares 0"
xdotool key Return



