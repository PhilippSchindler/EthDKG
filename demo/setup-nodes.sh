if [[ $# -eq 0 ]] ; then
    echo 'contract address missing'
    exit 1
fi

LL=60

xdotool \
	sleep 1 \
	type --args 1 "PS1='1$ '; history -c;" key Return \
	key CTRL+L \
	type --args 1 "python dkg.py --line-length $LL run 1 $1" \
	&
i3-msg workspace 1:node &> /dev/null && terminator --profile whitebig &> /dev/null &
sleep 2

xdotool \
	sleep 1 \
	type --args 1 "PS1='1$ '; history -c;" key Return \
	key CTRL+L \
	type --args 1 "python dkg.py --line-length $LL run 2 $1" \
	&
i3-msg workspace 2:node &> /dev/null && terminator --profile whitebig &> /dev/null &
sleep 2

xdotool \
	sleep 1 \
	type --args 1 "PS1='1$ '; history -c;" key Return \
	key CTRL+L \
	type --args 1 "python dkg.py --line-length $LL run 3 $1" \
	&
i3-msg workspace 3:node &> /dev/null && terminator --profile whitebig &> /dev/null &
sleep 2

xdotool \
	sleep 1 \
	type --args 1 "PS1='1$ '; history -c;" key Return \
	key CTRL+L \
	type --args 1 "python dkg.py --line-length $LL run 4 $1" \
	&
i3-msg workspace 4:node &> /dev/null && terminator --profile whitebig &> /dev/null &
sleep 2

xdotool \
	sleep 1 \
	type --args 1 "PS1='1$ '; history -c;" key Return \
	key CTRL+L \
	type --args 1 "python dkg.py --line-length $LL run 5 $1" \
	&
i3-msg workspace 5:node &> /dev/null && terminator --profile whitebig &> /dev/null &
sleep 2

i3-msg workspace 1:node &> /dev/null

