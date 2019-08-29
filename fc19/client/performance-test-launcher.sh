#!/bin/bash

export CONTRACT=$(python dkg.py deploy | tail -n1 | cut -d" " -f4)

declare -i L
declare -i COLS
declare -i account
declare -i last

COLS=4
ROWS=16
L=212/COLS-1
account=0
last=COLS*ROWS-1

run()
{   
    echo starting node with account $1
    if [ $1 -eq $last ]
    then
        terminator -e "bash -c \"python dkg.py --line-length $L run $1 $CONTRACT --send-invalid-shares 1; read -p 'press any key to exit...'\"" &>/dev/null &
    else
        terminator -e "bash -c \"python dkg.py --line-length $L run $1 $CONTRACT; read -p 'press any key to exit...'\"" &>/dev/null &
    fi
    sleep 3
}


echo $COLS $ROWS $L
i3-msg "workspace 7" &>/dev/null

for (( c=0; c<$COLS; c++ ))
do
    run $account
    account=account+1

    i3-msg split v &>/dev/null
    for (( r=1; r<$ROWS; r++ ))
    do
        run $account
        account=account+1
    done
    i3-msg focus parent &>/dev/null
    if [ $c -eq 0 ]
    then
        i3-msg split h &>/dev/null
    fi
done





# terminator -e 'bash -c "python dkg.py --line-length $L run 0 $CONTRACT ; read -p \"press any key to exit...\""' &>/dev/null &
# sleep 1

# terminator -e 'bash -c "python dkg.py --line-length $L run 1 $CONTRACT; read -p \"press any key to exit...\""' &>/dev/null &
# sleep 1

# terminator -e 'bash -c "python dkg.py --line-length $L run 2 $CONTRACT; read -p \"press any key to exit...\""' &>/dev/null &
# sleep 1

# i3-msg "focus left" &>/dev/null
# i3-msg "focus left" &>/dev/null
# i3-msg "split v" &>/dev/null

# terminator -e 'bash -c "python dkg.py --line-length $L run 3 $CONTRACT --abort-after-registration; read -p \"press any key to exit...\""' &>/dev/null &
# sleep 1

# i3-msg "focus right" &>/dev/null
# i3-msg "split v" &>/dev/null

# terminator -e 'bash -c "python dkg.py --line-length $L run 4 $CONTRACT --send-invalid-shares 1; read -p \"press any key to exit...\""' &>/dev/null &
# sleep 1


# i3-msg "focus right" &>/dev/null
# i3-msg "split v" &>/dev/null

# terminator -e 'bash -c "python dkg.py --line-length $L run 5 $CONTRACT; read -p \"press any key to exit...\""' &>/dev/null &
# sleep 1

# # i3-msg "move container to workspace number 4"
# # bash -c "python dkg.py run 0 0x12; read -p \"press any key to exit...\""