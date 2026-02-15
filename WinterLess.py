import re

from functions import *
from MumuManager import MumuGameAutomator
from typing import List, Dict, Tuple


def format_arena(text: str):
    # 清理文本
    text = text.strip("' ,")

    # 定义各部分的正则表达式模式
    # 修改header_pattern，匹配"挑战列表"和"我的实力："之间任意字符（包括空格、换行等）
    header_pattern = r'^(挑战列表)[\s\S]*?我的实力：\s*([\d,]+)'

    # 玩家信息模式（捕获组：前缀、中文名、战斗力、得分、排行）
    # 修改player_pattern，更准确地匹配玩家信息，忽略字符串间的空格与换行，前缀[]部分可选，#号排名部分可选
    player_pattern = r'(?:\[([^\]]+)\]\s*)?([^\s]+)\s+([\d,.]+万?)\s+([\d,]+)(?:\s*#\s*(\d+))?'

    # 结束部分模式
    footer_pattern = r'今日剩余挑战次数：\s*(\d+)[\s\S]*?([^\s]+)$'

    # 匹配表头
    header_match = re.search(header_pattern, text, re.MULTILINE)

    # 从表头匹配位置之后开始查找玩家信息，避免匹配到表头数据
    start_pos = 0
    if header_match:
        start_pos = header_match.end()

    # 在表头之后的部分匹配所有玩家
    player_matches = re.findall(player_pattern, text[start_pos:], re.MULTILINE)

    # 匹配结束部分
    footer_match = re.search(footer_pattern, text, re.MULTILINE)

    # 构建结果字典
    result = {
    }

    # 填充表头信息
    if header_match:
        result["title"] = header_match.group(1)
        result["my_power"] = header_match.group(2)
        result["my_power_numeric"] = int(header_match.group(2).replace(',', ''))

    # 填充玩家信息
    players = []
    for match in player_matches:
        # match现在包含：(prefix_content, chinese_name, combat_power, score, rank)，其中prefix_content和rank可能为None
        prefix_content, chinese_name, combat_power, score, rank = match

        # 如果有前缀内容，则构造完整的前缀，否则前缀为空
        prefix = f"[{prefix_content}]" if prefix_content else ""

        # 计算战斗力的数值
        power_num = combat_power.replace(',', '')
        if '万' in power_num:
            power_num = float(power_num.replace('万', '')) * 10000
        else:
            power_num = float(power_num)

        # 如果有排名，则构造完整排名字符串，否则为空
        rank_str = f"#{rank}" if rank else ""
        rank_numeric = int(rank) if rank else 0

        player_data = {
            "full_name": f"{prefix}{chinese_name}",
            "prefix": prefix,
            "chinese_name": chinese_name,
            "combat_power": combat_power,
            "combat_power_numeric": power_num,
            "score": score,
            "score_numeric": int(score.replace(',', '')),
            "rank": rank_str,
            "rank_numeric": rank_numeric
        }
        players.append(player_data)

    result['players'] = players
    # 填充结束部分
    if footer_match:
        result["remaining_challenges"] = int(footer_match.group(1))
        result["refresh_button"] = footer_match.group(2)

    return result


class WinterLess:
    def __init__(self, automator: MumuGameAutomator):
        self.monster_target = {
            'turtle': False,
            'reaper': False,
            'gina': False,
            'mercenary1': False,
            'mercenary2': False
        }
        self.coordinate = []
        self.automator = automator
        self.device_id = self.automator.mumu_device
        self.bear_start_time = 0

    # 常用函数直接调用
    def back(self):
        self.automator.back()

    def tap(self, x: int, y: int, random_range: int = 3):
        return self.automator.tap(x, y, random_range)

    def wait_and_click(self, template_path: str, timeout: int = 3, hold: bool = False, hold_time: int = 3,
                       threshold: float = 0.8, offset_x: int = 0, offset_y: int = 0,
                       scale_match: bool = False, scale_range: tuple = (0.5, 2.0)) -> bool:
        return self.automator.wait_and_click(template_path, timeout, hold, hold_time, threshold, offset_x, offset_y,
                                             scale_match, scale_range)

    def get_screen_text(self, region: Tuple[int, int, int, int] = None,
                        numbers: bool = False, preprocess: bool = True, with_qwen3: bool = True) -> str:
        return self.automator.get_screen_text(region, numbers, preprocess, with_qwen3)

    def wait_for_image(self, template_path: str, timeout: int = 3,
                       threshold: float = 0.8) -> bool:
        return self.automator.wait_for_image(template_path, timeout, threshold)

    def multiple_images_pos(self, paths: dict = None, timeout: int = 0, threshold: float = 0.8):
        return self.automator.multiple_images_pos(paths, timeout, threshold)

    def tap_random_area(self, x1: int, y1: int, x2: int, y2: int):
        return self.automator.tap_random_area(x1, y1, x2, y2)

    def get_image_pos(self, template_path: str, timeout: int = 3, threshold: float = 0.8,
                      offset_x: int = 0, offset_y: int = 0,
                      scale_match: bool = False, scale_range: tuple = (0.5, 2.0)) -> Tuple[int, int]:
        return self.automator.get_image_pos(template_path, timeout, threshold, offset_x, offset_y,
                                            scale_match, scale_range)

    def get_images_pos(self, template_path: str, timeout: int = 10,
                       threshold: float = 0.8, position_threshold: int = 8):
        return self.automator.get_images_pos(template_path, timeout, threshold, position_threshold)

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500):
        return self.automator.swipe(start_x, start_y, end_x, end_y, duration)

    def back_to_my_town(self, update_coordinate: bool = False):
        self.back_to_world()
        self.automator.swipe_random(192, 1400, 300, 1600,
                                    700, 600, 800, 900, duration=300)
        pos1 = self.get_image_pos('templates/my_town.png')
        if not pos1:
            return False
        self.tap(pos1[0], pos1[1])
        pos2 = self.get_image_pos('templates/my_town_anchor.png', scale_match=True)
        if not pos2:
            return False
        if update_coordinate:
            self.tap(pos2[0], pos2[1])
            self.wait_for_image('templates/island_enter.png')
            coordinate = self.get_screen_text((257, 1220, 449, 1302), numbers=True)
            self.back_to_world()
            self.coordinate = coordinate
        return True

    @loop_timeout(timeout_seconds=900)
    def back_to_world(self, timeout_check):
        world_icons = {
            0: 'templates/sidebar_close.png',
            1: 'templates/reconnect.png',
            2: 'templates/orders.png',
            3: 'templates/island_anchor.png',
            4: 'templates/world_search.png',
            5: 'templates/intelligence_btn.png',
            6: 'templates/my_town.png',
            7: 'templates/position_share.png'
        }
        current_time = time.time()
        while True:
            if timeout_check():
                break
            games_status = self.multiple_images_pos(world_icons)

            # 关闭左侧列表信息（因为会遮挡队列信息）
            if games_status[0] is not None:
                self.tap(695, 818)
                return True
            # 如果存在位置分享图标，则点击返回
            if games_status[7] is not None:
                self.back()
                return True
            if games_status[4] is not None and games_status[5] is not None:
                return True
            # 如果账号已登出
            if games_status[1] is not None:
                # 10分钟后再做操作
                time_left = int(time.time() - current_time)
                if time_left > 600:
                    self.tap(780, 1197)
                else:
                    time_left = 600 - time_left
                    m = time_left // 60
                    s = time_left % 60
                    print(f'wait for {m}:{s}')
                    time.sleep(30)
                continue
            # 如果在城镇，则点击野外按钮
            if games_status[2] is not None:
                self.tap(978, 1826)
                continue
            # 如果在晨曦岛，点击退出
            if games_status[3] is not None:
                self.tap(66, 43)
                time.sleep(0.5)
                continue

            # 处理回城图标遮挡目标的情况，比较少见，所以放最后。
            pos = games_status[6]
            if pos is not None:
                self.tap(pos[0], pos[1])
                time.sleep(0.5)
                continue
            self.back()
            time.sleep(0.1)

    def under_attack(self, x, y):
        # 点进进入军情
        result = ''
        war_analyze = {
            0: 'templates/war_assembl_attacking.png',
            1: 'templates/war_assembled.png',
            2: 'templates/war_marching.png',
            3: 'templates/war_scout.png'
        }
        self.tap(x, y, random_range=1)
        attacking_troops = self.get_images_pos(template_path='templates/war_target.png',
                                               position_threshold=15)
        if len(attacking_troops) >= 3:
            print('enable shield')
        war_types = self.multiple_images_pos(war_analyze)
        for key, value in war_types.items():
            if value is None:
                continue

            x, y = value
            time_left = self.get_seconds(region=(x + 100, y + 10, x + 800, y + 50))

            if key == 0 or key == 2:
                coordinate = self.get_screen_text((800, y - 22, 1200, y + 22), numbers=True)
                if coordinate == self.coordinate and time_left < 15:
                    self.enable_shield()
                break
            if key == 1:
                print('marching', value)
                coordinate = self.get_screen_text((800, y - 22, 1200, y + 22), numbers=True)
                if coordinate == self.coordinate:
                    print('downtown under attached')
            if key == 3:
                print('scout, seconds left:', time_left)
        self.back_to_world()
        return result

    def enable_shield(self, shield_type: int = 0):
        # TODO: 目前只能处理免费的盾牌
        types = [600, 822, 1044, 1266, 1488]
        self.back_to_world()
        self.wait_and_click('templates/enable_buffs.png')
        self.tap(280, 174)
        self.wait_and_click('templates/buff_shield.png')
        if self.wait_for_image('templates/buff_shield_btn.png'):
            i = shield_type
            self.tap(885, types[i])
            if i > 0:
                self.wait_and_click('templates/buff_with_diamond.png')
                self.tap(500, 1183)

        self.back_to_world()

    def claim_redpack(self):
        result = ''
        i = 0
        '''
        TODO: 
        目前红包需要聊天保留在盟聊，暂不支持切换世界/联盟领取红包
        '''
        self.tap(523, 1705)
        if self.wait_and_click('templates/redpack2.png', timeout=1):
            while self.wait_and_click('templates/redpack3.png'):
                self.tap(930, 347)
                i = i + 1
        result = result + f'应该领取了{i}个红包！'
        self.back_to_world()
        return result

    @loop_timeout(timeout_seconds=300)
    def sidebar_searching(self, should_break, path: str, timeout: int = 3, threshold: float = 0.8) \
            -> Tuple[int, int] | bool:
        self.back_to_world()
        # 点出面板
        while not self.wait_for_image('templates/sidebar_anchor1.png', timeout=1):
            self.tap(6, 895, random_range=1)
            if should_break():
                return False
        self.tap(6, 895, random_range=1)
        time.sleep(0.2)
        # 点击城镇
        self.tap(176, 404)
        time.sleep(0.1)
        rolling = True

        while rolling:
            pos = self.get_image_pos(path, timeout=timeout, threshold=threshold)
            if pos:
                return pos
            if self.wait_for_image('templates/travel_supply.png', timeout=1):
                rolling = False
            self.swipe(337, 900, 337, 490)
            time.sleep(1)
            if should_break():
                return False

    def check_hunter_status(self):
        result = ''
        self.back_to_world()
        self.wait_and_click("templates/alliance.png")
        self.wait_and_click("templates/alliance_war.png")
        self.tap(100, 184)
        time.sleep(0.1)
        self.wait_and_click("templates/alliance_auto-join.png")
        time.sleep(0.3)
        output = self.get_screen_text((200, 1100, 800, 1500))
        self.swipe(516, 1400, 548, 500)
        time.sleep(0.5)
        output = output + self.get_screen_text((200, 1350, 800, 1500))
        output = self.extract_numbers_with_context(output)
        if output:
            for i in output:
                if i['collected'] < i['total']:
                    if i['task_name'] == '冰原巨兽':
                        self.monster_target.update({'turtle': True})
                    if i['task_name'] == '英雄的使命':
                        self.monster_target.update({'reaper': True})
                    if i['task_name'] == '吉娜的反击':
                        self.monster_target.update({'gina': True})
                    if '佣兵' in i['task_name']:
                        self.monster_target.update({'mercenary1': True})
                        self.monster_target.update({'mercenary2': True})
                else:
                    if i['task_name'] == '冰原巨兽':
                        self.monster_target.update({'turtle': False})
                    if i['task_name'] == '英雄的使命':
                        self.monster_target.update({'reaper': False})
                    if i['task_name'] == '吉娜的反击':
                        self.monster_target.update({'gina': False})
                    if '佣兵' in i['task_name']:
                        self.monster_target.update({'mercenary1': False})
                        self.monster_target.update({'mercenary2': False})
            result = result + str(self.monster_target)
        else:
            result = result + 'OCR失败，信息更新失败。'
        self.back_to_world()
        return result

    @loop_timeout(timeout_seconds=120)
    def monster_hunt(self, should_break):
        result = ''
        self.back_to_world()

        # (200, 281, 364, 351)为行军信息区域，尽量保持队伍信息区域干净，否则影响效果
        # 确认是否有队列
        while True:
            if should_break():
                result = result + '获取队伍信息失败。'
                return result

            # 找不到行军标志，代表没有队列
            if not self.wait_for_image('templates/troop_anchor.png', timeout=1):
                break
            value = self.get_screen_text((200, 281, 364, 351), preprocess=False,
                                         numbers=True, with_qwen3=True)
            if len(value) == 2:
                current, max_queue = value
                if 7 > max_queue > current:
                    break
                else:
                    result = result + '没有空闲队伍。'
                    return result
            else:
                # 随机滑动，解决行军信息遮挡/干扰
                self.automator.swipe_random(400, 600, 410, 610,
                                            500, 700, 710, 710)

        if not self.wait_and_click('templates/assemble.png', timeout=1):
            result = result + '没有发现集结。'
            return result

        time.sleep(0.1)

        monster_dict = {
            'turtle': 'templates/mon_turtle.png',
            'reaper': 'templates/mon_reaper.png',
            'gina': 'templates/mon_gina.png',
            'mercenary1': 'templates/mon_mercenary1.png',
            'mercenary2': 'templates/mon_mercenary2.png'
        }

        monster_status = self.multiple_images_pos(monster_dict)
        for key, value in monster_status.items():
            if self.monster_target[key] and value:
                x = value[0] + 760
                y = value[1] + 28
                self.tap(x, y)
                time.sleep(0.3)
                self.tap(828, 1821)
                result = result + f'成功参与了集结{key}。'

        if result == '':
            result = result + '没有期待的目标。'
        self.back_to_world()
        return result

    def start_fist(self, mission_type: str = 'fist_860', diamonds_quantity: int = 0):
        result = ''
        position = self.get_images_pos(f'templates/{mission_type}.png', timeout=0, threshold=0.98)
        fist_quantity = len(position)
        for pos in position:
            self.tap(pos[0], pos[1])
            self.wait_and_click('templates/accept.png')
            # 接下来操作接受任务
            if diamonds_quantity == 1:
                result = f'获得一个{mission_type}任务，另一任务仍在刷新。'
                return result
            if fist_quantity == 2:
                result = f'居然有两个{mission_type}任务，活久见。。。'
                return result
            result = f'不管怎么样都有一个{mission_type}任务了，退出吧'
        return result

    @staticmethod
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
                        'total': y
                    })

        return result

    def general_mining(self, mine_name: str):
        result = ''
        self.back_to_world()
        gen_path = f'templates/mine_{mine_name}_gen.png'
        alliance_path = f'templates/mine_{mine_name}_alliance.png'
        # 检查矿是否正在开采，如果已经在开采直接跳过
        if (self.wait_for_image(gen_path, timeout=1, threshold=0.9)
                or self.wait_for_image(alliance_path, timeout=1, threshold=0.9)):
            return f'{mine_name}已在开采。'
        self.wait_and_click('templates/world_search.png', timeout=3)
        self.swipe(900, 1350, 100, 1350, 500)
        # 滑动后必须等待，否则会找不到或者采矿不正确
        time.sleep(0.2)
        search_path = f'templates/mine_{mine_name}_search.png'
        self.wait_and_click(search_path, timeout=3)
        self.wait_and_click('templates/search_btn.png')

        if self.wait_and_click('templates/mine_btn1.png', timeout=3):
            # 检查是否正确的采矿英雄
            if self.wait_for_image(f'templates/mine_{mine_name}_hero.png', timeout=1):
                # 移除多余的英雄
                self.remove_heros()
                self.tap(828, 1821)
                result = result + f' {mine_name}'
            else:
                self.back_to_world()
        return result

    def alliance_mining(self):
        mine_names = ['meal', 'wood', 'coal', 'iron']
        self.back_to_world()
        self.wait_and_click('templates/world_search.png', timeout=3)
        self.swipe(100, 1350, 900, 1350, 500)
        alliance_paths = {key: f'templates/mine_{mine_name}_alliance_search.png'
                          for key, mine_name in enumerate(mine_names)}
        alliance_status = self.multiple_images_pos(alliance_paths)
        mine_name = None
        for key, value in alliance_status.items():
            if value is None:
                continue
            co_mining_heros = {
                'meal': ['Molly', 'Ahmose'],
                'wood': ['Wayne', 'Molly'],
                'coal': ['Ahmose', 'Wayne'],
                'iron': ['Wayne', 'Molly']
            }
            mine_name = mine_names[key]

            # 点击盟矿按钮
            self.tap(value[0], value[1])

            # 检查盟矿是否正在开采
            if self.wait_for_image('templates/mine_alliance_working.png', timeout=3):
                self.back_to_world()
                return mine_name, f'盟矿{mine_name}已在开采。'

            # 检查是否已经当普矿开采
            pos = self.get_image_pos(f'templates/mine_{mine_name}_gen.png', timeout=3, threshold=0.9)
            if pos:
                # 召回冲突的普矿队伍
                _, y = pos
                self.tap(332, y)
                if not self.wait_and_click('templates/OK_btn.png', timeout=2):
                    self.back_to_world()
                    return mine_name, '召回队伍失败。'
                time.sleep(0.5)
                current_time = time.time()
                wait_time = self.get_seconds((100, y - 10, 300, y + 45))
                if wait_time > 60 * 10:
                    self.back_to_world()
                    return mine_name, '返回时间超过10分钟。'
                while time.time() - current_time < wait_time:
                    time.sleep(1)
            # 开采盟矿
            self.wait_and_click('templates/search_btn.png')
            if not self.wait_and_click('templates/mine_btn1.png'):
                self.back_to_world()
                return mine_name, '没有找到盟矿采集按钮'
            self.wait_and_click('templates/mine_btn2.png')
            if not self.wait_for_image(f'templates/mine_{mine_name}_hero.png', timeout=1):
                self.remove_heros(remove_all=True)
                if not self.change_hero(order=0, target=mine_name):
                    self.back_to_world()
                    return None
            self.remove_heros()
            for i, hero in enumerate(co_mining_heros[mine_name]):
                order = i + 1
                self.change_hero(order=order, target=hero)
            if self.wait_and_click('templates/march.png'):
                return mine_name, f'盟矿{mine_name}成功开始开采。'
        self.back_to_world()
        return mine_name, '采集盟矿失败。'

    @loop_timeout(timeout_seconds=30)
    def change_hero(self, should_break, order: int, target: str):
        x_aris = [300, 600, 900]
        x = x_aris[order]
        result = True
        self.tap(x, 500)
        path = f'templates/heros/{target}_small.png'
        self.swipe(500, 1100, 500, 1800)
        while not self.wait_and_click(path):
            self.swipe(500, 1150, 500, 900)
            if should_break():
                result = False
                break
        if not self.wait_and_click('templates/hero_switch.png', timeout=1):
            self.wait_and_click('templates/hero_assign.png', timeout=1)
        self.wait_and_click('templates/close_popup1.png', scale_match=True)
        return result

    def remove_heros(self, remove_all: bool = False):
        self.wait_for_image('templates/group1.png')
        if remove_all:
            self.tap(350, 477)
        else:
            self.tap(650, 477)
            time.sleep(0.1)
            self.tap(950, 477)
        time.sleep(0.1)

        # 晨曦岛操作

    def island_visit(self, x: int, y: int):
        # 拜访邻居
        result = ''
        self.tap(x, y)
        self.wait_and_click('templates/OK_btn.png')
        if self.wait_and_click('templates/island_gain1.png', timeout=5, scale_match=True):
            result = '拜访邻居，获得收益。'
        self.back_to_world()
        return result

    @loop_timeout(timeout_seconds=450)
    def store_purchase(self, should_break):
        self.back_to_world()
        purchase_paths = {
            1: 'templates/store_meal.png',
            2: 'templates/store_wood.png',
            3: 'templates/store_coal.png',
            4: 'templates/store_iron.png'
        }
        refresh_btn = 'templates/store_refresh.png'

        i = 0
        result = ''

        '''
        此处可改进，参考event相关
        '''
        self.wait_and_click('templates/Store.png')
        self.wait_and_click('templates/store1_off.png')
        if not self.wait_for_image('templates/store1_on.png'):
            self.back_to_world()
            result = result + '没有找到游荡商人。'
            return result

        # self.tap(998, 813)
        while True:
            if should_break():
                break
            # 截图查找是否有资源标志
            purchase_list = self.multiple_images_pos(purchase_paths)

            # 去除空值值
            purchase_list = {k: v for k, v in purchase_list.items() if v is not None}

            # 不为空时，说明还有东西买
            if purchase_list:
                for value in purchase_list.values():
                    # 点击购买
                    self.tap(value[0], value[1], random_range=1)
                    i = i + 1
                    time.sleep(0.2)
            else:
                # 点击不了刷新按钮可以退出
                if self.wait_and_click(refresh_btn, timeout=1):
                    time.sleep(2)
                else:
                    break
                time.sleep(1)
        result = result + f'成功从游荡商人处采购{i}次'
        self.back_to_world()
        return result

    @loop_timeout(timeout_seconds=300)
    def event_locate(self, should_break, path: str, event_type: int = 1):
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
            1: (200, 211, 780, 220),
            2: (780, 211, 200, 220)
        }
        self.back_to_world()
        self.wait_and_click(event_list[event_type])
        if self.wait_and_click(path):
            return True

        # 先划到最左
        pos = move_directions[event_type]
        x1, y1, x2, y2 = pos
        while not self.wait_for_image(anchor_list1[event_type], timeout=0):
            self.swipe(x1, y1, x2, y2, duration=800)
            if should_break():
                return False
        while not self.wait_and_click(path, timeout=1):
            self.swipe(x2 - 169, y2, x1, y1, duration=800)
            time.sleep(0.5)
            if self.wait_for_image(anchor_list2[event_type], timeout=0) or should_break():
                return False
        return True

    def crystal_lab(self):
        # TODO: 此处需要测试
        result = ''
        pos = self.sidebar_searching('templates/cavalry_sidebar_anchor.png')
        if pos:
            self.tap(pos[0], pos[1])
        else:
            result = result + '未找到矛兵营。'

        if self.wait_for_image('templates/crystal_lab.png', timeout=3):
            self.tap(797, 1434)
            pos = self.get_image_pos('templates/crystal_btn.png', timeout=2)
            for _ in range(12):
                self.tap(pos[0], pos[1])

            result = result + '成功提炼出火晶。'
            if self.wait_for_image('templates/fire_crystal_coupon.png', timeout=2):
                self.tap(790, 1750)
                result = result + '完成一次50%优惠的精炼火晶。'

        self.back_to_world()
        return result

    @loop_timeout(timeout_seconds=300)
    def alliance_treasure(self, should_break):
        self.back_to_world()
        result = ''
        self.wait_and_click('templates/alliance.png')
        self.wait_and_click('templates/alliance_treasure.png')
        self.tap(788, 595)
        if not self.wait_and_click('templates/quick_gain_small.png', timeout=2):
            i = 0
            while self.wait_for_image('templates/claim1.png', timeout=1):
                self.wait_and_click('templates/claim1.png', timeout=1)
                i = i + 1
                if should_break():
                    break
            result = result + f'获得{i}个盟友赠礼。'
        else:
            result = result + '一次获得至少12个盟友赠礼。'
        self.tap(488, 595)
        if self.wait_and_click('templates/intelligence_gain.png'):
            result = result + '获得战利品宝箱收益。'
            time.sleep(2)
            self.tap(533, 294)
        time.sleep(0.5)
        self.tap(533, 294)
        self.back_to_world()
        return result

    def earth_core(self):
        self.back_to_world()
        self.wait_and_click('templates/earth_core.png')
        pos = self.get_images_pos('templates/core_ready.png')
        for value in pos:
            self.tap(value[0], value[1])
            self.wait_and_click('templates/core_gain.png')
            if self.wait_and_click('templates/adventure_gain2.png'):
                self.back()
            time.sleep(1)
        self.back_to_world()

    @loop_timeout(timeout_seconds=300)
    def daily_charge_reward(self, should_break):
        self.back_to_world()
        self.tap(908, 99)
        self.wait_and_click('templates/gift_box1.png', threshold=0.5, timeout=5)
        self.wait_and_click('templates/gift_box2.png', timeout=0, threshold=0.5)
        i = 0
        while self.wait_and_click('templates/gift_more.png', timeout=0):
            self.wait_and_click('templates/gift_box1.png', threshold=0.5)
            self.wait_and_click('templates/gift_box2.png', timeout=0, threshold=0.5)
            i = i + 1
            if should_break():
                break
        result = f'收获了{i}个礼物'
        self.back_to_world()
        return result

    def daily_task_reward(self):
        result = ''
        self.back_to_world()
        self.wait_and_click('templates/daily_task.png')
        # TODO: 此处需要修改，需要切换到每日任务界面
        if self.wait_and_click('templates/quick_gain_small.png'):
            result = result + '领取奖励成功。'
        else:
            result = result + '目前没有奖励。'
        self.back_to_world()
        return result

    @loop_timeout(timeout_seconds=300)
    def set_alliance_mine(self, should_break):
        if self.automator.device_name != '蛮僮人':
            return "角色不可用"

        current = time.localtime()
        if current.tm_hour not in (7, 19) or not (40 <= current.tm_min <= 50):
            return "当前时间不在可放置时间，请手动操作"

        self.back_to_world()
        self.wait_and_click('templates/star_anchor.png')
        self.wait_and_click('templates/mark_star.png', offset_x=200, offset_y=53, timeout=1)
        self.wait_for_image('templates/mine_alliance_anchor.png', timeout=1)

        self.tap(540, 960)
        pos = self.get_image_pos('templates/demolish.png', timeout=3)
        if pos:
            _, y = self.get_image_pos('templates/alliance_mine_time.png')
            time_left = self.get_seconds((650, y - 20, 850, y + 20))
            if time_left >= 36000:
                return "盟矿剩余时间超过10小时，放弃"
            self.tap(pos[0], pos[1])
            self.wait_and_click('templates/OK_btn.png')

        # 处理附件队伍太多无法选中地面的问题
        while not self.wait_and_click('templates/build.png'):
            if should_break():
                return "盟矿放置失败。"
            self.tap(540, 960)
            self.wait_and_click('templates/select_ground.png', timeout=1)
            time.sleep(1)

        mining_pos = [(886, 924), (886, 1197), (885, 1471), (886, 1744)]
        mine_id = (int(time.strftime('%V')) + 3) % 4
        x, y = mining_pos[mine_id]
        self.tap(800, 200)
        time.sleep(1)
        self.tap(x, y)
        if self.wait_and_click('templates/place.png'):
            return "盟矿放置成功。"

    def get_seconds(self, region: Tuple[int, int, int, int] = None, preprocess: bool = True, with_qwen3: bool = True):
        time_left = 0
        try:
            text = self.get_screen_text(region, numbers=True, preprocess=preprocess, with_qwen3=with_qwen3)
            h, m, s = text
            time_left = h * 3600 + m * 60 + s
        except ValueError:
            pass
        return time_left

    def calculate_wait_time(self, wait_type: int = 0, extra_seconds: int = 0):
        wait_path = {
            0: 'queue_monster',
            1: 'queue_beast'
        }
        wait_time = 0
        pos = self.get_image_pos(f'templates/{wait_path[wait_type]}.png', timeout=1)
        if pos:
            x, y = pos
            wait_time = self.get_seconds((100, y + 10, 300, y + 45), preprocess=False)

        wait_time = wait_time * 2 + extra_seconds
        return wait_time

    @loop_timeout(timeout_seconds=600)
    def monster_hunter(self, should_break, target_type: int = 1, stop_value: int = 180):
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
                if should_break():
                    break
                # 检测体力
                self.back_to_world()
                now_time = time.time()
                wait_time = self.calculate_wait_time(target_type)

                if now_time + wait_time > target_time:
                    target_time = now_time + wait_time
                if time.time() - target_time < 0:
                    continue

                self.wait_and_click('templates/intelligence_btn.png')
                self.wait_for_image('templates/intelligence_anchor.png', timeout=2)
                strength = self.get_screen_text((900, 30, 1000, 90), preprocess=False,
                                                numbers=True, with_qwen3=True)
                if strength:
                    strength = int(strength[0])
                if strength < stop_value:
                    result = result + f'当前体力：{strength}，停止任务。'
                    break

                # 处理下一步操作
                self.back_to_world()
                if self.wait_for_image('templates/queue_assemble.png', timeout=2):
                    continue

                self.wait_and_click('templates/world_search.png')
                self.swipe(100, 1350, 900, 1350, 500)
                time.sleep(0.2)
                self.wait_and_click(f'templates/{icons[0]}.png', timeout=2)
                self.tap(546, 1820)
                self.wait_and_click('templates/assemble_monster.png', timeout=2)
                if (target_type == 0 and
                        (not self.wait_and_click('templates/bear_assemble2.png', timeout=2))):
                    result = result + 'return 集结失败'
                    continue
                self.wait_and_click(f'templates/{icons[1]}.png', timeout=2)
                self.wait_and_click(f'templates/{icons[2]}.png', threshold=0.8, timeout=1)
                i = i + 1
        except Exception as e:
            result = result + str(e)

        result = result + f'已执行{i}次, 当前体力：{strength}'
        self.back_to_world()
        return result

    def deposit(self, period: int = 1):
        period_locations = {
            1: (281, 1290),
            7: (788, 1290),
            15: (281, 1797),
            30: (788, 1797)
        }
        result = ''
        self.event_locate('templates/bank.png', event_type=2)
        # 检查存款是否到期
        if self.wait_for_image('templates/bank_started.png', timeout=1):
            result = result + '银行正在使用中，请稍后再试。'
            return result
        # 取出存款
        pos = self.get_image_pos('templates/band_withdraw.png', timeout=1)
        if pos:
            x, y = pos
            self.tap(x, y)
            self.wait_and_click('templates/intelligence_gain2.png', timeout=5)
            result = result + '取出存款完成。'
        # 没有充过值的，直接存30天
        if self.wait_for_image('templates/bank_unlock.png', timeout=1):
            # 如果1天的没有解锁，直接点一个月周期
            period = 30
        # 等待存款按钮出现
        self.wait_for_image('templates/bank_deposit.png', timeout=3)
        x, y = period_locations[period]
        self.tap(x, y)
        self.swipe(251, 1139, 600, 1139)
        if self.wait_and_click('templates/bank_saving.png', scale_match=True):
            result = result + '银行存款完成。'
        else:
            result = result + '银行存款失败。'
        self.back_to_world()
        return result

    def pet_treasure(self):
        result = ''
        self.back_to_world()
        self.wait_and_click('templates/pet_anchor.png')
        self.wait_and_click('templates/pet_go_pound.png')
        self.wait_and_click('templates/pet_go_treasure.png')

        # 如果有已完成的任务先点完成任务
        coordinates = self.get_images_pos('templates/pet_done.png')
        for item in coordinates:
            self.tap(item[0], item[1])
            time.sleep(0.2)
            self.tap(547, 1227)
            self.wait_and_click('templates/intelligence_gain2.png')
            time.sleep(0.2)
            self.tap(961, 362)

        result = result + f'收获了{len(coordinates)}个宝箱。'
        # TODO: 需要处理体力不足的判定。
        senior = self.get_images_pos('templates/pet_senior.png', threshold=0.95, timeout=1)
        medium = self.get_images_pos('templates/pet_medium.png', threshold=0.95, timeout=0)
        final_list = senior + medium
        if len(final_list) < 3:
            junior = self.get_images_pos('templates/pet_junior.png', threshold=0.95, timeout=0)
            final_list = final_list + junior
        for item in final_list:
            self.tap(item[0], item[1])
            self.wait_and_click('templates/treasure_search.png', timeout=1)
            self.wait_and_click('templates/treasure_search2.png', timeout=0)
            time.sleep(0.3)
            # self.tap(961, 402)
            self.wait_and_click('templates/close_popup1.png', scale_match=True, timeout=1)
            self.wait_and_click('templates/close_popup1.png', scale_match=True, timeout=1)

        result = result + f'开始寻找{len(final_list)}个宝箱，其中{len(senior)}个高级宝箱，{len(medium)}个中级宝箱。'

        # 点击联盟宝藏按钮，然后先分享，再获取盟友分享
        self.wait_and_click('templates/pet_share.png', threshold=0.9)
        if self.wait_and_click('templates/pet_share2.png'):
            self.tap(782, 350)
        if self.wait_and_click('templates/quick_gain_large.png'):
            self.wait_and_click('templates/intelligence_gain2.png')
        self.back_to_world()
        return result

    def read_mails(self):
        self.back_to_world()
        self.wait_and_click('templates/mails.png')
        positions = [130, 335, 540, 745]
        for x in positions:
            self.tap(x, 176)
            self.tap(713, 1854)
            self.tap(713, 1854)
            self.tap(713, 1854)
        self.back_to_world()

    @loop_timeout(timeout_seconds=60)
    def frozen_treasure(self, should_break):
        self.back_to_world()
        self.wait_and_click('templates/frozen_treasure.png')
        if not self.wait_for_image('templates/frozen_treasure_anchor.png', timeout=2):
            self.wait_and_click('templates/frozen_treasure_tab.png')
        self.tap(752, 793)
        i = 0
        while self.wait_and_click('templates/claim2.png', timeout=1, threshold=0.5):
            if should_break():
                break
            time.sleep(0.1)
            i = i + 1

        self.tap(319, 793)
        j = 0
        while self.wait_and_click('templates/claim2.png', timeout=1, threshold=0.5):
            if should_break():
                break
            time.sleep(0.1)
            j = j + 1
        if i > 0 or j > 0:
            result = f'成功领取{i}个每日任务和{j}个进度奖励。'
        else:
            result = '没有新的任务可领取。'
        self.back_to_world()
        return result

    @loop_timeout(timeout_seconds=900)
    def arena_fight(self, should_break):
        timestamp = time.time()
        result = ''
        battle_x = 937
        time_out = 30
        battle_y = [468, 665, 860, 1056, 1252]
        pos = self.sidebar_searching("templates/Archer_sidebar_anchor.png")
        if not pos:
            result = result + '定位失败，结束任务。'
            self.back_to_world()
            return result
        self.tap(pos[0], pos[1])
        self.wait_for_image("templates/orders.png")
        self.swipe(600, 1000, 200, 1000)
        if not self.wait_and_click("templates/arena_anchor.png"):
            result = result + '竞技场已结束。'
            return result

        self.wait_and_click("templates/arena_btn.png")

        i = 0
        fight_info = ''
        refresh_required = False
        while True:
            if should_break():
                break
            i = i + 1
            # 等待刷新按钮出现，防止数据读取错误
            self.wait_for_image('templates/refresh_arena.png', timeout=2)
            text = self.get_screen_text(with_qwen3=True)
            text = format_arena(text)
            my_power = text.get('my_power_numeric', 0)
            time_left = text.get('remaining_challenges', 99)

            # 如果本身战力为0，继续循环
            if my_power == 0 or time_left == 99:
                continue

            if time_left == 0:
                break

            # 找出五位玩家中战力最小的
            players = text['players']
            if len(players) != 5:
                continue
            fight_index, fight_target = min(enumerate(players), key=lambda x: x[1]['combat_power_numeric'])

            # 如果战力差距过大，则刷新
            if fight_target['combat_power_numeric'] - 1000000 > my_power or refresh_required:
                if self.wait_and_click('templates/refresh_arena.png', threshold=0.9):
                    refresh_required = False
                    continue

            # 能够战斗的开打~
            player_name = fight_target['full_name']
            player_power = fight_target['combat_power']
            self.tap(battle_x, battle_y[fight_index])
            self.wait_and_click('templates/fight.png')
            # 此处必须久等
            self.wait_for_image("templates/arena_battle_record.png", timeout=time_out)
            if self.wait_for_image("templates/arena_win.png"):
                fight_info = fight_info + f'击败了{player_name}, 战力{player_power}。'
                refresh_required = False
            else:
                fight_info = fight_info + f'惜败于{player_name}, 战力{player_power}。'
                refresh_required = True
            # 返回挑战列表
            self.tap(500, 1690)
        duration = int(time.time() - timestamp) // 60
        result = result + f'共循环{i}次，用时：{duration}分钟。 战况： ' + fight_info
        self.back_to_world()
        return result

    @loop_timeout(timeout_seconds=60)
    def crystal_deep(self, should_break):
        result = ''
        pos = self.sidebar_searching('templates/infantry_sidebar_anchor.png')
        if not pos:
            result = result + '定位失败，结束任务。'
            self.back_to_world()
            return result
        self.tap(pos[0], pos[1])
        self.wait_for_image("templates/orders.png")
        if self.wait_and_click('templates/crystal_deep.png', timeout=2):
            i = 0
            while self.wait_and_click('templates/claim1.png', threshold=0.7, timeout=1):
                if should_break():
                    break
                i = i + 1
            x = [328, 543, 757, 971]
            for x_pos in x:
                self.tap(x_pos, 753)
                self.tap(x_pos, 753)
            result = result + f'成功领取{i}次奖励'
        else:
            result = result + '没有可领取奖励。'
        self.back_to_world()
        return result

    def romulus_reward(self):
        result = ''
        pos = self.sidebar_searching('templates/infantry_sidebar_anchor.png')
        if not pos:
            result = result + '定位失败，结束任务。'
            self.back_to_world()
            return result
        self.tap(pos[0], pos[1])
        self.wait_for_image("templates/orders.png")
        self.swipe(200, 200, 800, 1000)
        if self.wait_and_click('templates/expert_romulus.png', timeout=2):
            result = result + '成功领取奖励'
        else:
            result = result + '没有可领取的奖励。'
        self.back_to_world()
        return result

    def strength_cans(self):
        result = ''
        pos = self.sidebar_searching('templates/infantry_sidebar_anchor.png')
        if not pos:
            result = result + '定位失败，结束任务。'
            self.back_to_world()
            return result
        self.tap(pos[0], pos[1])
        self.wait_for_image("templates/orders.png")
        self.swipe(200, 357, 850, 700)
        time.sleep(0.2)
        if self.wait_and_click("templates/gift_box.png"):
            time.sleep(0.2)
            self.tap_random_area(200, 1400, 800, 1600)
        pos = self.get_image_pos('templates/strength_can.png', threshold=0.75)
        if pos:
            result = result + '成功领取体力。'
            self.tap(pos[0], pos[1])
            self.wait_and_click('templates/claim3.png')
            result = result + self.monster_hunter(target_type=1, stop_value=180)
        return result

    def is_bear_day(self):
        self.event_locate(path='templates/bear_btn.png')
        text = self.get_screen_text((380, 1600, 700, 1700))
        text = re.sub(r'\s+', ' ', text.strip())
        if "预约自动开启" not in text:
            print('没有预约巨熊，请联系管理员提前预约')
            self.back_to_world()
            return False
        self.back_to_world()

        date_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', text)
        if date_match:
            date_str = date_match.group(1)
            current_time = time.localtime()
            current_date = f'{current_time.tm_year}-{current_time.tm_mon:02d}-{current_time.tm_mday:02d}'
            if current_date == date_str:
                return True
        return False

    def is_ready(self):
        return self.automator.is_ready()

    def get_status(self):
        return self.automator.get_status()

    def restart_game(self, force_restart=False):
        self.automator.restart_game(force_restart)
