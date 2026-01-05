import time
import re
import argparse

from TaskQueueManager import GameTaskManager
from MumuManager import MumuGameAutomator
from TaskManagerGUI import TaskManagerGUI
from typing import List, Dict

monster_target = {
    'turtle': False,
    'reaper': False,
    'gina': False,
    'mercenary1': False,
    'mercenary2': False
}


def back_to_world(automator: MumuGameAutomator):
    world_icons = {
        0: 'templates/sidebar_close.png',
        1: 'templates/reconnect.png',
        2: 'templates/orders.png',
        3: 'templates/island_anchor.png',
        4: 'templates/world_search.png',
        5: 'templates/intelligence_btn.png',
    }
    current_time = time.time()
    while True:
        games_status = automator.multiple_images_pos(world_icons)

        # 关闭左侧列表信息
        if games_status[0] is not None:
            automator.adb.tap(695, 818)
            continue

        if games_status[4] is not None and games_status[5] is not None:
            return True

        # 如果账号已登出
        if games_status[1] is not None:
            # 10分钟后再做操作
            time_left = int(time.time() - current_time)
            if time_left > 600:
                automator.adb.tap(780, 1197)
            else:
                time_left = 600 - time_left
                m = time_left//60
                s = time_left % 60
                print(f'wait for {m}:{s}')
                time.sleep(5)
            continue

        # 如果在城镇，则点击野外按钮
        if games_status[2] is not None:
            automator.adb.tap(978, 1826)
            continue

        # 如果在晨曦岛，点击退出
        if games_status[3] is not None:
            automator.adb.tap(66, 43)
            time.sleep(0.5)
            continue
        automator.adb.back()


def alliance_donating(automator: MumuGameAutomator):
    automator.wait_and_click("templates/alliance.png", timeout=3)
    automator.wait_and_click("templates/alliance_tech.png", timeout=3)
    automator.wait_and_click("templates/alliance_tech_forever.png", timeout=3)

    automator.wait_and_click("templates/alliance_donate.png", hold=True, hold_time=8, timeout=3)

    # 退出到主界面
    for i in range(1, 4):
        automator.wait_and_click(f"templates/close_popup{i}.png", timeout=1)

    i = 0
    while automator.wait_for_image("templates/escape.png", timeout=1):
        automator.wait_and_click("templates/escape.png", timeout=1)
        i = i + 1
        if i > 5:
            break
    return True


def world_help(automator: MumuGameAutomator):
    # 首先处理红包
    redpack = 'templates/redpack1.png'
    if automator.wait_for_image(redpack, timeout=0):
        automator.adb.tap(523, 1705)
        if automator.wait_and_click('templates/redpack2.png', timeout=1):
            while automator.wait_and_click('templates/redpack3.png'):
                automator.adb.tap(930, 347)
            automator.adb.tap(1001, 235)
        automator.adb.back()
    else:
        timestamp = time.time()
        while time.time() - timestamp < 1:
            automator.adb.tap(790, 1642)
            return True


def sidebar_searching(automator: MumuGameAutomator, path: str, timeout: int = 3, threshold: float = 0.8):
    back_to_world(automator)
    # 点出面板
    automator.adb.tap(1, 900)
    time.sleep(0.2)
    # 点击城镇
    automator.adb.tap(176, 404)
    time.sleep(0.1)
    rolling = True
    while rolling:
        pos = automator.get_image_pos(path, timeout=timeout, threshold=threshold)
        if pos:
            return pos
        if automator.wait_for_image('templates/travel_supply.png', timeout=1):
            rolling = False
        automator.adb.swipe(337, 900, 337, 490)
        time.sleep(1)


def warehouse_reward(automator: MumuGameAutomator):
    # 点出面板
    result = '仓库收益领取失败'
    pos = sidebar_searching(automator, path='templates/warehouse_reward.png', timeout=1, threshold=0.88)
    if pos:
        automator.adb.tap(pos[0], pos[1])
        time.sleep(0.1)
        automator.tap_random_area(400, 1000, 600, 1400)
        result = '成功领取仓库收益。'
    else:
        # 关闭面板
        automator.adb.tap(695, 818)

    return result


def hero_recruit(automator: MumuGameAutomator):
    pos = sidebar_searching(automator, path='templates/recruit1.png', threshold=0.9)
    if pos:
        automator.adb.tap(pos[0], pos[1])
        automator.wait_and_click('templates/recruit_free1.png')
    back_to_world(automator)


# 总是不会退出，待调试
def adventure_gains(automator: MumuGameAutomator):
    back_to_world(automator)
    automator.wait_and_click("templates/adventure.png", timeout=2)
    automator.wait_and_click("templates/adventure_treasure.png", timeout=1)
    time.sleep(0.1)
    if automator.wait_and_click("templates/adventure_gain2.png", timeout=1):
        time.sleep(0.2)
        automator.tap_random_area(450, 1007, 636, 1175)
    time.sleep(0.2)
    automator.wait_and_click("templates/escape.png", timeout=1)
    return '执行领取探险收益。'


def check_hunter_status(automator: MumuGameAutomator):
    global monster_target
    back_to_world(automator)
    automator.wait_and_click("templates/alliance.png")
    automator.wait_and_click("templates/alliance_war.png")
    automator.adb.tap(100, 184)
    time.sleep(0.1)
    automator.wait_and_click("templates/alliance_auto-join.png")
    time.sleep(0.3)
    result = automator.get_screen_text((200, 1100, 800, 1500))
    automator.adb.swipe(516, 1400, 548, 500)
    time.sleep(0.5)
    result = result + '\n' + automator.get_screen_text((200, 1350, 800, 1500))
    result = extract_numbers_with_context(result)
    back_to_world(automator)

    for i in result:
        if i['collected'] < i['total']:
            if i['collected'] < i['total']:
                if i['task_name'] == '冰原巨兽':
                    monster_target.update({'turtle': True})
                if i['task_name'] == '英雄的使命':
                    monster_target.update({'reaper': True})
                if i['task_name'] == '吉娜的反击':
                    monster_target.update({'gina': True})
                if '佣兵' in i['task_name']:
                    monster_target.update({'mercenary1': True})
                    monster_target.update({'mercenary2': True})
            else:
                if i['task_name'] == '冰原巨兽':
                    monster_target.update({'turtle': False})
                if i['task_name'] == '英雄的使命':
                    monster_target.update({'reaper': False})
                if i['task_name'] == '吉娜的反击':
                    monster_target.update({'gina': False})
                if '佣兵' in i['task_name']:
                    monster_target.update({'mercenary1': False})
                    monster_target.update({'mercenary2': False})
    # TODO: 佣兵荣耀
    return monster_target


def monster_hunt(automator: MumuGameAutomator):
    global monster_target

    back_to_world(automator)

    time.sleep(0.1)
    if not automator.wait_for_image('templates/assemble.png', timeout=1):
        return False

    # (200, 281, 364, 351)为行军信息区域，尽量保持队伍信息区域干净，否则影响效果
    # 确认是否有队列
    i = 0
    while True:
        value = automator.get_screen_text((200, 281, 364, 351), preprocess=False, numbers=True)
        if len(value) == 2:
            current, max_queue = value
            if 7 > max_queue > current:
                ready_to_march = True
            else:
                return False
            break
        else:
            automator.wait_and_click("templates/escape.png", timeout=1)
            i = i + 1
            if i > 5:
                return False

    if not ready_to_march:
        return False

    automator.wait_and_click('templates/assemble.png', timeout=1)
    time.sleep(0.1)

    # TODO: 佣兵荣耀
    monster_dict = {
        'turtle': 'templates/mon_turtle.png',
        'reaper': 'templates/mon_reaper.png',
        'gina': 'templates/mon_gina.png',
        'mercenary1': 'templates/mon_mercenary1.png',
        'mercenary2': 'templates/mon_mercenary2.png'
    }

    monster_status = automator.multiple_images_pos(monster_dict)
    for key, value in monster_status.items():
        if monster_target[key] and value:
            x = value[0] + 760
            y = value[1] + 28
            automator.adb.tap(x, y)
            time.sleep(0.3)
            automator.adb.tap(828, 1821)

    back_to_world(automator)


def start_fist(automator: MumuGameAutomator, mission_type: str = 'fist_860', diamonds_quantity: int = 0):
    result = ''
    position = automator.get_images_pos(f'templates/{mission_type}.png', timeout=0, threshold=0.98)
    fist_quantity = len(position)
    for pos in position:
        automator.adb.tap(pos[0], pos[1])
        automator.wait_and_click('templates/accept.png')
        # 接下来操作接受任务
        if diamonds_quantity == 1:
            result = f'获得一个{mission_type}任务，另一任务仍在刷新。'
            return result
        if fist_quantity == 2:
            result = f'居然有两个{mission_type}任务，活久见。。。'
            return result
        result = f'不管怎么样都有一个{mission_type}任务了，退出吧'
    return result


def alliance_mobilization(automator: MumuGameAutomator):
    result = ''
    click_x = [300, 780]
    if not event_locate(automator, 'templates/alliance_mobilization_anchor.png'):
        result = '没有找到联盟总动员任务，跳过。'
        return result

    automator.wait_and_click('templates/completed.png')

    diamonds = automator.get_images_pos('templates/diamond_500.png', timeout=1)
    diamonds_quantity = len(diamonds)

    # 如果两个钻石直接跳过
    if diamonds_quantity == 2:
        result = '都在刷新中，等待下次机会。'
        back_to_world(automator)
        return result

    '''
    在没有两个钻石的情况下，如果有拳头，首先处理拳头
    - 有拳头且有一个钻石，可以直接回退
    '''
    result = start_fist(automator, 'fist_860', diamonds_quantity=diamonds_quantity)
    if result != '':
        back_to_world(automator)
        return result

    if time.localtime().tm_hour > 11:
        fist520 = start_fist(automator, 'fist_520', diamonds_quantity=diamonds_quantity)
        if fist520 != '':
            result = result + '\n' + fist520
            back_to_world(automator)
            return result

    # 这时已经没有拳头了, 另一个肯定是要刷新的
    if diamonds_quantity == 1:
        x = 780 if diamonds[0][0] > 540 else 300
        click_x.remove(x)

    i = 0
    for x in click_x:
        automator.adb.tap(x, 1123)
        if automator.wait_and_click('templates/task_refresh.png'):
            automator.wait_and_click('templates/task_refresh2.png')
            i = i + 1
            time.sleep(0.1)
        else:
            automator.adb.tap(999, 632)
            result = result + '跳过一个正在执行的任务。'

    if i > 0:
        result = result + f'成功刷新了{i}个任务'

    back_to_world(automator)
    return result


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


def mining(automator: MumuGameAutomator):
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
    back_to_world(automator)
    time.sleep(1)
    # 检查当前的采矿情况
    mining_status = automator.multiple_images_pos(mining_dict)
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

        automator.wait_and_click('templates/world_search.png', timeout=1)
        automator.adb.swipe(100, 1350, 900, 1350, 500)
        time.sleep(0.1)

        alliance_status = automator.multiple_images_pos(alliance_search_path)
        for key, value in alliance_status.items():
            if value is None:
                continue

            temp_name = mining_names[key-1]
            pos = mining_status[key]
            if pos is not None:
                y = pos[1]
                automator.adb.tap(332, y)
                automator.wait_and_click('templates/OK_btn.png', timeout=2)
                time.sleep(0.2)
                wait_h, wait_m, wait_s = automator.get_screen_text((100, y - 10, 300, y + 45), preprocess=False,
                                                                   numbers=True)
                wait_time = wait_m * 60 + wait_s - 2
                time.sleep(wait_time)
                working_mines.remove(temp_name)
                pass

            # 开始处理盟矿
            automator.adb.tap(value[0], value[1])
            time.sleep(0.1)
            automator.adb.tap(546, 1820)
            automator.wait_and_click('templates/mine_btn1.png')
            automator.wait_and_click('templates/mine_btn2.png')

            # 取消第二，第三英雄
            time.sleep(0.3)
            automator.adb.tap(650, 477)
            time.sleep(0.1)
            automator.adb.tap(950, 477)
            if automator.wait_and_click('templates/march.png'):
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
        automator.wait_and_click('templates/world_search.png', timeout=3)
        automator.adb.swipe(900, 1350, 100, 1350, 500)

        # 滑动后必须等待，否则会找不到或者采矿不正确
        time.sleep(0.2)

        # 如果矿不存在则不进行开采
        automator.adb.tap(x, y)
        time.sleep(0.1)
        automator.adb.tap(546, 1820)

        if automator.wait_and_click('templates/mine_btn1.png', timeout=3):
            time.sleep(0.3)
            # 检查是否正确的采矿英雄
            if automator.wait_for_image(f'templates/mine_{item}_hero.png', timeout=1):
                # 移除多余的英雄
                automator.adb.tap(650, 477)
                time.sleep(0.1)
                automator.adb.tap(950, 477)
                # 点击出击
                time.sleep(0.1)
                automator.adb.tap(828, 1821)
                result = result + f' {item}'
            else:
                time.sleep(0.1)
                back_to_world(automator)

    return result


def soldier_training(automator: MumuGameAutomator):
    training_type = ['Archer', 'Spearman', 'Shielded']
    training_paths = {}
    for i, item in enumerate(training_type):
        training_paths.update({i: f'templates/{item}_completed_world.png'})
        training_paths.update({i + 3: f"templates/{item}_idle_world.png"})
        pass

    # 点出面板
    back_to_world(automator)
    time.sleep(0.2)
    automator.adb.tap(1, 900)
    time.sleep(0.2)
    # 点击城镇
    automator.adb.tap(176, 404)
    time.sleep(0.1)

    result = '练兵失败。'
    # 查找所有状态为完成或者空闲状态的兵营
    training_list = automator.multiple_images_pos(paths=training_paths, threshold=0.92)
    training_list = {k: v for k, v in training_list.items() if v is not None}
    if not training_list:
        result = '无空闲兵营，跳过练兵'
        return result

    result = '成功开始训练：'
    for key, value in training_list.items():
        if not value:
            continue

        # 点出面板
        automator.adb.tap(1, 900)
        time.sleep(0.2)
        # 点击城镇
        automator.adb.tap(176, 404)
        time.sleep(0.1)

        # 点击造兵
        automator.adb.tap(value[0], value[1])

        # 处理进入兵营
        name = training_type[key % 3]
        if (automator.wait_for_image('templates/orders.png', timeout=2) and not
                automator.wait_for_image(f'templates/{name}_training.png', timeout=1)):
            # 点击兵营两次
            automator.adb.tap(540, 860)
            time.sleep(0.2)
            automator.adb.tap(540, 860)
            time.sleep(0.2)
            automator.adb.tap(540, 860)
            time.sleep(0.2)
            # 点击训练按钮
            automator.wait_and_click("templates/training.png", timeout=1)
            # 判定是否进入训练界面
            if automator.wait_for_image("templates/training_identity.png", timeout=1):
                # 开始造兵
                automator.adb.tap(796, 1806)
                time.sleep(0.1)
                automator.adb.back()
                time.sleep(0.1)
                result = result + f' {name}'

    return result


def commander_reward(automator: MumuGameAutomator):
    back_to_world(automator)
    result = ''
    # 点进统帅
    automator.wait_and_click('templates/commander_anchor.png', timeout=1)
    # 点击礼包
    if automator.wait_and_click('templates/commander_gain.png', timeout=1):
        time.sleep(0.1)
        automator.adb.tap(495, 424)
        result = result + '领取到统帅等级奖励。'
    # 点击礼盒
    if automator.wait_and_click('templates/commander_reward.png', timeout=1):
        time.sleep(0.1)
        automator.adb.tap(795, 424)
        result = result + '领取普通礼盒奖励'

    # 点击加号
    automator.adb.tap(795, 424)
    i = 0
    while automator.wait_and_click('templates/commander_use.png', timeout=1):
        i = i + 1
    if i > 0:
        result = f'使用了 {i}次统帅经验。'
    back_to_world(automator)
    return result


# 晨曦岛操作
def island_gain(automator: MumuGameAutomator):
    back_to_world(automator)
    result = '没有获得任何收益。下次好运。'
    automator.swipe_random(192, 1400, 300, 1600,
                           700, 600, 800, 900, duration=300)
    time.sleep(1)
    pos1 = automator.get_image_pos('templates/my_town.png')
    if pos1:
        automator.adb.tap(pos1[0], pos1[1])
    else:
        result = '找不到城镇，跳过很执行'
        return result

    # 拜访邻居
    pos2 = automator.get_image_pos('templates/island_visit.png')
    if pos2:
        pos3_paths = {
            1: 'templates/island_gain1.png',
            2: 'templates/island_gain2.png'
        }
        automator.adb.tap(pos2[0], pos2[1])
        automator.wait_and_click('templates/OK_btn.png')
        pos3 = automator.multiple_images_pos(pos3_paths, timeout=3)
        i = 0
        for value in pos3.values():
            if value is None:
                continue
            automator.adb.tap(value[0], value[1])
            i = i + 1
            break
        automator.adb.tap(66, 43)
        time.sleep(0.5)
        if i > 0:
            result = '拜访邻居，获得收益。'
        back_to_world(automator)

    automator.adb.tap(540, 960)
    if not automator.wait_and_click('templates/island_enter.png'):
        result = result + '    找不到晨曦岛入口，'
        return result
    if not automator.wait_for_image('templates/island_maps.png'):
        result = result + '    未按计划抵达晨曦岛。'
        return result
    # 获取收益，大图标
    i = 0
    for value in automator.get_images_pos('templates/island_reward1.png'):
        automator.adb.tap(value[0], value[1])
        i = i + 1
    if i == 0:
        for value in automator.get_images_pos('templates/island_reward2.png', timeout=0):
            automator.adb.tap(value[0], value[1])
            i = i + 1
    if i > 0:
        result = result + '取得生命之树收益。'

    # 苹果收益
    if automator.wait_and_click('templates/island_apple1.png', timeout=1):
        automator.adb.tap(544, 1370)
        automator.wait_and_click('templates/intelligence_gain2.png')
        result = result + '取得苹果收益。'
    elif automator.wait_and_click('templates/island_apple2.png', timeout=0):
        automator.adb.tap(544, 1370)
        automator.wait_and_click('templates/intelligence_gain2.png')
        result = result + '取得苹果收益。'

    back_to_world(automator)
    return result


def store_purchase(automator: MumuGameAutomator):
    back_to_world(automator)
    purchase_paths = {
        1: 'templates/store_meal.png',
        2: 'templates/store_wood.png',
        3: 'templates/store_coal.png',
        4: 'templates/store_iron.png'
    }
    refresh_btn = 'templates/store_refresh.png'

    automator.wait_and_click('templates/Store.png')
    automator.wait_and_click('templates/store1_off.png')
    if not automator.wait_for_image('templates/store1_on.png'):
        back_to_world(automator)
        return False

    # print('greyout', end=' ')
    # print(automator.get_image_pos('templates/reconnect.png'))
    # automator.adb.tap(998, 813)
    while True:
        # 截图查找是否有资源标志
        purchase_list = automator.multiple_images_pos(purchase_paths)

        # 去除空值值
        purchase_list = {k: v for k, v in purchase_list.items() if v is not None}

        # 不为空时，说明还有东西买
        if purchase_list:
            for value in purchase_list.values():
                # 点击购买
                automator.adb.tap(value[0], value[1])
            # time.sleep(0.1)
        else:
            pos = automator.get_image_pos(refresh_btn)
            if pos:
                automator.adb.tap(pos[0], pos[1])
                time.sleep(1)
            else:
                break

    back_to_world(automator)


def event_locate(automator: MumuGameAutomator, path: str, event_type: int = 1):
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
    back_to_world(automator)
    automator.wait_and_click(event_list[event_type])
    if automator.wait_and_click(path):
        return True

    # 先划到最左
    pos = move_directions[event_type]
    x1, y1, x2, y2 = pos

    while not automator.wait_for_image(anchor_list1[event_type], timeout=0):
        automator.adb.swipe(x1, y1, x2, y2)
    while not automator.wait_and_click(path, timeout=1):
        automator.adb.swipe(x2 - 169, y2, x1, y1)
        time.sleep(0.5)
        if automator.wait_for_image(anchor_list2[event_type], timeout=0):
            return False
    return True


def crystal_lab(automator: MumuGameAutomator):
    # 点出面板
    back_to_world(automator)
    time.sleep(0.2)
    automator.adb.tap(1, 900)
    time.sleep(0.2)
    # 点击城镇
    automator.adb.tap(176, 404)
    time.sleep(0.1)

    # 点击矛兵营
    automator.adb.tap(339, 948)

    if automator.wait_for_image('templates/crystal_lab.png', timeout=3):
        print('yes')
        automator.adb.tap(797, 1434)
        pos = automator.get_image_pos('templates/crystal_btn.png', timeout=2)
        for _ in range(12):
            automator.adb.tap(pos[0], pos[1])

        if automator.wait_for_image('templates/fire_crystal_coupon.png', timeout=2):
            automator.adb.tap(790, 1750)

    back_to_world(automator)


def alliance_treasure(automator: MumuGameAutomator):
    back_to_world(automator)
    automator.wait_and_click('templates/alliance.png')
    automator.wait_and_click('templates/alliance_treasure.png')
    automator.adb.tap(788, 595)
    if not automator.wait_and_click('templates/quick_gain_small.png', timeout=2):
        while automator.wait_for_image('templates/claim1.png', timeout=1):
            automator.wait_and_click('templates/claim1.png', timeout=1)
    automator.adb.tap(488, 595)
    automator.wait_and_click('templates/intelligence_gain.png')
    automator.adb.tap(533, 294)
    back_to_world(automator)


def earth_core(automator: MumuGameAutomator):
    back_to_world(automator)
    automator.wait_and_click('templates/earth_core.png')
    pos = automator.get_images_pos('templates/core_ready.png')
    for value in pos:
        automator.adb.tap(value[0], value[1])
        automator.wait_and_click('templates/core_gain.png')
        if automator.wait_and_click('templates/adventure_gain2.png'):
            automator.adb.back()
        time.sleep(1)
    back_to_world(automator)


def daily_reword(automator: MumuGameAutomator):
    back_to_world(automator)
    automator.adb.tap(908, 99)
    automator.wait_and_click('templates/gift_box1.png')
    automator.wait_and_click('templates/gift_box2.png', timeout=0)
    i = 0
    while automator.wait_and_click('templates/gift_more.png', timeout=0):
        automator.wait_and_click('templates/gift_box1.png')
        automator.wait_and_click('templates/gift_box2.png', timeout=0)
        i = i + 1
    result = f'收获了{i}个礼物'
    back_to_world(automator)
    return result


def set_alliance_mine(automator: MumuGameAutomator):
    mining_pos = [(886, 924), (886, 1197), (885, 1471), (886, 1744)]
    mine_id = (int(time.strftime('%V')) + 3) % 4
    x, y = mining_pos[mine_id]
    back_to_world(automator)
    automator.wait_and_click('templates/star_anchor.png')
    automator.wait_and_click('templates/mark_star.png', offset_x=200, offset_y=53, timeout=1)
    automator.adb.tap(540, 960)
    # automator.adb.tap(500, 1160)
    if automator.wait_and_click('templates/demolish.png'):
        automator.wait_and_click('templates/OK_btn.png')

    # 处理附件队伍太多无法选中地面的问题
    keep_try = True
    while keep_try:
        automator.adb.tap(540, 960)
        if automator.wait_and_click('templates/build.png'):
            keep_try = False
        time.sleep(1)

    automator.adb.tap(800, 200)
    time.sleep(1)
    automator.adb.tap(x, y)
    automator.wait_and_click('templates/place.png')


def monster_hunter(automator: MumuGameAutomator):
    back_to_world(automator)
    result = ''
    try:
        automator.wait_and_click('templates/world_search.png')
        automator.adb.swipe(100, 1350, 900, 1350, 500)
        time.sleep(0.2)
        automator.wait_and_click('templates/monster.png')
        automator.adb.tap(546, 1820)
        automator.wait_and_click('templates/assemble_monster.png')
        if automator.wait_and_click('templates/bear_assemble2.png'):
            result = result + '准备集结：'
            automator.wait_and_click('templates/group7.png')
            if automator.wait_and_click('templates/march_monster.png', threshold=0.95, timeout=0):
                result = result + '成功开始集结。'
            else:
                result = result + '体力不够，取消集结。'
    finally:
        back_to_world(automator)
        return result


def deposit(automator: MumuGameAutomator):
    event_locate(automator, 'templates/bank.png', event_type=2)
    pos = automator.get_image_pos('templates/deposit.png')
    if pos:
        x, y = pos
        automator.adb.tap(x, y)
        time.sleep(1)
        automator.adb.tap(x, y)
        automator.adb.swipe(251, 1139, 600, 1139)
        automator.wait_and_click('templates/saving.png')
    back_to_world(automator)


def pet_treasure(automator: MumuGameAutomator):
    result = ''
    back_to_world(automator)
    automator.wait_and_click('templates/pet_anchor.png')
    automator.wait_and_click('templates/pet_go_pound.png')
    automator.wait_and_click('templates/pet_go_treasure.png')

    # time_left = automator.get_screen_text((343, 168, 743, 228), numbers=True)[0]
    # print(time_left)

    # 如果有已完成的任务先点完成任务
    coordinates = automator.get_images_pos('templates/pet_done.png')
    for item in coordinates:
        automator.adb.tap(item[0], item[1])
        time.sleep(0.2)
        automator.adb.tap(547, 1227)
        automator.wait_and_click('templates/intelligence_gain2.png')
        time.sleep(0.2)
        automator.adb.tap(961, 362)

    result = result + f'收获了{len(coordinates)}个宝箱。'

    senior = automator.get_images_pos('templates/pet_senior.png', threshold=0.95, timeout=1)
    medium = automator.get_images_pos('templates/pet_medium.png', threshold=0.95, timeout=0)
    final_list = senior + medium
    if len(final_list) < 3:
        junior = automator.get_images_pos('templates/pet_junior.png', threshold=0.95, timeout=0)
        final_list = final_list + junior
    for item in final_list:
        automator.adb.tap(item[0], item[1])
        automator.wait_and_click('templates/treasure_search.png')
        automator.wait_and_click('templates/treasure_search2.png')
        time.sleep(0.3)
        automator.adb.tap(961, 402)

    result = result + f'开始寻找{len(final_list)}个宝箱，其中{len(senior)}个高级宝箱，{len(medium)}个中级宝箱。'

    if automator.wait_and_click('templates/pet_share.png', threshold=0.9):
        automator.wait_and_click('templates/quick_gain_large.png')
        automator.wait_and_click('templates/intelligence_gain2.png')
        automator.wait_and_click('templates/close_popup2.png')
    back_to_world(automator)
    return result


def main():
    parser = argparse.ArgumentParser(description='MumuAutomation')
    parser.add_argument('deviceid', type=int, help='Mumu模拟器的编号')
    args = parser.parse_args()
    # abc = MumuGameAutomator(0, 'com.gof.china')
    # abc.restart_game()
    # abc.swipe_random(0,0, 1080, 1920, 0, 0, 1080, 1920)
    # abc.wait_and_click("templates/alliance_donate.png", hold=True, hold_time=5)
    device_id = args.deviceid
    automator = MumuGameAutomator(
        # 0 肉炒辣椒
        # 1 蛮僮人
        # 2 辣椒炒肉
        mumu_device=device_id,
        game_package="com.gof.china",  # 替换为实际游戏包名
        mmm_path=r'E:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe'
    )
    # automator.wait_and_click(abc, timeout=3)
    # print(automator.wait_for_image(abd, timeout=3))
    # automator.wait_and_click("templates/close_popup2.png")
    # automator.tap_random_area(200, 1600, 800, 1800)
    # automator.wait_and_click("templates/escape.png", timeout=1)

    # 2. 启动游戏（如果指定了包名）
    if automator.game_package:
        automator.start_game()

    # 3. 创建任务管理器
    # 创建任务管理器
    back_to_world(automator)

    manager = GameTaskManager(name=automator.adb.device_name, automator=automator)

    # 长间隔任务（间隔 > 600秒）
    manager.add_task('soldier_training', func=soldier_training, interval_seconds=1800, immediate=True)

    # 定时任务, 每小时
    manager.add_cron_task('Warehouse Reward', func=warehouse_reward, cron_expression='7 * * * *')
    manager.add_cron_task('Hero Recruit', func=hero_recruit, cron_expression='3 * * * *')
    manager.add_cron_task('CheckHunterStatus', func=check_hunter_status,
                          cron_expression='1 * * * *', immediate=True)
    # 定时任务，间隔时间更长
    manager.add_cron_task("alliance_donating", func=alliance_donating, cron_expression='5 */2 * * *')
    manager.add_cron_task('Alliance Treasure', func=alliance_treasure, cron_expression='45 */2 * * *')
    manager.add_cron_task('island tasks', func=island_gain, cron_expression='59 */2 * * *')
    manager.add_cron_task('Monster hunter', func=monster_hunter, cron_expression='50 */2 * * *')
    manager.add_cron_task('Fire Crystal', func=crystal_lab, cron_expression='30 3 * * *')
    manager.add_cron_task("Adventure", func=adventure_gains, cron_expression='40 */8 * * *')

    # 定时任务，每天一次
    manager.add_cron_task('Earth core', func=earth_core, cron_expression='35 3 * * *')
    manager.add_cron_task('Commander Reward', func=commander_reward, cron_expression='37 3 * * *')
    manager.add_cron_task('Daily Reward', func=daily_reword, cron_expression='39 3 * * *')
    manager.add_cron_task('Store Purchase', func=store_purchase, cron_expression='45 3 * * *')
    manager.add_cron_task('Bank Deposit', func=deposit, cron_expression='30 23 * * *')

    # 定时任务，更复杂的要求
    manager.add_cron_task('Warehouse Reward 1st', func=warehouse_reward, cron_expression='*/5 2 * * *')
    manager.add_cron_task('Warehouse Reward 2st', func=warehouse_reward, cron_expression='*/30 3-5 * * *')
    manager.add_cron_task('Pet Treasure', func=pet_treasure, cron_expression='45 1,7,15 * * *')

    # 短时间任务
    manager.add_task("world_help", func=world_help, interval_seconds=1)
    manager.add_task("Behemoth_hunt", func=monster_hunt, interval_seconds=15)
    manager.add_task("Mining", func=mining, interval_seconds=590, immediate=True)
    manager.add_task('Alliance Mobilization', func=alliance_mobilization, interval_seconds=150, immediate=True)

    # 特殊任务
    if device_id == 1:
        manager.add_cron_task('Alliance Mine Set', func=set_alliance_mine, cron_expression='40 7,19 * * *')

    # task_manager.register_task("alliance_donating", alliance_donating)
    # task_manager.register_task("world_hellp", world_hellp)
    # task_manager.run_continuous('alliance_donating')
    # task_manager.run_continuous('world_hellp', interval=1)
    manager.start()

    gui = TaskManagerGUI(manager)
    gui.run()
    # while True:
    #    time.sleep(1)


if __name__ == "__main__":
    main()
