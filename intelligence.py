import argparse
from functions import *
from MumuManager import MumuGameAutomator
from WinterLess import WinterLess


class IntelligenceDeal:
    def __init__(self, winterless: WinterLess):
        self.winterless = winterless

        self.paths = {
            0: 'templates/intelligence_red.png',
            1: 'templates/intelligence_monster.png',
            2: 'templates/intelligence_adv.png',
            3: 'templates/intelligence_rescue.png',
            4: 'templates/intelligence_gain.png'
        }

        self.required_strength = {
            0: 8,
            1: 8,
            2: 10,
            3: 12,
            4: 0
        }

    def deal_intelligence(self, x: int, y: int, i_type: int = 1, wait_time: float = 0):

        wait_time = wait_time

        # 点击图标
        self.winterless.tap(x, y)

        # 点击查看，如果没出现“前往查看”按钮就是点击了收获，随机点击屏幕后返回
        if not self.winterless.wait_and_click('templates/intelligence_check.png', timeout=5):
            self.winterless.tap_random_area(300, 1600, 600, 1800)
            print('找不到前往查看按钮，可能点击了收获')
            return wait_time

        if i_type == 1 or i_type == 0:
            # 判断当前是否有队列
            value = self.winterless.get_screen_text((200, 281, 364, 351), preprocess=False,
                                                    numbers=True, with_qwen3=True)
            if len(value) == 2:
                current, max_queue = value
                if current > max_queue:
                    return wait_time
            # 点击 出征
            self.winterless.wait_and_click('templates/intelligence_march.png')
            '''
            # 选择队伍，我这里是第八队
            如果没有出现第8点的队标，则返回（
            time.sleep(0.1)
            self.automator.tap(870, 184)
            '''
            if not self.winterless.wait_and_click('templates/group8.png'):
                self.winterless.wait_and_click('templates/close_popup2.png')
                return wait_time

            # 点击出征，队伍出发。
            if self.winterless.wait_and_click('templates/intelligence_depart1.png', threshold=0.9):
                # 获取队伍返回时间
                pos = self.winterless.get_image_pos('templates/queue_beast.png', timeout=1)
                if pos:
                    x, y = pos
                    current_time = time.time()
                    wait_time = current_time + self.winterless.get_seconds((100, y+10, 300, y + 45)) * 2
            else:
                self.winterless.back()
        elif i_type == 2:
            time.sleep(0.1)
            self.winterless.wait_and_click('templates/intelligence_adv_depart.png')
            time.sleep(0.1)
            self.winterless.wait_and_click('templates/fight.png')
            self.winterless.wait_and_click('templates/fight2.png', timeout=5)

        elif i_type == 3:
            time.sleep(0.1)
            if self.winterless.wait_and_click('templates/intelligence_rescue_depart.png'):
                self.winterless.wait_and_click('templates/intelligence_btn.png', threshold=0.8)
            time.sleep(0.2)

        return  wait_time

    @loop_timeout(timeout_seconds=1800)
    def process_intelligence(self, should_break):
        wait_time = 0
        terminate = False
        while True:
            if should_break() or terminate:
                break
            time.sleep(0.1)
            self.winterless.wait_and_click('templates/intelligence_btn.png', threshold=0.92, timeout=1)

            # 等待中间城镇图标出现
            self.winterless.wait_for_image('templates/intelligence_anchor.png')

            strength = self.winterless.get_screen_text((900, 30, 1000, 90), preprocess=False,
                                                       numbers=True, with_qwen3=True)
            strength = int(strength[0])

            positions = self.winterless.multiple_images_pos(self.paths, threshold=0.8)
            positions = {k: v for k, v in positions.items() if v is not None}

            # 去除空值后dict为空，则说明没有任务了，跳出循环
            if not positions:
                print("No more intelligence tasks")
                break
            # 找出最小的key，意味着最小的体力要求，如果当前体力小于等于该key对应的体力要求，则跳出循环
            minimum_key = min(positions.keys())
            for key, value in positions.items():
                if strength < self.required_strength[key]:
                    if key == minimum_key:
                        print("Not enough strength for intelligence task", strength, self.required_strength[key])
                        terminate = True
                        break
                    continue

                if (key == 0 or key == 1) and time.time() - wait_time < 0:
                    continue

                # 点击查看图标
                if key == 4:
                    time.sleep(0.5)
                    self.winterless.tap(value[0], value[1])
                    if not self.winterless.wait_and_click('templates/intelligence_gain2.png', timeout=5):
                        continue
                    time.sleep(2)
                    self.winterless.tap_random_area(300, 800, 600, 1000)
                    continue
                wait_time = self.deal_intelligence(x=value[0], y=value[1], i_type=key, wait_time=wait_time)

                self.winterless.wait_and_click('templates/intelligence_btn.png', threshold=0.92, timeout=1)


def main():
    args = argparse.ArgumentParser()
    args.add_argument('deviceid', type=int, help='Mumu模拟器的编号')
    args = args.parse_args()

    automator = MumuGameAutomator(mumu_device=args.deviceid, game_package="com.gof.china",
                                  mmm_path=r'D:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe')
    winterless = WinterLess(automator)

    automator = IntelligenceDeal(winterless)
    automator.process_intelligence()


if __name__ == '__main__':
    main()