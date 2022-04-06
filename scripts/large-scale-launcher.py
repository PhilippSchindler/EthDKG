import sys
import subprocess
import time
import re
import fcntl
import os
import requests.compat

from typing import List, Optional, Any, Dict
from ethdkg import utils
from ethdkg.state_updates import StateUpdate

node_state = StateUpdate.NEW
node_states: List[StateUpdate]
node_processes: List[subprocess.Popen]
contract = None


with open("./ganache-cli_1025A.sh", "r") as f:
    node_addresses = re.findall("0x[0-9a-fA-F]{40}", f.read())

N: int = 0

w3 = utils.connect()


# 10 % failing after register
# 10 % manipulating their shares
# 10 % stopping in recover phase

# --send-invalid-shares <TARGET>
# --abort-on-key-share-submission
# --abort-after-registration


def print_stdout(data):
    lines = data.decode().splitlines()
    for line in lines:
        if line.strip() == "":
            print()
        else:
            print(">> ", line)
    return lines


def run(n=None):
    global N, node_processes, node_states, node_addresses, contract

    if n is not None:
        N = n

    assert N != 0
    node_addresses = node_addresses[N + 1 :]

    print("RUNNING CONTRACT DEPLOYMENT: python -m ethdkg deploy\n")
    stdout = subprocess.check_output(
        f"pipenv run python -m ethdkg deploy --account-index {N}", stderr=subprocess.STDOUT, shell=True
    )
    stdout_lines = print_stdout(stdout)

    contract_addr = next(re.finditer("0x[0-9a-fA-F]+", stdout_lines[-8])).group(0)
    contract = utils.get_contract("ETHDKG", contract_addr)

    print(f"CONTRACT DEPLOYED AT: {contract_addr}")
    print()
    print()
    # time.sleep(1.0)
    print(f"STARTING NODE PROCESSES... ", end="", flush=True)
    node_states = [StateUpdate.NEW] * N
    node_processes = [
        subprocess.Popen(
            [
                "pipenv",
                "run",
                "python",
                "-m",
                "ethdkg",
                "run",
                contract_addr,
                "--account-index",
                str(i),
                "--interactive",
            ],
            # f"pipenv run python -m ethdkg run {contract_addr} --account-index {i}",
            # shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        for i in range(N)
    ]

    for p in node_processes:
        fcntl.fcntl(p.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)

    print("DONE")
    print()

    # for i, p in enumerate(node_processes):
    #     print(i)
    #     while True:
    #         p.stdout.flush()
    #         line = p.stdout.readline()
    #         if line == "":
    #             time.sleep(0.1)
    #         print(i, ">>", line)
    #         if line == "StateUpdate.STARTED\n":
    #             break

    wait_for(StateUpdate.STARTED, step=False)
    wait_for(StateUpdate.INITIALIZED)
    wait_for(StateUpdate.WAITING_FOR_REGISTRATION_CONFIRMATION)
    wait_for(StateUpdate.REGISTRATION_CONFIRMED)

    print("mining until registration phase ends... ", end="", flush=True)
    utils.mine_until_registrations_confirmed(contract)
    print("done\n")

    wait_for(StateUpdate.REGISTRATION_PHASE_COMPLETED)
    wait_for(StateUpdate.SETUP_COMPLETED)
    wait_for(StateUpdate.WAITING_FOR_SHARING_CONFIRMATION)
    wait_for(StateUpdate.SHARING_CONFIRMED)

    print("mining until sharing phase ends... ", end="", flush=True)
    utils.mine_until_share_distribution_confirmed(contract)
    print("done\n")

    wait_for(StateUpdate.SHARING_PHASE_COMPLETED)
    wait_for(StateUpdate.SHARES_LOADED)


def wait_for(state, batch_size: int = 32, step: bool = True):
    global node_state

    if batch_size == 0 or batch_size > N:
        batch_size = N

    finished = 0
    t_start = time.time()

    block_number = utils.block_number()

    def print_progress(first_time=False):
        if not first_time:
            if batch_size == N:
                print("\033[F" * 3, end="")
            else:
                print("\033[F" * 4, end="")
        print(f"    reached by {finished}/{N} nodes")
        print(f"    elapsed time: {time.time() - t_start:.2f}s")
        print(f"    current block: {block_number}")
        if batch_size != N:
            if first_time:
                print(f"    batch 0 to {batch_size}")
            else:
                print(f"    batch {batch_start} to {batch_end}")

    print(state.name)
    print(f"    started at block: {utils.block_number()}")
    print_progress(first_time=True)

    for batch_start in range(0, N, batch_size):
        batch_end = min(batch_start + batch_size, N)

        if step:
            for node_index in range(batch_start, batch_end):
                if node_states[node_index] < state:
                    node_processes[node_index].stdin.write("continue\n")
                    node_processes[node_index].stdin.flush()

        while True:
            for node_index in range(batch_start, batch_end):
                if node_states[node_index] >= state:
                    continue
                while node_states[node_index] < state:
                    line = node_processes[node_index].stdout.readline()
                    if line == "":
                        break
                    line = line.strip()
                    if line.startswith("StateUpdate."):
                        node_states[node_index] = StateUpdate[line.split(".")[1]]
                else:
                    finished += 1
                    print_progress()

            if finished < batch_end:
                time.sleep(1.0)
                block_number = utils.block_number()
                print_progress()
            else:
                break

    block_number = utils.block_number()
    print(f"    completed at block: {block_number}\n")
    node_state = state


def step():
    for p in node_processes:
        p.stdin.write("continue\n")
        p.stdin.flush()


# xdotool type 'python -m ethdkg deploy'
# xdotool key Return
#
# i3-msg "workspace back_and_forth" &>/dev/null
# read -p "Press enter to start nodes... "
#
# CONTRACT=$(cat ./logs/deployment.log | head -n8 | tail -n1 | cut -d" " -f8)
# echo "Contract address: $CONTRACT"
#

if __name__ == "__main__":
    try:
        N = int(sys.argv[1])
        run()
    except IndexError:
        print("Usage: python3.7 large-scale-launcher.py <NUM_NODES>")

