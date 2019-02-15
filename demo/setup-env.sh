docker stop $(docker ps -aq) &> /dev/null

i3-msg workspace number 1 &> /dev/null; sleep 0.5; xdotool key CTRL+Q;
i3-msg workspace number 2 &> /dev/null; sleep 0.5; xdotool key CTRL+Q;
i3-msg workspace number 3 &> /dev/null; sleep 0.5; xdotool key CTRL+Q;
i3-msg workspace number 4 &> /dev/null; sleep 0.5; xdotool key CTRL+Q;
i3-msg workspace number 5 &> /dev/null; sleep 0.5; xdotool key CTRL+Q;
i3-msg workspace number 6 &> /dev/null; sleep 0.5; xdotool key CTRL+Q;
i3-msg workspace number 7 &> /dev/null; sleep 0.5; xdotool key CTRL+Q;

# i3-msg workspace 6:docker/ganache &> /dev/null; sleep 1; xdotool key CTRL+Q; sleep 0.5;
# i3-msg workspace 7:management &> /dev/null; sleep 1; xdotool key CTRL+Q; sleep 0.5;
# i3-msg workspace 8: &> /dev/null; sleep 1; xdotool key CTRL+Q; sleep 1;


xdotool \
	sleep 1 \
	type --args 1 "PS1='D$ '; cd ~/github.com/ethdkg; history -c" key Return \
	sleep 1 \
	key CTRL+L \
	type --args 1 "# docker build -t ethdkg ." key Return \
	type --args 1 "docker run -p 127.0.0.1:8545:8545 -it ethdkg /bin/bash" key Return \
	sleep 2 \
	type --args 1 "ganache-cli --host 0.0.0.0 --blockTime 15" \
	&
i3-msg workspace 6:docker/ganache &> /dev/null && terminator --profile whitebig &> /dev/null &


sleep 8


xdotool \
	sleep 1 \
	type --args 1 "cd ~/github.com/ethdkg && pipenv shell && exit" key Return \
	sleep 1 \
	type --args 1 "PS1='M$ '; cd client; history -c;" key Return \
	type --args 1 "history -s ../demo/setup-nodes.sh " key Return \
	type --args 1 "history -s \"python -c 'import utils; utils.mine_blocks(10)'\"" key Return \
	type --args 1 "history -s \"python dkg.py deploy\"" key Return \
	type --args 1 "history -s \"python -c 'import utils; print(utils.blockNumber())'\"" key Return \
	key CTRL+L \
	&
i3-msg workspace 7:management &> /dev/null && terminator --profile whitebig &> /dev/null &


sleep 5

i3-msg workspace number 6


#xdotool \
#	sleep 1 \
#	type --args 1 "cd ~/github.com/ethdkg && pipenv shell && exit" key Return \
#	sleep 1 \
#	type --args 1 "PS1='1$ '; cd client; history -c;" key Return \
#	sleep 1 \
#	type --args 1 "history -s python dkg.py --line-length 60 run 1 " key Return \
#	sleep 1 \
#	key CTRL+L \
#	&
#i3-msg workspace 1 &> /dev/null && terminator --profile whitebig &> /dev/null &
#
# sleep 5
