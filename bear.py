import argparse
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image

from ImageMatcher import ImageMatcher
from MumuManager import ADBController

target_players = [
    ['辣椒', '暧昧', '木瓜', '三千梨花树', '节能', '土豆嫂牛肉', 'xy520', '可乐',
     '乱怼', '荷华', '翅膀', '西瓜', '边边', '猴儿', '太美', '宫本'],
    ['肉', '暧昧', '木瓜', '三千梨花树', '节能', '土豆嫂牛肉', 'xy520', '可乐',
     '乱怼', '荷华', '翅膀', '西瓜', '边边', '猴儿', '太美', '宫本'],
    ['元宝家的元宝', '河东盐运使', '辽东郡', '中年狗叔', '白色糖果',
     '呆呆鱼', '红色糖果', 'mars', '龙大师', '粉色糖果', '相信光吗', '小蔡头']
]

# hero_x = [100, 210, 320, 430, 540, 650, 760, 870]
hero_x = [210, 320, 430, 540]


class BearHunting:
    def __init__(self, device_id: int = 0,
                 template_paths: dict = None,
                 troop_paths: dict = None,
                 threshold: float = 0.8):
        self.device_id = device_id
        self.threshold = threshold

        self.image_matcher = ImageMatcher()
        self.adb = ADBController(device_id=self.device_id,
                                 mmm_path=r'D:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe')

        self.troops = {}
        self.templates = {}
        self.joined_time = {}

        if template_paths:
            self.templates = self.load_templates(template_paths)
        if troop_paths:
            self.troops = self.load_templates(troop_paths)

        # 每次循环都创建
        self.executor = ThreadPoolExecutor(max_workers=20)

    @staticmethod
    def load_templates(paths: dict) -> dict:
        """加载模板图片"""
        templates = {}
        for i, path in paths.items():
            img = np.array(Image.open(path))
            if img is None:
                raise ValueError(f"无法加载模板图片: {path}")

            templates.update(
                {
                    i: img
                }
            )
        return templates

    def get_images_pos(self, threshold: float = 0.95):
        # print(f"等待图像: {template_path}")

        template_keys = list(self.templates.keys())
        template_values = list(self.templates.values())

        screenshot = self.adb.screenshot()
        result = list(self.executor.map(
            lambda template: self.image_matcher.find_template(screenshot, template, threshold),
            template_values
        ))

        result = dict(zip(template_keys, result))
        return result

    def _get_image_pos(self, template: np.ndarray, screenshot: np.ndarray, threshold: float = 0.8,
                       offset_x: int = 0, offset_y: int = 0):
        position = self.image_matcher.find_template(screenshot, template, threshold)
        if position:
            x, y = position
            x += offset_x
            y += offset_y
            return x, y
        return False

    def get_image_pos(self, template_path: str, timeout: int = 3,
                      threshold: float = 0.8, offset_x: int = 0, offset_y: int = 0):
        # print(f"等待图像: {template_path}")
        template = self.image_matcher.load_template(template_path)
        start_time = time.time()
        while time.time() - start_time - 0.1 < timeout:
            screenshot = self.adb.screenshot()
            result = self._get_image_pos(template=template, screenshot=screenshot, threshold=threshold,
                                         offset_x=offset_x, offset_y=offset_y)
            if result:
                return result
            time.sleep(0.2)
        return False

    def wait_and_click(self, template_path: str, timeout: int = 3,
                       threshold: float = 0.8, offset_x: int = 0, offset_y: int = 0):
        position = self.get_image_pos(template_path=template_path, timeout=timeout,
                                      threshold=threshold, offset_x=offset_x, offset_y=offset_y)

        if position:
            x, y = position
            self.adb.tap(x, y)
        else:
            return False

    def troop_depart(self, target: str, troop_id: int):

        # 选择队伍
        self.adb.tap(hero_x[troop_id], 184)
        time.sleep(0.1)
        # 选择出发
        self.adb.tap(828, 1821)
        time.sleep(0.2)

        '''
        是否成功派兵的判定
        '''
        screenshot = self.adb.screenshot()
        if (self._get_image_pos(template=self.troops['ratio'], screenshot=screenshot) and
                self._get_image_pos(template=self.troops['buff'], screenshot=screenshot)):
            self.adb.back()
            return False
        # 有编组退出两次
        if self._get_image_pos(template=self.troops[1], screenshot=screenshot):
            self.adb.back()
            time.sleep(0.1)
            self.adb.back()
            return False
        timestamp = time.time()
        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
        self.joined_time.update({target: timestamp})
        print(f'{time_str}:\t成功加入 {target} 的集结')

    def bear_joining(self, target: str, troop_id: int, target_y: int):

        # 点击加入按钮
        time.sleep(0.1)
        self.adb.tap(961, target_y)
        '''
        此处停留可能还要再调整，
        0.2: 经常卡死在选队伍界面，推测为时间不够出现编队
        '''
        time.sleep(0.15)

        '''
        第一次截图：
        这时可能出现三种情况：
        1. 点中+号，进入派兵界面，这时队伍编组可选，选中编组出发，退出函数
        2. 由于屏幕滚动，没点中+号，但是也进入了玩家队伍界面，这是需要判定是否有小+号，有则点击，没有则界面返回，退出函数
        3. 队伍已满或者已加入编队，不做任何操作
        '''
        screenshot = self.adb.screenshot()
        # 如果界面能选队伍，直接选好队伍出发
        if self._get_image_pos(template=self.troops[1], screenshot=screenshot):
            self.troop_depart(target=target, troop_id=troop_id)
            return True

        # 如果界面有集结标识，有加入图标点击加入图标，没有退回上层并中断
        if (self._get_image_pos(template=self.troops['ratio'], screenshot=screenshot) and
                self._get_image_pos(template=self.troops['buff'], screenshot=screenshot)):
            # 有加入图标，点击加入图标
            if self._get_image_pos(template=self.troops[0], screenshot=screenshot):
                self.adb.tap(900, 769)
                time.sleep(0.2)
            # 没有加入图标，返回列表，退出函数
            else:
                self.adb.back()
                return False

        '''
        第二次截图：
        这里主要处理第一次截图中的第二种情况做下一步操作
        1. 正常情况下停留在玩家队伍界面，则界面返回，退出函数
        2. 运气好还是进入了派兵界面，这时队伍编组可选，选中编组出发，退出函数
        但是第二次情况的通常结果是兵派不出去，会停留在派兵界面界面，这时可能需要第三次载图判定
        
        这里逻辑可能有问题，因为派后后就进入了派兵函数(troop_depart)，派兵成功应该由派兵函数判定
        '''
        screenshot = self.adb.screenshot()
        if (self._get_image_pos(template=self.troops['ratio'], screenshot=screenshot) and
                self._get_image_pos(template=self.troops['buff'], screenshot=screenshot)):
            self.adb.back()
            return False
        if self._get_image_pos(template=self.troops[1], screenshot=screenshot):
            self.troop_depart(target=target, troop_id=troop_id)
            return True

    def bear_assemble(self):
        # pos = self.back_to_world()
        pos = self.get_image_pos('templates/bear.png', timeout=5, threshold=0.75)
        if pos:
            self.adb.tap(pos[0], pos[1])
        else:
            print('找不到熊标，跳过开车')
            fail_time = time.time() - 350
            return fail_time

        # 点击集结按钮
        time.sleep(0.2)
        self.adb.tap(691, 1542)
        time.sleep(0.1)
        # 点击集结确认
        self.adb.tap(540, 1221)
        time.sleep(0.1)
        # 选择一队
        self.adb.tap(100, 184)
        time.sleep(0.1)
        # 出发
        self.adb.tap(828, 1821)
        assemble_time = time.time()
        time.sleep(0.1)
        time_str = time.strftime("%H:%M:%S", time.localtime(time.time()))
        print(f'{time_str}:\t集结开车......')

        # 点进集结
        self.adb.tap(998, 813)
        # 刷到最底端

        for _ in range(7):
            self.adb.swipe(540, 1600, 540, 300, duration=300)

        return assemble_time

    def back_to_world(self):
        world_icons = {
            0: 'templates/bear.png',
            1: 'templates/reconnect.png'
        }
        while True:
            games_status = self.load_templates(world_icons)
            if games_status[0] is not None:
                return games_status[0]

            # 如果账号已登出
            if games_status[1] is not None:
                self.adb.tap(780, 1197)
                continue
            self.adb.back()

    def enable_pet(self):
        if self.get_image_pos('templates/pet_fight_check.png'):
            return  True
        if self.wait_and_click('templates/pet_anchor.png', timeout=1):
            self.wait_and_click('templates/pet_fight.png', timeout=1)
            self.wait_and_click('templates/pet_skill_butch.png', timeout=1)
            self.wait_and_click('templates/pet_quick_use_confirm.png', timeout=1)
            self.adb.back()


def main():
    parser = argparse.ArgumentParser(description='Bear Hunting')
    parser.add_argument('deviceid', type=int, help='Mumu模拟器的编号')
    args = parser.parse_args()
    device_id = args.deviceid

    templates_path = {}
    troop_paths = {
        'ratio': 'templates/troop_ratio.png',
        'buff': 'templates/troop_buff.png',
        0: 'templates/troop_inner.png',
        1: 'templates/group1.png'
    }

    assemble_interval = 350
    hour = [21, 21, 21]

    # 判断是否到达开始时间
    now = time.time()
    now_struct = time.localtime(now)
    target_struct = time.struct_time((
        now_struct.tm_year, now_struct.tm_mon, now_struct.tm_mday,
        hour[device_id], 0, 0,
        now_struct.tm_wday, now_struct.tm_yday, now_struct.tm_isdst
    ))
    target = time.mktime(target_struct)

    target_counter = len(target_players[device_id])
    for i in range(target_counter):
        path = f'templates/bear{device_id}/{i}.png'
        templates_path.update({i: path})

    templates_path.update({'war': 'templates/war_settings.png'})
    templates_path.update({'world': 'templates/world_search.png'})
    templates_path.update({'troop': 'templates/troop_buff.png'})
    templates_path.update({'depart': 'templates/group1.png'})
    templates_path.update({'no_queue': 'templates/troop_purchase.png'})

    automator = BearHunting(template_paths=templates_path, troop_paths=troop_paths, device_id=device_id)

    run_reset = False

    # 准备打熊
    while True:
        timestamp = time.time()
        if target - timestamp < 0:
            break
        if target - timestamp < 30:
            if run_reset:
                continue
            print('熊坑归位！！！')
            automator.adb.tap(1080 / 2, 1920 / 2)
            if automator.get_image_pos('templates/bear_anchor.png', timeout=1):
                automator.adb.back()
                continue
            # 前往熊坑
            automator.adb.tap(804, 1853)
            time.sleep(0.5)
            automator.adb.tap(284, 1201)
            time.sleep(0.5)
            automator.adb.tap(764, 178)
            time.sleep(0.5)
            automator.adb.tap(885, 538)
            run_reset = True
        elif target - timestamp < 60 * 5:
            # 拉回部队
            print('5分钟后开始打熊，拉回所有队伍')
            pos = automator.get_image_pos('templates/retreat.png')
            if pos:
                automator.adb.tap(pos[0], pos[1])
                time.sleep(0.2)
                automator.adb.tap(769, 1181)
                time.sleep(0.2)
        elif target - timestamp < 60 * 15:
            print('请开宠物，换装备！请开宠物，换装备！请开宠物，换装备！')
            automator.enable_pet()
            time.sleep(1)
        else:
            print(f'距开始还有{int((target - timestamp)//60)}分钟。')
            time.sleep(60)

    assemble_time = 0
    while True:
        new_time = time.time()
        # 每10秒刷动一次
        if new_time - assemble_time >= assemble_interval:
            if assemble_time > 0:
                automator.adb.back()
            assemble_time = automator.bear_assemble()
        elif int(new_time % 60) % 15 == 0:
            automator.adb.swipe(540, 1600, 540, 300, duration=300)
            time.sleep(0.2)

        anchors = automator.get_images_pos()

        for key, value in anchors.items():
            # 如果返回值为空，直接处理下一组
            if value is None:
                continue

            # 序号为int，代表有刷到玩家，处理后马上中断当前轮回
            if isinstance(key, int):
                name = target_players[device_id][key]
                last_joined = automator.joined_time.get(name, 0)
                if new_time - last_joined <= 60 * 5:
                    continue

                troop_id = key % 4
                y = value[1] + 171
                automator.bear_joining(target=name, troop_id=troop_id, target_y=y)
                break
            # 如果没有匹配到玩家，而且还处于队伍列表，马上中断当前轮回
            elif key == 'war':
                break
            # 如果在世界界面重新点进队伍列表
            elif key == 'world':
                automator.adb.tap(998, 813)
                # 刷到最底端
                for _ in range(10):
                    automator.adb.swipe(540, 1600, 540, 300, duration=300)
                    time.sleep(1)
                break
            # 其他两种情况：在玩家队伍或者派兵界面都回退一次。派兵界面的回退次数不能确定，都只回退一次
            else:
                automator.adb.back()


if __name__ == "__main__":
    main()
