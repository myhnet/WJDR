import time
import numpy as np
import re
import os
from MumuManager import MumuGameAutomator
from typing import List, Dict, Tuple
import subprocess
import cv2
from PIL import Image
import json
from qwen_vision_ocr import extra_text_qwen3, format_arena

from typing import Tuple, List, Dict, Optional, Union

try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("警告: pytesseract 未安装，OCR功能将不可用")

import time
from MumuManager import MumuGameAutomator
from OCRProcessor import OCRProcessor


class Test:
    def __init__(self, device_id: int, mmm_path: str = r'D:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe'):
        self.automator = MumuGameAutomator(device_id, 'com.gof.china', mmm_path=mmm_path)
        self.sys_config = 'sys_config.json'

    def back_to_world(self):
        world_icons = {
            0: 'templates/sidebar_close.png',
            1: 'templates/reconnect.png',
            2: 'templates/orders.png',
            3: 'templates/island_anchor.png',
            4: 'templates/world_search.png',
            5: 'templates/intelligence_btn.png',
            6: 'templates/my_town.png'
        }
        current_time = time.time()
        while True:
            games_status = self.automator.multiple_images_pos(world_icons)

            # 关闭左侧列表信息（因为会遮挡队列信息）
            if games_status[0] is not None:
                self.automator.adb.tap(695, 818)
                continue

            if games_status[4] is not None and games_status[5] is not None:
                return True

            # 如果账号已登出
            if games_status[1] is not None:
                # 10分钟后再做操作
                time_left = int(time.time() - current_time)
                if time_left > 600:
                    self.automator.adb.tap(780, 1197)
                else:
                    time_left = 600 - time_left
                    m = time_left // 60
                    s = time_left % 60
                    print(f'wait for {m}:{s}')
                    time.sleep(30)
                continue

            # 如果在城镇，则点击野外按钮
            if games_status[2] is not None:
                self.automator.adb.tap(978, 1826)
                continue

            # 如果在晨曦岛，点击退出
            if games_status[3] is not None:
                self.automator.adb.tap(66, 43)
                time.sleep(0.5)
                continue

            # 处理回城图标遮挡目标的情况，比较少见，所以放最后。
            pos = games_status[6]
            if pos is not None:
                self.automator.adb.tap(pos[0], pos[1])
                time.sleep(0.5)
                continue
            self.automator.adb.back()

    def extract_numbers_with_context(text: str) -> List[Dict[str, any]]:
        # 分割文本为行
        lines = text.strip().split('\n')
        result = []
        current_task = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 移除空格（因为每个字符间都有空格）
            compressed_line = line.replace(' ', '')

            # 检查是否是任务名称（不包含冒号和斜杠）
            if ':' not in compressed_line and '/' not in compressed_line:
                current_task = compressed_line
                continue

            # 检查是否包含奖励信息
            if '队员奖励已领取次数' in compressed_line:
                # 提取数字
                match = re.search(r'(\d+)/(\d+)', compressed_line)
                if match:
                    x, y = int(match.group(1)), int(match.group(2))

                    result.append({
                        'task_name': current_task,
                        'collected': x,
                        'total': y,
                        'ratio': f"{x}/{y}",
                        'percentage': round(x / y * 100, 2) if y > 0 else 0
                    })

        return result

    def event_locate(self, path: str, event_type: int = 1):
        event_list = {
            1: 'templates/events.png',
            2: 'templates/best_deal.png'
        }
        anchor_list1 = {
            1: 'templates/event_calendar.png',
            2: 'templates/bank.png'
        }
        anchor_list2 = {
            1: 'templates/event_community.png',
            2: 'templates/weekly_coupon.png'
        }
        move_directions = {
            1: (200, 211, 800, 220),
            2: (800, 211, 200, 220)
        }
        self.back_to_world()
        self.automator.wait_and_click(event_list[event_type])
        if self.automator.wait_and_click(path):
            return True

        # 先划到最左
        pos = move_directions[event_type]
        x1, y1, x2, y2 = pos

        while not self.automator.wait_for_image(anchor_list1[event_type], timeout=0):
            self.automator.adb.swipe(x1, y1, x2, y2)
        while not self.automator.wait_and_click(path, timeout=1):
            self.automator.adb.swipe(x2 - 169, y2, x1, y1)
            time.sleep(0.5)
            if self.automator.wait_for_image(anchor_list2[event_type], timeout=0):
                return False
        return True

    def sidebar_searching(self, path: str, timeout: int = 3, threshold: float = 0.8):
        self.back_to_world()
        # 点出面板
        self.automator.adb.tap(6, 890, random_range=1)
        time.sleep(0.2)
        # 点击城镇
        self.automator.adb.tap(176, 404)
        time.sleep(0.1)
        rolling = True
        while rolling:
            pos = self.automator.get_image_pos(path, timeout=timeout, threshold=threshold)
            if pos:
                return pos
            if self.automator.wait_for_image('templates/travel_supply.png', timeout=1):
                rolling = False
            self.automator.adb.swipe(337, 900, 337, 490)
            time.sleep(1)

    def task_detect(self):
        world_icons = {
            0: 'templates/reconnect.png',
            1: 'templates/cancel_btn.png',
            2: 'templates/world_search.png',
            3: 'templates/intelligence_btn.png',
            4: 'templates/orders.png',
            5: 'templates/island_maps.png'
        }
        games_status = self.automator.multiple_images_pos(world_icons)
        print(games_status)

    def test2(self):
        i = 100
        while True:
            i = i + 1
            screenshot = self.automator.adb.screenshot()
            filename = f'tests/{i}.png'
            img = Image.fromarray(screenshot)
            img.save(filename)

    def earth_core(self):
        self.back_to_world()
        self.automator.wait_and_click('templates/earth_core.png')
        pos = self.automator.get_images_pos('templates/core_ready.png')
        for value in pos:
            self.automator.adb.tap(value[0], value[1])
            self.automator.wait_and_click('templates/core_gain.png')
            if self.automator.wait_and_click('templates/adventure_gain2.png'):
                self.automator.adb.back()
            time.sleep(1)
        self.back_to_world()

    def test3(self):
        print(self.automator.get_image_pos('templates/store_refresh.png', threshold=0.47))

    def arena_fight(self):
        timestamp = time.time()
        result = ''
        battle_x = 937
        time_out = 3
        battle_y = [468, 665, 860, 1056, 1252]
        pos = self.sidebar_searching("templates/Archer_sidebar_anchor.png")
        if not pos:
            result = result + '定位失败，结束任务。'
            self.back_to_world()
            return result
        self.automator.adb.tap(pos[0], pos[1])
        self.automator.wait_for_image("templates/orders.png")
        self.automator.adb.swipe(600, 1000, 200, 1000)
        if not self.automator.wait_and_click("templates/arena_anchor.png", timeout=time_out):
            result = result + '竞技场已结束。'
            return result

        self.automator.wait_and_click("templates/arena_btn.png", timeout=time_out)

        time_left = 5
        i = 0
        j = 0
        fight_info = ''
        refresh = False
        while time_left > 0:
            text = self.automator.get_screen_text(with_qwen3=True)
            text = format_arena(text)
            my_power = text.get('my_power_numeric', 0)
            time_left = text.get('remaining_challenges', 99)

            # 如果本身战力为0，继续循环
            if my_power == 0 or time_left == 99:
                j = j + 1
                if j > 15:
                    duration = int(time.time() - timestamp) // 60
                    result = 'OCR失败次数过多，退出。' + result + f'共战斗了{i}场，用时：{duration}分钟。 战况：'
                    self.back_to_world()
                    return result
                continue

            # 找出五位玩家中战力最小的
            players = text['players']
            fight_index, fight_target = min(enumerate(players), key=lambda x: x[1]['combat_power_numeric'])
            print(fight_target)

            # 新规则： 不管对方战力如何，先打一场，失败了再刷新。，
            if refresh and self.automator.wait_and_click('templates/refresh_arena.png', threshold=0.9):
                i = i + 1
                refresh = False
                continue

            # 能够战斗的开打~
            player_name = fight_target['full_name']
            player_power = fight_target['combat_power']
            self.automator.adb.tap(battle_x, battle_y[fight_index])
            self.automator.wait_and_click('templates/fight.png')
            self.automator.wait_for_image("templates/arena_battle_record.png")
            if self.automator.wait_for_image("templates/arena_win.png", timeout=time_out):
                fight_info = fight_info + f'击败了{player_name}, 战力{player_power}。'
            else:
                fight_info = fight_info + f'惜败于{player_name}, 战力{player_power}。'
                refresh = True
            print(fight_info)

            # 返回挑战列表
            self.automator.adb.tap(500, 1890)

            i = i + 1
        duration = int(time.time() - timestamp) // 60
        result = result + f'共战斗了{i}场，用时：{duration}分钟。 战况: {fight_info}'
        self.back_to_world()
        return result

    def daily_charge_reward(self):
        self.back_to_world()
        self.automator.adb.tap(908, 99)
        self.automator.wait_and_click('templates/gift_box1.png', threshold=0.5, timeout=5)
        self.automator.wait_and_click('templates/gift_box2.png', timeout=0, threshold=0.5)
        i = 0
        while self.automator.wait_and_click('templates/gift_more.png', timeout=0):
            self.automator.wait_and_click('templates/gift_box1.png', threshold=0.5)
            self.automator.wait_and_click('templates/gift_box2.png', timeout=0, threshold=0.5)
            i = i + 1
        result = f'收获了{i}个礼物'
        self.back_to_world()
        return result

    def daily_commander_reward(self):
        self.back_to_world()
        result = ''
        # 点进统帅
        self.automator.wait_and_click('templates/commander_anchor.png', timeout=1)
        # 点击礼包
        if self.automator.wait_and_click('templates/commander_gain.png', timeout=1):
            time.sleep(0.1)
            self.automator.adb.tap(495, 424)
            result = result + '领取到统帅等级奖励。'
        # TODO: 点击礼盒目前总是点击不到，需要修正
        if self.automator.wait_and_click('templates/commander_reward.png', timeout=1, threshold=0.7):
            time.sleep(0.1)
            self.automator.adb.tap(795, 424)
            result = result + '领取普通礼盒奖励'

        # 点击加号
        self.automator.wait_and_click('templates/plus1.png', timeout=1)
        i = 0
        while self.automator.wait_and_click('templates/commander_use.png', timeout=1):
            i = i + 1
        if i > 0:
            result = f'使用了 {i}次统帅经验。'
        self.back_to_world()
        return result

    def frozen_treasure(self):
        self.back_to_world()
        self.automator.wait_and_click('templates/frozen_treasure.png')
        if not self.automator.wait_for_image('templates/frozen_treasure_anchor.png', timeout=2):
            self.automator.wait_and_click('templates/frozen_treasure_tab.png.png')
        self.automator.adb.tap(752, 793)
        i = 0
        while self.automator.wait_and_click('templates/claim2.png', timeout=1, threshold=0.5):
            time.sleep(0.1)
            i = i + 1

        self.automator.adb.tap(319, 793)
        j = 0
        while self.automator.wait_and_click('templates/claim2.png', timeout=1, threshold=0.5):
            time.sleep(0.1)
            j = j + 1
        if i > 0 or j > 0:
            result = f'成功领取{i}个每日任务和{j}个进度奖励。'
        else:
            result = '没有新的任务可领取。'
        self.back_to_world()
        return result

    def mining(self):
        result = ''
        have_alliance_mine = False
        mining_names = ['meal', 'wood', 'coal', 'iron']
        working_mines = []

        mining_dict = {
            1: 'templates/mine_meal_gen.png',
            2: 'templates/mine_wood_gen.png',
            3: 'templates/mine_coal_gen.png',
            4: 'templates/mine_iron_gen.png',
            5: 'templates/mine_meal_alliance.png',
            6: 'templates/mine_wood_alliance.png',
            7: 'templates/mine_coal_alliance.png',
            8: 'templates/mine_iron_alliance.png'
        }
        # 点击指定位置防止矿信息被遮挡
        self.back_to_world()
        time.sleep(1)
        # 检查当前的采矿情况
        print('backed to world')
        mining_status = self.automator.multiple_images_pos(mining_dict)
        print('get all status', mining_status)
        for i in range(4):
            mining_name = mining_names[i]
            common_index = i + 1
            alliance_index = i + 5

            common_value = mining_status.get(common_index)
            alliance_value = mining_status.get(alliance_index)

            common_exist = common_value is not None
            alliance_exist = alliance_value is not None

            if common_exist and alliance_exist:
                pass
            elif common_exist:
                working_mines.append(mining_name)
            elif alliance_exist:
                working_mines.append(mining_name)
                have_alliance_mine = True

        if have_alliance_mine and len(working_mines) == 4:
            result = '所有矿产都在正常开采, 跳过任务。'
            return result

        # 如果在上一步中没有找到盟矿，当首先处理盟矿
        if not have_alliance_mine:
            alliance_search_path = {
                1: 'templates/mine_meal_alliance_search.png',
                2: 'templates/mine_wood_alliance_search.png',
                3: 'templates/mine_coal_alliance_search.png',
                4: 'templates/mine_iron_alliance_search.png'
            }

            self.automator.wait_and_click('templates/world_search.png', timeout=1)
            self.automator.adb.swipe(100, 1350, 900, 1350, 500)
            time.sleep(0.1)

            alliance_status = self.automator.multiple_images_pos(alliance_search_path)
            for key, value in alliance_status.items():
                if value is None:
                    continue

                temp_name = mining_names[key - 1]
                pos = mining_status[key]
                if pos is not None:
                    y = pos[1]
                    self.automator.adb.tap(332, y)
                    self.automator.wait_and_click('templates/OK_btn.png', timeout=2)
                    time.sleep(0.2)
                    text = self.automator.get_screen_text((100, y - 10, 300, y + 45),
                                                          preprocess=False, numbers=True, with_qwen3=True)
                    print(text)
                    wait_h, wait_m, wait_s = text
                    wait_time = wait_m * 60 + wait_s - 2
                    time.sleep(wait_time)
                    working_mines.remove(temp_name)
                    pass

                # 开始处理盟矿
                self.automator.adb.tap(value[0], value[1])
                time.sleep(0.1)
                self.automator.adb.tap(546, 1820)
                self.automator.wait_and_click('templates/mine_btn1.png')
                self.automator.wait_and_click('templates/mine_btn2.png')

                # 取消第二，第三英雄
                time.sleep(0.3)
                self.automator.adb.tap(650, 477)
                time.sleep(0.1)
                self.automator.adb.tap(950, 477)
                if self.automator.wait_and_click('templates/march.png'):
                    working_mines.append(temp_name)
                    result = f'成功采集盟矿: {temp_name}'

        # 从数组中剔除盟矿与在采矿
        for i in working_mines:
            mining_names.remove(i)

        # 开始采集未采矿
        mining_search_dict = {
            'meal': (229, 1367),
            'wood': (472, 1368),
            'coal': (711, 1369),
            'iron': (947, 1365)
        }
        result = result + ', 成功采集普矿:'
        for item in mining_names:
            x, y = mining_search_dict[item]
            # 点击“查找”并划到最右边
            self.automator.wait_and_click('templates/world_search.png', timeout=3)
            self.automator.adb.swipe(900, 1350, 100, 1350, 500)

            # 滑动后必须等待，否则会找不到或者采矿不正确
            time.sleep(0.2)

            # 如果矿不存在则不进行开采
            self.automator.adb.tap(x, y)
            time.sleep(0.1)
            self.automator.adb.tap(546, 1820)

            if self.automator.wait_and_click('templates/mine_btn1.png', timeout=3):
                time.sleep(0.3)
                # 检查是否正确的采矿英雄
                if self.automator.wait_for_image(f'templates/mine_{item}_hero.png', timeout=1):
                    # 移除多余的英雄
                    self.automator.adb.tap(650, 477)
                    time.sleep(0.1)
                    self.automator.adb.tap(950, 477)
                    # 点击出击
                    time.sleep(0.1)
                    self.automator.adb.tap(828, 1821)
                    result = result + f' {item}'
                else:
                    time.sleep(0.1)
                    self.back_to_world()
        self.back_to_world()
        return result

    def crystal_deep(self):
        result = ''
        pos = self.sidebar_searching('templates/Shield_sidebar_anchor.png')
        if not pos:
            result = result + '定位失败，结束任务。'
            self.back_to_world()
            return result
        self.automator.adb.tap(pos[0], pos[1])
        self.automator.wait_for_image("templates/orders.png")
        if self.automator.wait_and_click('templates/crystal_deep.png', timeout=2):
            i = 0
            while self.automator.wait_and_click('templates/claim1.png', threshold=0.5, timeout=1):
                i = i + 1
                if i > 5:
                    break
            x = [328, 543, 757, 971]
            for x_pos in x:
                self.automator.adb.tap(x_pos, 753)
                self.automator.adb.tap(x_pos, 753)
            result = result + f'成功领取{i}次奖励'
        else:
            result = result + '没有可领取奖励。'
        self.back_to_world()
        return result

    def strength_cans(self):
        result = ''
        pos = self.sidebar_searching('templates/Shield_sidebar_anchor.png')
        if not pos:
            result = result + '定位失败，结束任务。'
            self.back_to_world()
            return result
        self.automator.adb.tap(pos[0], pos[1])
        self.automator.wait_for_image("templates/orders.png")
        self.automator.adb.swipe(200, 357, 850, 700)
        time.sleep(0.2)
        if self.automator.wait_and_click("templates/gift_box.png"):
            time.sleep(0.2)
            self.automator.tap_random_area(200, 1400, 800, 1600)
        pos = self.automator.get_image_pos('templates/strength_can.png', threshold=0.75)
        if pos:
            result = result + '成功领取体力。'
            self.automator.adb.tap(pos[0], pos[1])
            self.automator.wait_and_click('templates/claim3.png')
            result = result + self.monster_hunter(target_type=1, stop_value=180)
        return result

    def calculate_wait_time(self, wait_type: int = 0, extra_seconds: int = 0):
        wait_path = {
            0: 'queue_monster',
            1: 'queue_beast'
        }
        wait_time = 0
        try:
            pos = self.automator.get_image_pos(f'templates/{wait_path[wait_type]}.png', timeout=1)
            if pos:
                x, y = pos
                time_left = self.automator.get_screen_text((100, y + 10, 300, y + 45),
                                                           preprocess=False, numbers=True, with_qwen3=True)
                wait_h, wait_m, wait_s = time_left
                wait_time = (wait_m * 60 + wait_s) * 2 + extra_seconds
        finally:
            pass

        return wait_time

    def monster_hunter(self, target_type: int = 0, stop_value: int = 180):
        result = ''
        target = {
            0: ['behemoth', 'group7', 'march_monster'],
            1: ['beast', 'group8', 'march_beast']
        }
        icons = target[target_type]
        target_time = 0
        i = 0
        strength = 0
        try:
            while True:

                # 检测体力
                self.back_to_world()
                now_time = time.time()
                wait_time = self.calculate_wait_time(target_type)

                if now_time + wait_time > target_time:
                    target_time = now_time + wait_time
                if time.time() - target_time < 0:
                    continue

                self.automator.wait_and_click('templates/intelligence_btn.png')
                self.automator.wait_for_image('templates/intelligence_anchor.png', timeout=2)
                strength = self.automator.get_screen_text((900, 30, 1000, 90), preprocess=False,
                                                          numbers=True, with_qwen3=True)
                if strength:
                    strength = int(strength[0])
                if strength < stop_value:
                    result = result + f'当前体力：{strength}，停止任务。'
                    break

                # 处理下一步操作
                self.back_to_world()
                if self.automator.wait_for_image('templates/queue_assemble.png', timeout=2):
                    continue

                self.automator.wait_and_click('templates/world_search.png')
                self.automator.adb.swipe(100, 1350, 900, 1350, 500)
                time.sleep(0.2)
                self.automator.wait_and_click(f'templates/{icons[0]}.png', timeout=2)
                self.automator.adb.tap(546, 1820)
                self.automator.wait_and_click('templates/assemble_monster.png', timeout=2)
                if (target_type == 0 and
                        (not self.automator.wait_and_click('templates/bear_assemble2.png', timeout=2))):
                    result = result + 'return 集结失败'
                    continue
                self.automator.wait_and_click(f'templates/{icons[1]}.png', timeout=2)
                self.automator.wait_and_click(f'templates/{icons[2]}.png', threshold=0.95, timeout=0)
                i = i + 1
        except Exception as e:
            result = result + str(e)

        finally:
            result = result + f'已执行{i}次, 当前体力：{strength}'
            self.back_to_world()
            return result

    def deposit(self):
        self.event_locate('templates/bank.png', event_type=2)
        pos = self.automator.get_image_pos('templates/deposit.png')
        if pos:
            x, y = pos
            self.automator.adb.tap(x, y)
            self.automator.wait_and_click('templates/intelligence_gain2.png', timeout=5)
            time.sleep(0.5)
            self.automator.adb.tap(x, y)
            self.automator.adb.swipe(251, 1139, 600, 1139)
            self.automator.wait_and_click('templates/saving.png')
        self.back_to_world()

    def romulus_reward(self):
        result = ''
        pos = self.sidebar_searching('templates/Shield_sidebar_anchor.png')
        if not pos:
            result = result + '定位失败，结束任务。'
            self.back_to_world()
            return result
        self.automator.adb.tap(pos[0], pos[1])
        self.automator.wait_for_image("templates/orders.png")
        self.automator.adb.swipe(200, 300, 700, 1000)
        if self.automator.wait_and_click('templates/expert_romulus.png', timeout=2):
            result = result + '成功领取奖励'
        else:
            result = result + '没有可领取的奖励。'
        self.back_to_world()
        return result

    def test(self):
        # print(self.mining())
        # print(self.automator.get_images_pos('templates/claim1.png', threshold=0.5))
        # print(self.automator.get_images_pos('templates/claim2.png', threshold=0.5))
        # print(self.automator.get_images_pos('templates/test.png', threshold=0.8, position_threshold=10))
        # print(self.arena_fight())
        # print(self.monster_hunter(stop_value=180, target_type=1))
        print(self.romulus_reward())
        # print(self.automator.get_image_pos('templates/test2.png'))


def main():
    test = Test(device_id=0)
    test.test()


if __name__ == "__main__":
    main()
