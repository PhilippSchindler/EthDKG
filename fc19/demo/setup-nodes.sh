if [[ $# -eq 0 ]] ; then
    echo 'contract address missing'
    exit 1
fi

LL=60

read -p "Press enter to start node 1... "

i3-msg workspace 1:node &> /dev/null && terminator --profile whitebig &> /dev/null &
feh --bg-fill ~/github.com/ethdkg/demo/nums/1.png

xdotool \
	sleep 1 \
	type --args 1 "PS1='1$ '; history -c;" key Return \
	key CTRL+L \
	type --args 1 "python dkg.py --line-length $LL \\" key Return \
	type --args 1 "run 1 $1" \
	&

read -p "Press enter to start nodes 2 and 3... "

i3-msg workspace 2:node &> /dev/null && terminator --profile whitebig &> /dev/null &
feh --bg-fill ~/github.com/ethdkg/demo/nums/2.png
xdotool \
	sleep 1 \
	type --args 1 "PS1='2$ '; history -c;" key Return \
	key CTRL+L \
	type --args 1 "python dkg.py --line-length $LL \\" key Return \
	type --args 1 "run 2 $1" key Return \
	&
sleep 5


i3-msg workspace 3:node &> /dev/null && terminator --profile whitebig &> /dev/null &
feh --bg-fill ~/github.com/ethdkg/demo/nums/3.png
xdotool \
	sleep 1 \
	type --args 1 "PS1='3$ '; history -c;" key Return \
	key CTRL+L \
	type --args 1 "python dkg.py --line-length $LL \\" key Return \
	type --args 1 "run 3 $1" key Return \
	&

read -p "Press enter to start (adversarial) node 4... "


i3-msg workspace 4:node &> /dev/null && terminator --profile whitebig &> /dev/null &
feh --bg-fill ~/github.com/ethdkg/demo/nums/4.png
xdotool \
	sleep 1 \
	type --args 1 "PS1='4$ '; history -c;" key Return \
	key CTRL+L \
	type --args 1 "python dkg.py --line-length $LL \\" key Return \
	type --args 1 "run 4 $1 \\" key Return \
	type --args 3 "-" "-" "send-invalid-shares 1" \
	&

read -p "Press enter to start (faulty) node 5... "


i3-msg workspace 5:node &> /dev/null && terminator --profile whitebig &> /dev/null &
feh --bg-fill ~/github.com/ethdkg/demo/nums/5.png
xdotool \
	sleep 1 \
	type --args 1 "PS1='5$ '; history -c;" key Return \
	key CTRL+L \
	type --args 1 "python dkg.py --line-length $LL \\" key Return \
	type --args 1 "run 5 $1 \\" key Return \
	type --args 3 "-" "-" "abort-after-registration" \
	&

