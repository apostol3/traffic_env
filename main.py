import argparse
import time

import pynlab

import traffic_env

__author__ = 'leon.ljsh'


def above_zero(string):
    value = int(string)
    if value <= 0:
        msg = "{} not above zero".format(value)
        raise argparse.ArgumentTypeError(msg)
    return value


parser = argparse.ArgumentParser(description="traffic environment for nlab")
parser.add_argument("-u", "--uri",
                    help="connection URI in format '[tcp|winpipe]://hostname(/pipe_name|:port)'(default: %(default)s",
                    metavar="uri", type=str, dest="connection_uri", default="tcp://127.0.0.1:5005")
parser.add_argument("-t", "--time", help="simulation time in seconds (default: %(default)s)",
                    metavar="sec", type=above_zero, dest="time", default=3600)
parser.add_argument("--no-gui", help="do not show gui", action="store_false",
                    dest="gui")

args = parser.parse_args()

print("initializing... ", end="")

esi = pynlab.EStartInfo()
esi.count = 1
esi.incount = 13
esi.outcount = 1
esi.mode = pynlab.SendModes.specified

last_time = time.perf_counter()

lab = pynlab.NLab(args.connection_uri)
game = traffic_env.Game(args.time, args.gui)
print("complete")

print("connenting to nlab at {}... ".format(args.connection_uri), end="", flush=True)
lab.connect()
print("connected")

print("waiting for start information from nlab... ", end="", flush=True)
lab.set_start_info(esi)
lab.get_start_info()
print("ok")

print("working")
while lab.is_ok != pynlab.VerificationHeader.stop:
    while not game.go:
        esdi = pynlab.ESendInfo()
        esdi.head = pynlab.VerificationHeader.ok
        game.outputs = game.get()
        esdi.data = [game.outputs]
        lab.set(esdi)

        get = lab.get()
        if lab.is_ok == pynlab.VerificationHeader.stop:
            print("get stop header from nlab. stopping")
            exit()
        game.set(get.data[0])

        game.tick(1 / 15)
        new_time = time.perf_counter()
        if new_time - last_time > 1 / 30:
            last_time = new_time
            game.dispatch_messages()
            game.draw()

    eri = pynlab.ERestartInfo()
    eri.result = [game.fitness]
    lab.restart(eri)
    game.restart()

    lab.get()
    if lab.is_ok == pynlab.VerificationHeader.stop:
        print("get stop header from nlab. stopping")
        exit()
