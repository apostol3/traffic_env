import random
import sys
import time
from enum import Enum
from math import e

import pygame

__author__ = "leon.ljsh"


class TrafficState(Enum):
    red = 0
    red_green = 1
    green = 2
    green_red = 3


class TrafficLight:
    def __init__(self):
        self.state = TrafficState.green
        self.state_time = 0
        self.state_time_min = [7, 6, 10, 3]
        self.control_sig = True

    def tick(self, dt):
        self.state_time += dt
        min_current_state_time = self.state_time_min[self.state.value]
        if self.state_time > min_current_state_time:
            if self.state == TrafficState.red_green:
                self.state = TrafficState.green
                self.state_time = 0
            elif self.state == TrafficState.green_red:
                self.state = TrafficState.red
                self.state_time = 0
            elif self.state == TrafficState.red and self.control_sig is True:
                self.state = TrafficState.red_green
                self.state_time = 0
            elif self.state == TrafficState.green and self.control_sig is False:
                self.state = TrafficState.green_red
                self.state_time = 0


class Car:
    def __init__(self, pos, direction, traffic_light, game):
        self.pos = pos
        self.direction = direction
        self.v = (0, 0)
        self.a = (0, 0)
        self.w = 4
        self.h = 2
        self.traffic = traffic_light
        self.game = game
        self.cross_time = 0

    def stop(self):
        self.v = (0, 0)

    def start(self):
        self.v = (5 * (2 * self.direction - 1), 0)

    def tick(self, dt):
        self.cross_time += dt
        self.v = (self.v[0] + self.a[0] * dt, self.v[1] + self.a[1] * dt)
        self.pos = (self.pos[0] + self.v[0] * dt, self.pos[1] + self.v[1] * dt)
        near = 1.5

        if self.direction is True:
            try:
                near = min(c.pos[0] - (self.pos[0] + self.w) for c in self.game.cars
                           if c.direction and (c.pos[0] > self.pos[0] + self.w))
            except ValueError:
                pass

            if self.pos[0] + self.w < 0 and self.traffic.state != TrafficState.green:
                near = min(-self.pos[0] - self.w, near)
        else:

            try:
                near = min(self.pos[0] - (c.pos[0] + c.w) for c in self.game.cars
                           if not c.direction and (c.pos[0] + c.w < self.pos[0]))
            except ValueError:
                pass

            if self.pos[0] > self.game.zebra_width and self.traffic.state != TrafficState.green:
                near = min(self.pos[0] - self.game.zebra_width, near)

        if near < 0.5:
            self.stop()
        elif near >= 1.5:
            self.start()


class Pedestrian:
    def __init__(self, pos, direction, traffic_light, game):
        self.pos = pos
        self.direction = direction
        self.v = (0, 0)
        self.a = (0, 0)
        self.l = 0.5
        self.traffic = traffic_light
        self.game = game
        self.cross_time = 0

    def stop(self):
        self.v = (0, 0)

    def start(self):
        self.v = (0, 1 * (2 * self.direction - 1))

    def tick(self, dt):
        self.cross_time += dt
        self.v = (self.v[0] + self.a[0] * dt, self.v[1] + self.a[1] * dt)
        self.pos = (self.pos[0] + self.v[0] * dt, self.pos[1] + self.v[1] * dt)
        near = 0.5

        if self.direction is True:
            try:
                near = min(p.pos[1] - (self.pos[1] + self.l) for p in self.game.pedestrians
                           if p.direction and (self.pos[1] + self.l < p.pos[1]))
            except ValueError:
                pass

            if self.pos[1] + self.l < 0 and self.traffic.state != TrafficState.red:
                near = min(-self.pos[1] - self.l, near)
        else:
            try:
                near = min(self.pos[1] - (p.pos[1] + p.l) for p in self.game.pedestrians
                           if not p.direction and (self.pos[1] > p.pos[1] + p.l))
            except ValueError:
                pass

            if self.pos[1] > self.game.road_width and self.traffic.state != TrafficState.red:
                near = min(self.pos[1] - self.game.road_width, near)

        if near < 0.1:
            self.stop()
        elif near >= 0.5:
            self.start()


class Game:
    def __init__(self, max_time):
        pygame.init()
        self.size = self.width, self.height = 1200, 550
        self.black = 0, 0, 0
        self.white = 255, 255, 255
        self.blue = 0, 0, 255
        self.green = 0, 255, 0
        self.red = 255, 0, 0
        self.violet = 255, 0, 255
        self.yellow = 255, 255, 0
        self.pink = 252, 15, 192

        self.screen = pygame.display.set_mode(self.size)
        self.font = pygame.font.SysFont('Tahoma', 12, False, False)

        self.zoom = 17
        self.road_width = 7
        self.road_segment = 25
        self.zebra_width = 3
        self.road_length = self.road_segment * 2 + self.zebra_width

        self.cam_pos_X = self.width / 2 - self.zebra_width * self.zoom / 2
        self.cam_pos_Y = 300

        self.traffic_light = TrafficLight()
        self.cars = []
        self.pedestrians = []

        self.inputs = [0]
        self.outputs = [0 for _ in range(13)]
        self.sensors = (1, 3, 7, 13, 21)

        self.gen_possibilities = [(1 / 14, 1 / 3), (1 / 3, 1 / 20), (1 / 30, 1 / 90), (1 / 3, 1 / 5)]
        random.shuffle(self.gen_possibilities)

        self.max_time = max_time
        self.sim_time = 0
        self.red_time = 0
        self.green_time = 0
        self.switch_time = 0

        self.cars_crossed = 0
        self.peds_crossed = 0

        self.cars_wait = 0
        self.peds_wait = 0

        self.go = False
        self.fitness = 0

    @property
    def current_part(self):
        return int(self.sim_time / int(self.max_time / 4))

    def recycling_cars(self, dt):
        live_cars = []
        for car in self.cars:
            if (car.direction is True and car.pos[0] < self.zebra_width + self.road_segment) \
                    or (car.direction is False and car.pos[0] + car.w > -self.road_segment):
                live_cars.append(car)
            else:
                self.cars_crossed += 1
                self.cars_wait += car.cross_time

        self.cars = live_cars

        appear_possibility = (dt * self.gen_possibilities[self.current_part][0],
                              dt * self.gen_possibilities[self.current_part][0])
        if random.random() < appear_possibility[0]:
            if self.cars:
                left = min(min((car.pos[0] - 0.5 - random.random() * 5) * car.direction for car in self.cars),
                           -self.road_segment)
            else:
                left = -self.road_segment
            self.cars.append(Car((left - 4, self.road_width / 2 + (self.road_width / 2 - 2) / 2), True,
                                 self.traffic_light, self))
        if random.random() < appear_possibility[1]:
            if self.cars:
                right = max(
                    max((car.pos[0] + car.w + 0.5 + random.random() * 5) * (not car.direction) for car in self.cars),
                    self.zebra_width + self.road_segment)
            else:
                right = self.zebra_width + self.road_segment
            self.cars.append(Car((right, (self.road_width / 2 - 2) / 2), False, self.traffic_light, self))

    def recycling_pedestrians(self, dt):
        live_peds = []
        for p in self.pedestrians:
            if (p.direction is True and p.pos[1] < self.road_width + 2 * self.zebra_width) \
                    or (p.direction is False and p.pos[1] + p.l > -2 * self.zebra_width):
                live_peds.append(p)
            else:
                self.peds_crossed += 1
                self.peds_wait += p.cross_time

        self.pedestrians = live_peds

        appear_possibility = (dt * self.gen_possibilities[self.current_part][1],
                              dt * self.gen_possibilities[self.current_part][1])
        if random.random() < appear_possibility[0]:
            if self.pedestrians:
                up = min(min((p.pos[1] - 0.1 - random.random() * 0.4) * p.direction for p in self.pedestrians),
                         -self.zebra_width * 2)
            else:
                up = -self.zebra_width * 2
            self.pedestrians.append(Pedestrian((self.zebra_width / 3, up - 0.5), True, self.traffic_light, self))
        if random.random() < appear_possibility[1]:
            if self.pedestrians:
                down = max(
                    max((p.pos[1] + p.l + 0.1 + random.random() * 0.4) * (not p.direction) for p in self.pedestrians),
                    2 * self.zebra_width + self.road_width)
            else:
                down = 2 * self.zebra_width + self.road_width
            self.pedestrians.append(Pedestrian((2 * self.zebra_width / 3, down), False, self.traffic_light, self))

    def tick(self, dt):
        if self.go:
            return

        self.traffic_light.tick(dt)
        for car in self.cars:
            car.tick(dt)

        for p in self.pedestrians:
            p.tick(dt)

        self.recycling_cars(dt)
        self.recycling_pedestrians(dt)

        self.sim_time += dt
        if self.traffic_light.state == TrafficState.green:
            self.green_time += dt
        elif self.traffic_light.state == TrafficState.red:
            self.red_time += dt
        else:
            self.switch_time += dt

        fail_state = self.is_fail()
        self.go |= fail_state or self.sim_time > self.max_time

        if self.peds_crossed and self.cars_crossed:
            if not fail_state:
                self.fitness = 12216 * e ** (
                    -0.04 * (self.cars_wait + self.peds_wait) / (self.cars_crossed + self.peds_crossed))
            else:
                live_cars_wait = sum(c.cross_time for c in self.cars)
                live_peds_wait = sum(p.cross_time for p in self.pedestrians)
                live_cars_count = len(self.cars)
                live_peds_count = len(self.pedestrians)
                self.fitness = 12216 * e ** (
                    -0.04 * (self.cars_wait + self.peds_wait + live_cars_wait + live_peds_wait) /
                    (self.cars_crossed + self.peds_crossed + live_cars_count + live_peds_count))
                self.fitness /= 10

    def is_fail(self):
        return any(True for p in self.pedestrians if p.cross_time > 90) or \
               any(True for c in self.cars if c.cross_time > 120)

    def draw_zebra(self):
        number_of_lines = 7
        width_of_line = self.road_width * self.zoom / (2 * number_of_lines)

        pygame.draw.line(self.screen, self.green, [-self.road_segment * self.zoom + self.cam_pos_X, self.cam_pos_Y],
                         [(self.road_segment + self.zebra_width) * self.zoom + self.cam_pos_X, self.cam_pos_Y], 2)
        pygame.draw.line(self.screen, self.green, [-self.road_segment * self.zoom + self.cam_pos_X,
                                                   self.cam_pos_Y + self.road_width * self.zoom],
                         [(self.road_segment + self.zebra_width) * self.zoom + self.cam_pos_X,
                          self.cam_pos_Y + self.road_width * self.zoom], 2)
        pygame.draw.line(self.screen, self.green, [-self.road_segment * self.zoom + self.cam_pos_X,
                                                   self.cam_pos_Y + self.road_width * self.zoom / 2],
                         [(self.road_segment + self.zebra_width) * self.zoom + self.cam_pos_X,
                          self.cam_pos_Y + self.road_width * self.zoom / 2], 1)

        for i in range(number_of_lines):
            pygame.draw.rect(self.screen, self.green, [self.cam_pos_X, self.cam_pos_Y + width_of_line * 2 * i,
                                                       self.zebra_width * self.zoom, width_of_line])

        pygame.draw.rect(self.screen, self.green, [self.cam_pos_X, self.cam_pos_Y,
                                                   self.zebra_width * self.zoom, -self.zebra_width * self.zoom], 2)
        pygame.draw.rect(self.screen, self.green,
                         [self.cam_pos_X, self.cam_pos_Y + (width_of_line * 2 * number_of_lines),
                          self.zebra_width * self.zoom, self.zebra_width * self.zoom], 2)

    def draw_traffic_light(self):
        state = self.traffic_light.state
        light_states = [(True, False, False), (True, True, False), (False, False, True), (False, True, False)]
        red_light, yellow_light, green_light = light_states[state.value]
        traffic_light_pos_x = self.zebra_width * self.zoom + self.cam_pos_X
        traffic_light_pos_y = self.cam_pos_Y
        traffic_light_w = self.zebra_width / 3 * self.zoom
        traffic_light_h = -self.zebra_width * self.zoom
        pygame.draw.rect(self.screen, self.violet,
                         [traffic_light_pos_x, traffic_light_pos_y, traffic_light_w, traffic_light_h], 3)
        pygame.draw.circle(self.screen, self.red,
                           [int(traffic_light_pos_x + 1 / 2 * traffic_light_w),
                            int(traffic_light_pos_y + 5 / 6 * traffic_light_h)], int(traffic_light_w / 2),
                           not red_light)
        pygame.draw.circle(self.screen, self.yellow,
                           [int(traffic_light_pos_x + 1 / 2 * traffic_light_w),
                            int(traffic_light_pos_y + 3 / 6 * traffic_light_h)], int(traffic_light_w / 2),
                           not yellow_light)
        pygame.draw.circle(self.screen, self.green,
                           [int(traffic_light_pos_x + 1 / 2 * traffic_light_w),
                            int(traffic_light_pos_y + 1 / 6 * traffic_light_h)], int(traffic_light_w / 2),
                           not green_light)

    def draw_lamp(self, position, text, color, val):
        _text = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(_text, (position[0] + 10, position[1]))

        pygame.draw.circle(self.screen, (128, 128, 128), (position[0], position[1] + 7), 5, 1)

        if val:
            pygame.draw.circle(self.screen, color, (position[0], position[1] + 7), 4, 0)

    def draw_bar(self, rect, color, val):
        pygame.draw.rect(self.screen, (128, 128, 128), ((rect[0][0], rect[0][1]), (rect[1][0], rect[1][1])), 1)
        if val:
            pygame.draw.rect(self.screen, color,
                             ((rect[0][0] + 1, rect[0][1] + rect[1][1] - 2), (rect[1][0] - 2, -val * (rect[1][1] - 4))))

    def draw(self):
        self.screen.fill(self.black)
        self.draw_zebra()
        self.draw_traffic_light()
        for s in self.sensors:
            pygame.draw.line(self.screen, self.white,
                             [self.cam_pos_X + (self.zebra_width + s) * self.zoom, self.cam_pos_Y], [
                                 self.cam_pos_X + (self.zebra_width + s) * self.zoom,
                                 self.cam_pos_Y + (self.road_width / 2) * self.zoom])
            pygame.draw.line(self.screen, self.white,
                             [self.cam_pos_X - s * self.zoom, self.cam_pos_Y + self.road_width * self.zoom],
                             [self.cam_pos_X - s * self.zoom, self.cam_pos_Y + self.road_width / 2 * self.zoom])
        for car in self.cars:
            pygame.draw.rect(self.screen, self.red,
                             [car.pos[0] * self.zoom + self.cam_pos_X, car.pos[1] * self.zoom + self.cam_pos_Y,
                              car.w * self.zoom, car.h * self.zoom], 2)

        for p in self.pedestrians:
            pygame.draw.rect(self.screen, self.pink,
                             [p.pos[0] * self.zoom + self.cam_pos_X, p.pos[1] * self.zoom + self.cam_pos_Y,
                              p.l * self.zoom, p.l * self.zoom])

        self.draw_bar(((50, 10), (10, 50)), (40, 235, 40), self.inputs[0])

        self.draw_bar(((100, 10), (10, 50)), (235, 40, 40), self.outputs[0])
        self.draw_bar(((115, 10), (10, 50)), (40, 40, 235), self.outputs[1])
        self.draw_bar(((130, 10), (10, 50)), (40, 40, 235), self.outputs[2])
        for i in range(3, len(self.outputs)):
            self.draw_bar(((100 + i * 15, 10), (10, 50)), self.white, self.outputs[i])

        if self.sim_time:
            self.draw_bar(((500, 10), (10, 50)), (235, 40, 40), self.red_time / self.sim_time)
            self.draw_bar(((515, 10), (10, 50)), (40, 235, 40), self.green_time / self.sim_time)
            self.draw_bar(((530, 10), (10, 50)), (235, 235, 40), self.switch_time / self.sim_time)

        self.screen.blit(self.font.render("Simulation time:  {:.0f}s".format(self.sim_time), True, (255, 255, 255)),
                         (650, 10))
        self.screen.blit(self.font.render("Cars crossed:  {}".format(self.cars_crossed), True, (255, 255, 255)),
                         (650, 30))
        self.screen.blit(self.font.render("Peds crossed: {}".format(self.peds_crossed), True, (255, 255, 255)),
                         (650, 50))
        if self.cars_crossed:
            self.screen.blit(self.font.render("Cars wait:  {:3.1f}s".format(self.cars_wait / self.cars_crossed),
                                              True, (255, 255, 255)), (650, 70))
        if self.peds_crossed:
            self.screen.blit(self.font.render("Peds wait: {:3.1f}s".format(self.peds_wait / self.peds_crossed),
                                              True, (255, 255, 255)), (650, 90))

        self.screen.blit(self.font.render("Fitness: {:6.0f}".format(self.fitness),
                                          True, (255, 255, 255)), (650, 110))

        pygame.display.flip()

    def get(self):
        outputs = []
        state_mappings = (1, 1, 0, 0)
        outputs.append(state_mappings[self.traffic_light.state.value])

        up_sensor = any(True for p in self.pedestrians if
                        0 < p.pos[0] < self.zebra_width and -self.zebra_width < p.pos[1] < 0)
        down_sensor = any(True for p in self.pedestrians if
                          0 < p.pos[0] < self.zebra_width and
                          self.road_width < p.pos[1] < self.road_width + self.zebra_width)
        outputs.append(up_sensor)
        outputs.append(down_sensor)

        for s in self.sensors:
            val = any(True for c in self.cars if c.direction and c.pos[0] < -s < c.pos[0] + c.w)
            outputs.append(val)
        for s in self.sensors:
            val = any(True for c in self.cars if not c.direction and c.pos[0] < s + self.zebra_width < c.pos[0] + c.w)
            outputs.append(val)

        self.outputs = outputs
        return outputs

    def set(self, inputs):
        self.inputs = inputs
        self.traffic_light.control_sig = inputs[0] > 0.5

    def dispatch_messages(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.restart()

    def restart(self):
        self.traffic_light = TrafficLight()
        self.cars = []
        self.pedestrians = []

        self.inputs = [0]
        self.outputs = [0, 0, 0]
        self.sensors = [1, 3, 7, 13, 21]

        self.sim_time = 0
        self.red_time = 0
        self.green_time = 0
        self.switch_time = 0

        self.cars_crossed = 0
        self.peds_crossed = 0

        self.cars_wait = 0
        self.peds_wait = 0

        self.go = False
        self.fitness = 0


def main():
    game = Game(3600)
    # time_old = time.perf_counter()
    time_draw = time.perf_counter()

    while True:
        game.tick(1 / 15)
        game.get()
        time.sleep(1 / 60)

        # game.set([not game.traffic_light.control_sig])
        game.set([not (game.outputs[1] or game.outputs[2]) or
                  (game.outputs[3] and game.outputs[7]) or (game.outputs[12] and game.outputs[8])])
        if time.perf_counter() - time_draw > 1 / 30:
            game.dispatch_messages()
            # keys = pygame.key.get_pressed()
            # game.set([game.traffic_light.control_sig ^ bool(keys[pygame.K_SPACE])])
            game.draw()
            time_draw = time.perf_counter()


if __name__ == "__main__":
    main()
