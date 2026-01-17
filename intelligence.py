import argparse
import time
import functools
from MumuManager import MumuGameAutomator


def loop_timeout(timeout_seconds=300):
    """装饰器：为函数中的循环添加超时检查"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 创建超时检查函数
            start_time = time.time()

            def should_break():
                return time.time() - start_time > timeout_seconds

            # 将should_break作为第一个额外参数插入到原函数参数列表中
            # 对于实例方法，args[0]是self，args[1:]是原始参数
            # 我们需要传递 (self, should_break, *original_args)
            return func(*args[:1], should_break, *args[1:], **kwargs)

        return wrapper

    return decorator


class IntelligenceDeal:
    def __init__(self, automator: MumuGameAutomator):
        self.automator = automator

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

    def deal_intelligence(self, strength: int, x: int, y: int, i_type: int = 1, wait_time: float = 0):

        wait_time = wait_time
        strength = strength

        # 点击图标
        self.automator.adb.tap(x, y)

        # 点击查看，如果没出现“前往查看”按钮就是点击了收获，随机点击屏幕后返回
        if not self.automator.wait_and_click('templates/intelligence_check.png', timeout=2):
            self.automator.tap_random_area(300, 1600, 600, 1800)
            return strength, wait_time

        if i_type == 1 or i_type == 0:
            # 判断当前是否有队列
            value = self.automator.get_screen_text((200, 281, 364, 351), preprocess=False,
                                                   numbers=True, with_qwen3=True)
            if len(value) == 2:
                current, max_queue = value
                if current > max_queue:
                    return strength, wait_time
            # 点击 出征
            self.automator.wait_and_click('templates/intelligence_march.png')
            '''
            # 选择队伍，我这里是第八队
            如果没有出现第8点的队标，则返回（
            time.sleep(0.1)
            self.automator.adb.tap(870, 184)
            '''
            if not self.automator.wait_and_click('templates/group8.png'):
                self.automator.wait_and_click('templates/close_popup2.png')
                return strength, wait_time

            # 点击出征，队伍出发。
            if self.automator.wait_and_click('templates/intelligence_depart1.png', threshold=0.9):
                strength = strength - 8

                # 获取队伍返回时间
                pos = self.automator.get_image_pos('templates/queue_beast.png', timeout=1)
                if pos:
                    x, y = pos
                    current_time = time.time()
                    time_left = self.automator.get_screen_text((100, y + 10, 300, y + 45),
                                                               preprocess=False, numbers=True, with_qwen3=True)
                    wait_h, wait_m, wait_s = time_left
                    wait_time = current_time + (wait_m * 60 + wait_s) * 2 + 5
            else:
                self.automator.adb.back()
        elif i_type == 2:
            time.sleep(0.1)
            self.automator.wait_and_click('templates/intelligence_adv_depart.png')
            time.sleep(0.1)
            self.automator.wait_and_click('templates/fight.png')
            if self.automator.wait_and_click('templates/fight2.png', timeout=5):
                strength = strength - 10

        elif i_type == 3:
            time.sleep(0.1)
            if self.automator.wait_and_click('templates/intelligence_rescue_depart.png'):
                strength = strength - 12
                self.automator.wait_and_click('templates/intelligence_btn.png', threshold=0.8)
            time.sleep(0.2)

        return strength, wait_time

    @loop_timeout(timeout_seconds=1800)
    def process_intelligence(self, should_break):
        self.automator.wait_and_click('templates/intelligence_btn.png', threshold=0.99)

        strength = self.automator.get_screen_text((900, 30, 1000, 90), preprocess=False,
                                                  numbers=True, with_qwen3=True)

        if strength:
            strength = strength[0]
        else:
            strength = 8

        if strength >= 160:
            self.automator.wait_and_click('templates/expert_agnes.png')

        terminate = False
        wait_time = 0
        while not terminate:
            if should_break():
                break
            time.sleep(0.1)
            self.automator.wait_and_click('templates/intelligence_btn.png', threshold=0.92, timeout=1)

            positions = self.automator.multiple_images_pos(self.paths, threshold=0.8)

            i = 0

            for key, value in positions.items():
                if value is None or strength < self.required_strength[key]:
                    i = i + 1
                    if i == len(positions):
                        terminate = True
                    continue
                if (key == 0 or key == 1) and time.time() - wait_time < 0:
                    continue
                # 点击查看图标
                if key == 4:
                    time.sleep(0.5)
                    self.automator.adb.tap(value[0], value[1])
                    if not self.automator.wait_and_click('templates/intelligence_gain2.png', timeout=5):
                        continue
                    time.sleep(2)
                    self.automator.tap_random_area(300, 800, 600, 1000)
                    continue
                strength, wait_time = self.deal_intelligence(strength=strength,
                                                             x=value[0], y=value[1], i_type=key, wait_time=wait_time)

                self.automator.wait_and_click('templates/intelligence_btn.png', threshold=0.92, timeout=1)


def main():
    args = argparse.ArgumentParser()
    args.add_argument('deviceid', type=int, help='Mumu模拟器的编号')
    args = args.parse_args()

    automator = MumuGameAutomator(mumu_device=args.deviceid, game_package="com.gof.china",
                                  mmm_path=r'D:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe')

    automator = IntelligenceDeal(automator)
    automator.process_intelligence()


if __name__ == '__main__':
    main()