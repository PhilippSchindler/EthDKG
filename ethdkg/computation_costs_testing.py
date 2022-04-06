from . import crypto
import time
import math

# def shared_keys(sk, pks):
#     return {j: crypto.shared_key(sk, pk) for i, pk in enumerate(pks)}

n = 16


def T(operation, *args):
    t_start = time.time()
    result = [operation(i, *args) for i in range(n)]
    t_end = time.time()
    t = t_end - t_start

    print(str(operation).ljust(60), f"    single={t / n}, total={t}")
    if n == 1:
        return result[0]
    return result


def TS(operation, *args):
    t_start = time.time()
    result = operation(*args)
    t_end = time.time()
    t = t_end - t_start

    print(str(operation).ljust(60), f"    single={t}, total={n*t}")
    return result


def keygen(i):
    return crypto.keygen()


def derive_shared_keys(i, keys):
    sk, _ = keys[i]
    return [crypto.shared_key(sk, pk) for j, (_, pk) in enumerate(keys) if i != j]


def bench_keys():
    global n
    for n in [4, 8, 16, 32, 64, 128, 256, 512]:
        print()
        print(f"Running benchmark for n={n}:")

        keys = T(keygen)
        shared_keys = T(derive_shared_keys, keys)

    """
    Running benchmark for n=4:
    <function keygen at 0x7f0f0ce3ee18>                              single=0.009732067584991455, total=0.03892827033996582
    <function derive_shared_keys at 0x7f0f0ce3eea0>                  single=0.0298159122467041, total=0.1192636489868164

    Running benchmark for n=8:
    <function keygen at 0x7f0f0ce3ee18>                              single=0.0099526047706604, total=0.0796208381652832
    <function derive_shared_keys at 0x7f0f0ce3eea0>                  single=0.07077565789222717, total=0.5662052631378174

    Running benchmark for n=16:
    <function keygen at 0x7f0f0ce3ee18>                              single=0.009785428643226624, total=0.15656685829162598
    <function derive_shared_keys at 0x7f0f0ce3eea0>                  single=0.15025115013122559, total=2.4040184020996094

    Running benchmark for n=32:
    <function keygen at 0x7f0f0ce3ee18>                              single=0.010112114250659943, total=0.32358765602111816
    <function derive_shared_keys at 0x7f0f0ce3eea0>                  single=0.31160882860422134, total=9.971482515335083

    Running benchmark for n=64:
    <function keygen at 0x7f0f0ce3ee18>                              single=0.009964879602193832, total=0.6377522945404053
    <function derive_shared_keys at 0x7f0f0ce3eea0>                  single=0.6320334672927856, total=40.45014190673828

    Running benchmark for n=128:
    <function keygen at 0x7f0f0ce3ee18>                              single=0.01014433428645134, total=1.2984747886657715
    <function derive_shared_keys at 0x7f0f0ce3eea0>                  single=1.292378356680274, total=165.42442965507507

    Running benchmark for n=256:
    <function keygen at 0x7f0f0ce3ee18>                              single=0.010170464403927326, total=2.6036388874053955
    <function derive_shared_keys at 0x7f0f0ce3eea0>                  single=2.6275182850658894, total=672.6446809768677

    Running benchmark for n=512:
    <function keygen at 0x7f0f0ce3ee18>                              single=0.010074093472212553, total=5.157935857772827
    ^T<function derive_shared_keys at 0x7f0f0ce3eea0>                  single=5.40045006852597, total=2765.0304350852966
    """


def bench_sharing():
    global n
    for n in [2 ** i for i in range(2, 10)]:
        t = math.ceil(n / 2) - 1
        print()
        print(f"Running benchmark for n={n}, t={t}")

        secret = crypto.random_scalar()
        nodes = {crypto.random_scalar(): crypto.keygen() for i in range(n)}
        i, (ski, pki) = next(iter(nodes.items()))
        pks = {j: pkj for j, (_, pkj) in nodes.items()}
        shared_keys = {j: crypto.shared_key(ski, pkj) for j, pkj in pks.items() if i != j}
        shares = TS(crypto.share_secret, secret, list(nodes.keys()), t)

    """
    Running benchmark for n=4, t=1
    <function share_secret at 0x7f23a14d6840>                        single=0.020970821380615234, total=0.08388328552246094

    Running benchmark for n=8, t=3
    <function share_secret at 0x7f23a14d6840>                        single=0.0399785041809082, total=0.3198280334472656

    Running benchmark for n=16, t=7
    <function share_secret at 0x7f23a14d6840>                        single=0.08032727241516113, total=1.2852363586425781

    Running benchmark for n=32, t=15
    <function share_secret at 0x7f23a14d6840>                        single=0.16210341453552246, total=5.187309265136719

    Running benchmark for n=64, t=31
    <function share_secret at 0x7f23a14d6840>                        single=0.3376932144165039, total=21.61236572265625

    Running benchmark for n=128, t=63
    <function share_secret at 0x7f23a14d6840>                        single=0.6602764129638672, total=84.515380859375

    Running benchmark for n=256, t=127
    <function share_secret at 0x7f23a14d6840>                        single=1.4253015518188477, total=364.877197265625

    Running benchmark for n=512, t=255
    <function share_secret at 0x7f23a14d6840>                        single=3.3307595252990723, total=1705.348876953125
    """

    return locals()

