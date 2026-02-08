import numpy as np
from pathlib import Path
from typing import Tuple, List

from functions import *
from WinterLess import WinterLess


class Hero:
    def __init__(self, winterless: WinterLess):
        self.winterless = winterless
        self.force_back()

    def back(self):
        self.winterless.automator.adb.back()

    def force_back(self):
        self.winterless.back_to_world()
        self.wait_and_click('templates/2.hero.png')

    def tap(self, x, y):
        return self.winterless.automator.tap(x, y)

    def swipe(self, x1, y1, x2, y2):
        return self.winterless.automator.adb.swipe(x1, y1, x2, y2, duration=500)

    def get_image_pos(self, path: str, timeout: int = 3):
        return self.winterless.automator.get_image_pos(path, timeout=timeout)

    def wait_and_click(self, path: str, timeout: int = 3):
        return self.winterless.automator.wait_and_click(path, timeout=timeout)

    def load_file(self, path: str):
        return self.winterless.automator.load_file(path)

    def get_image_pos_from_ram(self, target: np.ndarray, template: np.ndarray):
        return self.winterless.automator.get_image_pos_from_ram(target, template, scale_match=True)

    def get_images_pos(self, path: str, timeout: int = 3):
        return self.winterless.automator.get_images_pos(path, timeout=timeout)

    def crop_screenshot(self, region: Tuple[int, int, int, int]):
        screenshot = self.winterless.automator.get_screenshot()
        if region is not None:
            x1, y1, x2, y2 = region
            image = screenshot[y1:y2, x1:x2]
            return image
        return None

    def get_most_powerful_hero_pos(self, hero_type: int):
        types = ['Archer', 'Shield', 'Spearman']
        hero_type = types[hero_type]
        self.tap(1021, 54)
        self.wait_and_click('templates/power.png')
        poses = self.get_images_pos(f'templates/{hero_type}_hero_anchor.png')
        if not poses:
            return None
        target = min(poses, key=lambda item: (item[1], item[0]))
        x, y = target
        x = x + 78
        y = y + 109
        return [x, y]

    def get_hero_name(self, x, y):
        x1 = x - 90
        y1 = y - 100
        x2 = x + 90
        y2 = y + 100
        image = self.crop_screenshot((x1, y1, x2, y2))
        path_obj = Path('templates/heros')
        files = list(path_obj.rglob('*large.png'))
        files = [file for file in files if file.is_file()]
        for file in files:
            if not file.is_file():
                continue
            file = str(file)
            template = self.load_file(file)
            if self.get_image_pos_from_ram(template, image):
                name = file.split('\\')[-1].split('_')[0]
                return name
        return 'Unknown_Hero'

    @loop_timeout(timeout_seconds=30)
    def get_target_hero(self, should_break, hero_name: str):
        path = f'templates/heros/{hero_name}_large.png'
        while True:
            if should_break():
                return False
            pos = self.get_image_pos(path)
            if pos:
                return pos[0], pos[1]
            self.swipe(500, 850, 500, 300)

    @loop_timeout(timeout_seconds=30)
    def get_on_off_hero_arms(self, should_break, hero_name: str, operation='on'):
        path = f'templates/heros/{hero_name}_large.png'
        while not self.wait_and_click(path):
            if should_break():
                return False
            self.swipe(500, 850, 500, 300)
        self.wait_and_click('templates/hero_arms.png')
        self.wait_and_click(f'templates/hero_arms_get_{operation}.png')
        self.back()

    def swap_hero_arms(self, swap_list: List):
        source = swap_list[0]
        target = swap_list[1]
        self.get_on_off_hero_arms(source, 'off')
        self.get_on_off_hero_arms(target, 'on')
