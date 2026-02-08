from functions import *
from WinterLess import WinterLess
from intelligence import IntelligenceDeal
from bear import BearHunting


class TaskList:
    def __init__(self, winterless: WinterLess):
        self.winterless = winterless
        self.bear_start_time = 0

    def update_coordinate(self):
        if self.winterless.back_to_my_town(update_coordinate=True):
            return 'update coordinate success'
        else:
            return 'update coordinate failed'

    def alliance_donating(self):
        result = ''
        self.winterless.wait_and_click("templates/alliance.png", timeout=3)
        self.winterless.wait_and_click("templates/alliance_tech.png", timeout=3)
        self.winterless.wait_and_click("templates/alliance_tech_forever.png", timeout=3)
        if self.winterless.wait_and_click("templates/alliance_donate.png",
                                          hold=True, hold_time=8, timeout=3):
            result = result + '成功完成捐献。'
        # 退出到主界面
        self.winterless.back_to_world()
        return result

    def world_help(self):
        start_time = time.time()
        result = ''
        world_icons = {
            0: 'templates/attacked.png',
            1: 'templates/redpack1.png',
            2: 'templates/soldier_cure.png',
            3: 'templates/garrison.png',
            4: 'templates/island_visit.png',
            5: 'templates/bear.png'
        }
        games_status = self.winterless.multiple_images_pos(world_icons)
        for key, value in games_status.items():
            if value is None:
                continue
            x, y = value
            if key == 0:
                result = self.winterless.under_attack(x, y)
                return result
            elif key == 1:
                result = self.winterless.claim_redpack()
            elif key == 2:
                self.winterless.tap(x, y)
                pos = self.winterless.get_image_pos('templates/soldier_cure_btn.png')
                if pos:
                    self.winterless.tap(pos[0], pos[1])
                    time.sleep(0.1)
                    self.winterless.tap(pos[0], pos[1])
            elif key == 3:
                x = x + 227
                y = y + 15
                self.winterless.tap(x, y)
                self.winterless.wait_and_click('templates/OK_btn.png')
            elif key == 4:
                self.winterless.island_visit(x, y)
            elif key == 5:
                self.bear_hunting()
            break

        # 点击联盟互助
        while time.time() - start_time < 1.9:
            self.winterless.tap(853, 1650, random_range=1)
        return result

    def warehouse_reward(self):
        # 点出面板
        result = '仓库收益领取失败'
        pos = self.winterless.sidebar_searching(path='templates/warehouse_reward.png', timeout=1, threshold=0.88)
        if pos:
            self.winterless.tap(pos[0], pos[1])
            time.sleep(0.1)
            self.winterless.tap_random_area(400, 1000, 600, 1400)
            result = '成功领取仓库收益。'
        else:
            # 关闭面板
            self.winterless.tap(695, 818)

        return result

    def hero_recruit(self):
        result = ''
        self.winterless.back_to_world()
        self.winterless.wait_and_click('templates/2.hero.png')
        self.winterless.wait_and_click('templates/recruit.png')
        if self.winterless.wait_and_click('templates/recruit_free1.png'):
            result = result + '成功完成招募。'
        else:
            result = result + '招募失败。'
        self.winterless.tap(980, 681)
        self.winterless.back_to_world()
        return result

    def adventure_gains(self):
        self.winterless.back_to_world()
        self.winterless.wait_and_click("templates/adventure.png", timeout=2)
        self.winterless.wait_and_click("templates/adventure_treasure.png", timeout=1)
        self.winterless.wait_and_click("templates/adventure_gain2.png", timeout=3)
        self.winterless.back_to_world()
        return '执行领取探险收益。'

    def travel_gains(self):
        result = ''
        pos = self.winterless.sidebar_searching(path='templates/travel_supply_free.png')
        if not pos:
            self.winterless.back_to_world()
            result = result + '目前没有奖励。'
            return result
        self.winterless.tap(pos[0], pos[1])
        self.winterless.wait_and_click('templates/travel_supply_record.png')
        if self.winterless.wait_and_click('templates/claim2.png'):
            result = result + '成功领取补给。'
        else:
            result = result + '领取补给失败。'
        self.winterless.back_to_world()
        return result

    def check_hunter_status(self):
        return self.winterless.check_hunter_status()

    def monster_hunt(self):
        return self.winterless.monster_hunt()

    def monster_hunter(self):
        return self.winterless.monster_hunter()

    def alliance_mobilization(self):
        result = ''
        click_x = [300, 780]
        if not self.winterless.event_locate('templates/alliance_mobilization_anchor.png'):
            result = result + '没有找到联盟总动员任务，跳过。'
            return result

        self.winterless.wait_and_click('templates/completed.png')

        diamonds = self.winterless.get_images_pos('templates/diamond_500.png', timeout=1)
        diamonds_quantity = len(diamonds)

        # 如果两个钻石直接跳过
        if diamonds_quantity == 2:
            result = '都在刷新中，等待下次机会。'
            self.winterless.back_to_world()
            return result

        '''
        在没有两个钻石的情况下，如果有拳头，首先处理拳头
        - 有拳头且有一个钻石，可以直接回退
        '''
        result = self.winterless.start_fist('fist_860', diamonds_quantity=diamonds_quantity)
        if result != '':
            self.winterless.back_to_world()
            return result

        if time.localtime().tm_hour > 11:
            fist520 = self.winterless.start_fist('fist_520', diamonds_quantity=diamonds_quantity)
            if fist520 != '':
                result = result + '\n' + fist520
                self.winterless.back_to_world()
                return result

        # 这时已经没有拳头了, 另一个肯定是要刷新的
        if diamonds_quantity == 1:
            x = 780 if diamonds[0][0] > 540 else 300
            click_x.remove(x)

        i = 0
        for x in click_x:
            self.winterless.tap(x, 1123)
            if self.winterless.wait_and_click('templates/task_refresh.png'):
                self.winterless.wait_and_click('templates/task_refresh2.png')
                i = i + 1
                time.sleep(0.1)
            else:
                self.winterless.tap(999, 632)
                result = result + '跳过一个正在执行的任务。'

        if i > 0:
            result = result + f'成功刷新了{i}个任务'

        self.winterless.back_to_world()
        return result

    def mining(self):
        result = ''
        mining_names = ['meal', 'wood', 'coal', 'iron']
        alliance_mine, alliance_result = self.winterless.alliance_mining()
        if alliance_mine:
            mining_names.remove(alliance_mine)
        for mine_name in mining_names:
            result = result + self.winterless.general_mining(mine_name)

        self.winterless.back_to_world()
        result = alliance_result + result
        return result

    def soldier_training(self):
        training_type = ['Archer', 'Spearman', 'Shielded']
        training_paths = {}
        for i, item in enumerate(training_type):
            training_paths.update({i: f'templates/{item}_completed_world.png'})
            training_paths.update({i + 3: f"templates/{item}_idle_world.png"})
            pass

        # 点出面板
        self.winterless.back_to_world()

        time.sleep(0.2)
        self.winterless.tap(1, 900)

        time.sleep(0.2)
        # 点击城镇
        self.winterless.tap(176, 404)
        time.sleep(0.1)

        # 查找所有状态为完成或者空闲状态的兵营
        training_list = self.winterless.multiple_images_pos(paths=training_paths, threshold=0.92)
        training_list = {k: v for k, v in training_list.items() if v is not None}
        if not training_list:
            result = '无空闲兵营，跳过练兵'
            return result

        result = '成功开始训练：'
        for key, value in training_list.items():
            if not value:
                continue

            # 点出面板
            self.winterless.tap(1, 900)
            time.sleep(0.2)
            # 点击城镇
            self.winterless.tap(176, 404)
            time.sleep(0.1)

            # 点击造兵
            self.winterless.tap(value[0], value[1])

            # 处理进入兵营
            name = training_type[key % 3]
            if (self.winterless.wait_for_image('templates/orders.png', timeout=2) and
                    not self.winterless.wait_for_image(f'templates/{name}_training.png', timeout=1)):
                # 点击兵营两次
                self.winterless.tap(540, 860)
                time.sleep(0.2)
                self.winterless.tap(540, 860)
                time.sleep(0.2)
                self.winterless.tap(540, 860)
                time.sleep(0.2)
                # 点击训练按钮
                self.winterless.wait_and_click("templates/training.png", timeout=1)
                # 判定是否进入训练界面
                if self.winterless.wait_for_image("templates/training_identity.png", timeout=1):
                    # 开始造兵
                    self.winterless.tap(796, 1806)
                    time.sleep(0.1)
                    self.winterless.back()
                    time.sleep(0.1)
                    result = result + f' {name}'
        self.winterless.back_to_world()
        return result

    @loop_timeout(timeout_seconds=300)
    def daily_commander_reward(self, should_break):
        self.winterless.back_to_world()
        result = ''
        # 点进统帅
        self.winterless.wait_and_click('templates/commander_anchor.png', timeout=1)
        # 点击礼包
        if self.winterless.wait_and_click('templates/claim1.png', timeout=1):
            time.sleep(0.1)
            self.winterless.tap(495, 424)
            result = result + '领取到统帅等级奖励。'
        if self.winterless.wait_and_click('templates/commander_reward.png', timeout=1, threshold=0.7):
            time.sleep(0.1)
            self.winterless.tap(795, 424)
            result = result + '领取普通礼盒奖励'

        # 点击加号
        self.winterless.wait_and_click('templates/plus1.png', timeout=1)
        i = 0
        while self.winterless.wait_and_click('templates/commander_use.png', timeout=1):
            i = i + 1
            if should_break():
                break
        if i > 0:
            result = f'使用了 {i}次统帅经验。'
        self.winterless.back_to_world()
        return result

    @loop_timeout(timeout_seconds=300)
    def island_gain(self, should_break):
        result = ''
        self.winterless.back_to_my_town()

        self.winterless.tap(540, 960)
        if not self.winterless.wait_and_click('templates/island_enter.png'):
            result = result + '    找不到晨曦岛入口，'
            return result
        if not self.winterless.wait_for_image('templates/island_maps.png'):
            result = result + '    未按计划抵达晨曦岛。'
            return result
        # 获取收益，大图标
        i = 0
        while self.winterless.wait_and_click('templates/island_reward1.png', timeout=1, scale_match=True):
            if should_break():
                break
            i = i + 1
        if i > 0:
            result = result + '取得生命之树收益。'

        # 苹果收益
        if self.winterless.wait_and_click('templates/island_apple1.png', timeout=1, scale_match=True):
            self.winterless.wait_and_click('templates/claim1.png', scale_match=True)
            result = result + '取得苹果收益。'

        self.winterless.back_to_world()
        return result

    def store_purchase(self):
        return self.winterless.store_purchase()

    def crystal_lab(self):
        return self.winterless.crystal_lab()

    def alliance_treasure(self):
        return self.winterless.alliance_treasure()

    def earth_core(self):
        return self.winterless.earth_core()

    def daily_charge_reward(self):
        return self.winterless.daily_charge_reward()

    def daily_task_reward(self):
        return self.winterless.daily_task_reward()

    def set_alliance_mine(self):
        return self.winterless.set_alliance_mine()

    def deposit(self, period: int = 1):
        return self.winterless.deposit(period=period)

    def pet_treasure(self):
        return self.winterless.pet_treasure()

    def read_mails(self):
        return self.winterless.read_mails()

    def frozen_treasure(self):
        return self.winterless.frozen_treasure()

    def arena_fight(self):
        return self.winterless.arena_fight()

    def crystal_deep(self):
        return self.winterless.crystal_deep()

    def romulus_reward(self):
        return self.winterless.romulus_reward()
    
    def intelligence(self):
        self.winterless.back_to_world()
        executor = IntelligenceDeal(self.winterless)
        executor.process_intelligence()
        self.winterless.back_to_world()

    def strength_cans(self):
        return self.winterless.strength_cans()

    def recall_all_troops(self):
        self.winterless.recall_all_troops()

    def enable_pet_fight_buff(self):
        self.winterless.enable_pet_fight_buff()

    def bear_hunting(self):
        target_players = [
            ['辣椒', '暧昧', '木瓜', '三千梨花树', '节能', '土豆嫂牛肉', 'xy520', '可乐',
             '乱怼', '荷华', '翅膀', '西瓜', '边边', '猴儿', '太美', '宫本'],
            ['肉', '暧昧', '木瓜', '三千梨花树', '节能', '土豆嫂牛肉', 'xy520', '可乐',
             '乱怼', '荷华', '翅膀', '西瓜', '边边', '猴儿', '太美', '宫本'],
            ['元宝家的元宝', '辽东郡', '中年狗叔', '力刀刃', '白色糖果', '刹力神',
             '红色糖果', 'mars', '龙大师', '粉色糖果', '驿天蓬', '小蔡头']
        ]
        start_time = time.time()

        if start_time - self.bear_start_time > 3600 * 12:
            self.bear_start_time = start_time
        self.winterless.back_to_world()
        templates_path = {}
        troop_paths = {
            'ratio': 'templates/troop_ratio.png',
            'buff': 'templates/troop_buff.png',
            0: 'templates/troop_inner.png',
            1: 'templates/group1.png'
        }
        device_id = self.winterless.device_id
        assemble_interval = 350

        target_counter = len(target_players[device_id])
        for i in range(target_counter):
            path = f'templates/bear{device_id}/{i}.png'
            templates_path.update({i: path})

        templates_path.update({'war': 'templates/war_settings.png'})
        templates_path.update({'troop': 'templates/troop_buff.png'})
        templates_path.update({'depart': 'templates/group1.png'})
        templates_path.update({'no_queue': 'templates/troop_purchase.png'})

        bear = BearHunting(template_paths=templates_path, troop_paths=troop_paths, winterless=self.winterless)

        assemble_time = 0
        while True:
            new_time = time.time()
            if new_time - self.bear_start_time >= 60 * 25:
                print('自动开车、上车时间结束，程序将自动退出，有需要请手动操作。')
                break
            # 每10秒刷动一次
            if new_time - assemble_time >= assemble_interval:
                self.winterless.back_to_world()
                assemble_time = bear.bear_assemble()
                if not assemble_time:
                    assemble_time = new_time - assemble_interval
                    self.winterless.back_to_world()
                self.winterless.wait_and_click('templates/assemble.png')
                for _ in range(7):
                    self.winterless.automator.swipe(540, 1600, 540, 300, duration=300)
            elif int(new_time % 60) % 15 == 0:
                self.winterless.automator.swipe(540, 1600, 540, 300, duration=300)
                time.sleep(0.2)

            anchors = bear.get_images_pos()

            for key, value in anchors.items():
                # 如果返回值为空，直接处理下一组
                if value is None:
                    continue

                # 序号为int，代表有刷到玩家，处理后马上中断当前轮回
                if isinstance(key, int):
                    name = target_players[device_id][key]
                    # 如果5分钟内加入过该玩家，跳过
                    last_joined = bear.joined_time.get(name, 0)
                    if new_time - last_joined <= 60 * 5:
                        continue
                    troop_id = key % 4
                    y = value[1] + 171
                    bear.bear_joining(target=name, troop_id=troop_id, target_y=y)
                    # 这里是否要中断当前轮回？有没有可能同一界面有多个可加入玩家？
                    break
                # 如果没有匹配到玩家，而且还处于队伍列表，马上中断当前轮回
                elif key == 'war':
                    break
                # 如果在世界界面重新点进队伍列表
                else:
                    self.winterless.back_to_world()
                    self.winterless.wait_and_click('templates/assemble.png')
                    # 刷到最底端
                    for _ in range(10):
                        self.winterless.automator.swipe(540, 1600, 540, 300, duration=300)
                    break
        pass

    def bear_swipe(self):
        if os.path.exists('sys_config.json'):
            with open('sys_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)

        # self.winterless.swap_hero_arm()

        pass

    def is_ready(self):
        return self.winterless.is_ready()

    def get_status(self):
        return self.winterless.get_status()

    def restart_game(self, force_restart=False):
        self.winterless.restart_game(force_restart=force_restart)
