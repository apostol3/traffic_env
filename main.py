import argparse
import time

import env
import nlab

import traffic_env

__author__ = 'leon.ljsh'

parser = argparse.ArgumentParser(description="traffic enviroment for nlab")
parser.add_argument("-p", "--pipe", help="pipe name (default: %(default)s)",
                    metavar="name", type=str, dest="pipe_name", default="nlab")

args = parser.parse_args()

pipe_str = "\\\\.\\pipe\\{}"
pipe_name = args.pipe_name

esi = env.EStartInfo()
esi.count = 1
esi.incount = 13
esi.outcount = 1
esi.mode = env.SendModes.specified

last_time = time.perf_counter()
lab = nlab.NLab(pipe_str.format(pipe_name))
game = traffic_env.Game()

lab.connect()

lab.set_start_info(esi)
lab.get_start_info()

while lab.is_ok != env.VerificationHeader.stop:
    while not game.go:
        esdi = env.ESendInfo()
        esdi.head = env.VerificationHeader.ok
        game.outputs = game.get()
        esdi.data = [game.outputs]
        lab.set(esdi)

        get = lab.get()
        if lab.is_ok == env.VerificationHeader.stop:
            exit()
        game.set(get.data[0])

        game.tick(1 / 15)
        new_time = time.perf_counter()
        if new_time - last_time > 1 / 30:
            last_time = new_time
            game.dispatch_messages()
            game.draw()

    eri = env.ERestartInfo()
    eri.result = [game.fitness]
    lab.restart(eri)
    game.restart()

    lab.get()
    if lab.is_ok == env.VerificationHeader.stop:
        exit()
