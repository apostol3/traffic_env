import random
import sys
import time
from enum import Enum

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

    def stop(self):
        self.v = (0, 0)

    def start(self):
        self.v = (5 * (2 * self.direction - 1), 0)

    def tick(self, dt):
        self.v = (self.v[0] + self.a[0] * dt, self.v[1] + self.a[1] * dt)
        self.pos = (self.pos[0] + self.v[0] * dt, self.pos[1] + self.v[1] * dt)
        near = 1.5
        if self.direction is True:
            near_f = list(filter((lambda c: c.direction and (c.pos[0] > self.pos[0] + self.w)), self.game.cars))
            if near_f:
                near = min(c.pos[0] - (self.pos[0] + self.w) for c in near_f)
            if self.pos[0] + self.w < 0 and self.traffic.state != TrafficState.green:
                near = min(-self.pos[0] - self.w, near)
        else:
            near_f = list(filter((lambda c: not c.direction and (c.pos[0] + c.w < self.pos[0])), self.game.cars))
            if near_f:
                near = min(self.pos[0] - (c.pos[0] + c.w) for c in near_f)
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

    def stop(self):
        self.v = (0, 0)

    def start(self):
        self.v = (0, 1 * (2 * self.direction - 1))

    def tick(self, dt):
        self.v = (self.v[0] + self.a[0] * dt, self.v[1] + self.a[1] * dt)
        self.pos = (self.pos[0] + self.v[0] * dt, self.pos[1] + self.v[1] * dt)
        near = 0.5
        if self.direction is True:
            near_f = list(filter((lambda p: p.direction and (self.pos[1] + self.l < p.pos[1])), self.game.pedestrians))
            if near_f:
                near = min(p.pos[1] - (self.pos[1] + self.l) for p in near_f)
            if self.pos[1] + self.l < 0 and self.traffic.state != TrafficState.red:
                near = min(-self.pos[1] - self.l, near)
        else:
            near_f = list(filter((lambda p: not p.direction and (self.pos[1] > p.pos[1] + p.l)), self.game.pedestrians))
            if near_f:
                near = min(self.pos[1] - (p.pos[1] + p.l) for p in near_f)
            if self.pos[1] > self.game.road_width and self.traffic.state != TrafficState.red:
                near = min(self.pos[1] - self.game.road_width, near)

        if near < 0.1:
            self.stop()
        elif near >= 0.5:
            self.start()


class Game:
    def __init__(self):
        pygame.init()
        self.size = self.width, self.height = 1200, 550
        self.black = 0, 0, 0
        self.blue = 0, 0, 255
        self.green = 0, 255, 0
        self.red = 255, 0, 0
        self.violet = 255, 0, 255
        self.yellow = 255, 255, 0
        self.pink = 252, 15, 192

        self.screen = pygame.display.set_mode(self.size)
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

    def recycling_cars(self, dt):
        live_cars = []
        for car in self.cars:
            if (car.direction is True and car.pos[0] < self.zebra_width + self.road_segment) \
                    or (car.direction is False and car.pos[0] + car.w > -self.road_segment):
                live_cars.append(car)

        self.cars = live_cars

        appear_possibility = dt * 1 / 5, dt * 1 / 5
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

        self.pedestrians = live_peds

        appear_possibility = dt * 1 / 10, dt * 1 / 10
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
        self.traffic_light.control_sig = not self.traffic_light.control_sig
        self.traffic_light.tick(dt)
        for car in self.cars:
            car.tick(dt)

        for p in self.pedestrians:
            p.tick(dt)

        self.recycling_cars(dt)
        self.recycling_pedestrians(dt)

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

    def draw(self):
        self.screen.fill(self.black)
        self.draw_zebra()
        self.draw_traffic_light()
        pygame.draw.circle(self.screen, self.red, [100, 100], 10, self.traffic_light.control_sig)
        for car in self.cars:
            pygame.draw.rect(self.screen, self.red,
                             [car.pos[0] * self.zoom + self.cam_pos_X, car.pos[1] * self.zoom + self.cam_pos_Y,
                              car.w * self.zoom, car.h * self.zoom], 2)

        for p in self.pedestrians:
            pygame.draw.rect(self.screen, self.pink,
                             [p.pos[0] * self.zoom + self.cam_pos_X, p.pos[1] * self.zoom + self.cam_pos_Y,
                              p.l * self.zoom, p.l * self.zoom])
        pygame.display.flip()


def main():
    game = Game()
    time_old = time.perf_counter()
    time_draw = time.perf_counter()

    while time.perf_counter() - time_old < 100:
        keys = pygame.key.get_pressed()
        game.traffic_light.control_sig = game.traffic_light.control_sig ^ keys[pygame.K_SPACE]
        game.tick(1 / 30)
        time.sleep(1 / 90)
        if time.perf_counter() - time_draw > 1 / 30:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
            game.draw()
            time_draw = time.perf_counter()


if __name__ == "__main__":
    main()
