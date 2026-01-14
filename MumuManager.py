from typing import Tuple, Dict, Optional, List, Any
import subprocess
import json
import re
import time
import io
import random
import zlib
import numpy as np

from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from OCRProcessor import OCRProcessor
from ImageMatcher import ImageMatcher


def find_distinct_points(coordinates, threshold=8):
    """
    方法3：寻找显著不同的点
    """

    # 对坐标进行排序
    sorted_points = sorted(coordinates, key=lambda p: (p[1], p[0]))

    distinct_points = []

    for point in sorted_points:
        if not distinct_points:
            distinct_points.append(point)
        else:
            # 检查点是否与已有显著点相似
            similar = False
            for dp in distinct_points:
                distance = np.linalg.norm(np.array(point) - np.array(dp))
                if distance <= threshold:
                    similar = True
                    break

            if not similar:
                distinct_points.append(point)

    # 合并过于接近的点
    merged_points = []
    for point in distinct_points:
        if not merged_points:
            merged_points.append([point])
        else:
            # 检查是否可以合并到现有组
            merged = False
            for group in merged_points:
                group_center = np.mean(group, axis=0)
                distance = np.linalg.norm(np.array(point) - group_center)
                if distance <= threshold:
                    group.append(point)
                    merged = True
                    break

            if not merged:
                merged_points.append([point])

    # 计算最终的代表点
    final_points = []
    for group in merged_points:
        group_array = np.array(group)
        center = np.mean(group_array, axis=0)
        center_rounded = tuple(np.round(center).astype(int))
        final_points.append(center_rounded)

    # 按Y坐标排序
    final_points.sort(key=lambda p: p[1])

    return final_points


class ADBController:
    def __init__(self, device_id: int, mmm_path: str = r'C:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe'):
        self.device_id = device_id
        self.str_device_id = str(self.device_id)
        self.device_name = None
        self.mmm_path = [mmm_path]
        self._check_and_select_device()

    def get_all_devices_info(self):
        devices = {}
        try:
            # 获取设备列表

            mmm_info = self.mmm_path + ['info', '-v', 'all']
            result = subprocess.run(mmm_info, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                pass
            else:
                mmm_info = self.mmm_path + ['setting', '-v', 'all', '-a']
                result = subprocess.run(mmm_info, capture_output=True, text=True, check=True, encoding='utf-8')
            lines = result.stdout
            lines = json.loads(lines)

            for key, value in lines.items():
                name = value['name'] if 'name' in value else value.get('player_name', '')
                tab_name = format(zlib.crc32(name.encode('utf-8')), '08x')
                state = False
                if 'is_process_started' in value:
                    state = value['is_process_started']
                else:
                    mmm_info = self.mmm_path + ['adb', '-v', key]
                    result = subprocess.run(mmm_info, capture_output=True, text=True, encoding='utf-8')
                    lines = json.loads(result.stdout)
                    if 'adb_host' in lines:
                        state = True
                key = int(key)
                devices.update(
                    {
                        key:
                            {
                                'id':   key,
                                'name': name,
                                'tab_name': tab_name,
                                'state': state
                            }
                    }
                )

            if not devices:
                raise Exception("未检测到连接的ADB设备")
            else:
                return devices
        except subprocess.CalledProcessError:
            raise Exception("ADB命令执行失败，请检查ADB是否正确安装")

    def _check_and_select_device(self):
        devices = self.get_all_devices_info()

        # 如果用户未指定设备ID，自动选择第一个设备
        if self.device_id is None:
            if len(devices) > 1:
                print(f"检测到多个设备: {devices}")
                print(f"自动选择第一个设备: {devices[0]}")
            self.device_ids = devices[0]
        else:
            if self.device_id not in list(devices.keys()):
                raise Exception(f"指定设备 {self.device_id} 未连接或不可用")

        self.device_name = devices[self.device_id]['name']

        print(f"已选择设备: {self.device_name}")

    def _get_adb_command(self, command, include_device=True):
        """构建ADB命令，自动添加设备ID"""
        if include_device and self.device_id:
            command = self.mmm_path + ['adb', '-v', self.str_device_id, '-c'] + command
            return command
        else:
            command = self.mmm_path + ['adb', '-v', '0', '-c'] + command
            return command

    def tap(self, x, y, random_range: int = 3):
        if random_range >= 0:
            i = random_range
            j = 0 - random_range
        else:
            i = 0 - random_range
            j = random_range
        x = x + random.randint(j, i)
        y = y + random.randint(j, i)
        cmd = self._get_adb_command(['shell', 'input', 'tap', str(x), str(y)])
        subprocess.run(cmd)
        time.sleep(0.1)

    def screenshot(self):
        """获取屏幕截图，返回numpy数组格式的图像"""
        try:
            # 方法1: 尝试使用exec-out命令，这通常能获得更干净的输出
            cmd = self._get_adb_command(['exec-out', 'screencap', '-p'])
            result = subprocess.run(cmd, capture_output=True, timeout=3)

            # 检查命令是否成功执行
            if result.returncode != 0:
                raise Exception(f"screencap命令执行失败，错误码: {result.returncode}")

            # 检查输出是否为空
            if not result.stdout:
                raise Exception("截图输出为空")

            # 检查输出是否以PNG文件头开始（可选）
            if result.stdout[:8] != b'\x89PNG\r\n\x1a\n':
                print("警告: 截图数据可能不是标准PNG格式，尝试修复...")
                # 尝试寻找PNG文件头
                png_header = b'\x89PNG\r\n\x1a\n'
                if png_header in result.stdout:
                    idx = result.stdout.find(png_header)
                    result.stdout = result.stdout[idx:]
                else:
                    # 如果不是PNG，尝试直接处理原始数据
                    return self._screenshot_raw()

            # 尝试使用BytesIO打开图像
            try:
                image = Image.open(io.BytesIO(result.stdout))
                # 确保图像被完全加载
                image.load()
                return np.array(image)
            except Exception as e:
                print(f"PIL打开图像失败，尝试使用原始数据方法: {e}")
                return self._screenshot_raw()

        except subprocess.TimeoutExpired:
            raise Exception("截图命令超时，请检查设备连接")
        except Exception as e:
            print(f"截图失败: {e}")
            # 尝试备用方法
            return self._screenshot_fallback()

    def _screenshot_raw(self):
        """处理原始截图数据的备用方法"""
        try:
            # 使用原始的screencap命令（不带-p参数）
            cmd = self._get_adb_command(['shell', 'screencap'])
            result = subprocess.run(cmd, capture_output=True, timeout=5)

            if result.returncode != 0 or not result.stdout:
                raise Exception("原始截图方法失败")

            # 原始数据可能需要处理行尾符转换
            # Android的screencap输出使用\r\n作为行尾，需要转换为\n
            raw_data = result.stdout.replace(b'\r\n', b'\n')

            # 尝试解析原始数据
            # 原始数据格式通常是: [header][pixel data]
            # 对于某些设备，可能需要更复杂的解析
            return self._parse_raw_screenshot(raw_data)

        except Exception as e:
            print(f"原始截图方法失败: {e}")
            raise Exception("所有截图方法都失败，请检查设备是否支持screencap命令")

    def _parse_raw_screenshot(self, raw_data):
        """解析原始截图数据"""
        try:
            # 尝试寻找常见图像格式的魔术头
            # PNG
            png_header = b'\x89PNG\r\n\x1a\n'
            if raw_data.startswith(png_header):
                image = Image.open(io.BytesIO(raw_data))
                return np.array(image)

            # JPEG
            jpeg_header = b'\xff\xd8\xff'
            if raw_data.startswith(jpeg_header):
                image = Image.open(io.BytesIO(raw_data))
                return np.array(image)

            # 如果以上都不是，尝试作为原始RGB数据解析
            # 这需要知道设备的分辨率
            device_info = self.get_device_info()
            if 'resolution' in device_info:
                # 从分辨率字符串中提取宽高
                res_str = device_info['resolution']
                match = re.search(r'(\d+)x(\d+)', res_str)
                if match:
                    width, height = int(match.group(1)), int(match.group(2))
                    # 假设是RGB888格式（每个像素3字节）
                    expected_size = width * height * 3
                    if len(raw_data) >= expected_size:
                        # 取前expected_size字节作为图像数据
                        img_data = raw_data[:expected_size]
                        # 转换为numpy数组并reshape
                        img_array = np.frombuffer(img_data, dtype=np.uint8)
                        img_array = img_array.reshape((height, width, 3))
                        return img_array

            raise Exception("无法解析截图数据")
        except Exception as e:
            print(f"解析原始截图数据失败: {e}")
            raise

    def _screenshot_fallback(self):
        """使用第三方工具的备用截图方法"""
        try:
            # 方法1: 使用adb截图并保存到设备，然后拉取
            remote_path = '/sdcard/screenshot.png'
            cmd_save = self._get_adb_command(['shell', 'screencap', '-p', remote_path])
            subprocess.run(cmd_save, capture_output=True, timeout=5)

            # 拉取截图
            local_path = 'temp_screenshot.png'
            cmd_pull = self._get_adb_command(['pull', remote_path, local_path])
            result = subprocess.run(cmd_pull, capture_output=True, timeout=5)

            if result.returncode == 0:
                # 读取本地文件
                image = Image.open(local_path)
                img_array = np.array(image)

                # 清理临时文件
                import os
                if os.path.exists(local_path):
                    os.remove(local_path)

                return img_array
            else:
                raise Exception("备用截图方法失败")

        except Exception as e:
            print(f"备用截图方法失败: {e}")
            raise Exception("所有截图方法都失败")

    def get_current_app(self):
        """获取当前前台应用的包名"""
        try:
            # 使用更可靠的方法获取当前应用
            cmd = self._get_adb_command(['shell', 'dumpsys', 'window', 'windows'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            # 查找当前焦点窗口
            for line in result.stdout.split('\n'):
                if 'mCurrentFocus' in line or 'mFocusedApp' in line:
                    # 提取包名
                    patterns = [
                        r'([a-zA-Z0-9_\.]+)/[a-zA-Z0-9_\.]+',
                        r'package=([a-zA-Z0-9_\.]+)',
                        r'([a-zA-Z0-9_\.]+)\.[a-zA-Z0-9_\.]+'
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, line)
                        if match:
                            package_name = match.group(1)
                            return package_name

            # 备选方法
            cmd = self._get_adb_command(['shell', 'dumpsys', 'activity', 'activities'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            for line in result.stdout.split('\n'):
                if 'ResumedActivity' in line:
                    pattern = r'([a-zA-Z0-9_\.]+)/[a-zA-Z0-9_\.]+'
                    match = re.search(pattern, line)
                    if match:
                        package_name = match.group(1)
                        return package_name

            return None

        except Exception as e:
            print(f"获取当前应用失败: {e}")
            return None

    def is_app_foreground(self, package_name):
        """检查指定应用是否在前台"""
        current_app = self.get_current_app()
        return current_app == package_name if current_app else False

    def launch_app(self, package_name):
        """启动指定应用"""
        cmd = self._get_adb_command(
            ['shell', 'monkey', '-p', package_name, '-c', 'android.intent.category.LAUNCHER', '1'])
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"已启动应用: {package_name}")
        else:
            print(f"启动应用失败: {result.stderr}")

    def force_stop_app(self, package_name):
        """强制停止应用"""
        cmd = self._get_adb_command(['shell', 'am', 'force-stop', package_name])
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"已强制停止应用: {package_name}")
        else:
            print(f"停止应用失败: {result.stderr}")

    def swipe(self, start_x, start_y, end_x, end_y, duration=500):
        """执行滑动操作"""
        cmd = self._get_adb_command(['shell', 'input', 'swipe',
                                     str(start_x), str(start_y),
                                     str(end_x), str(end_y),
                                     str(duration)])
        subprocess.run(cmd)

        # 滑动后等待0.1秒
        time.sleep(0.1)

    def long_press(self, x, y, duration=1000):
        """执行长按操作"""
        cmd = self._get_adb_command(['shell', 'input', 'swipe',
                                     str(x), str(y), str(x), str(y),
                                     str(duration)])
        subprocess.run(cmd)

    def get_device_info(self):
        """获取设备信息"""
        info = {'device_id': self.device_id}
        try:
            # 获取设备型号
            cmd = self._get_adb_command(['shell', 'getprop', 'ro.product.model'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            info['model'] = result.stdout.strip() if result.returncode == 0 else '未知'

            # 获取Android版本
            cmd = self._get_adb_command(['shell', 'getprop', 'ro.build.version.release'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            info['android_version'] = result.stdout.strip() if result.returncode == 0 else '未知'

            # 获取设备分辨率
            cmd = self._get_adb_command(['shell', 'wm', 'size'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            info['resolution'] = result.stdout.strip() if result.returncode == 0 else '未知'

            return info
        except Exception as e:
            print(f"获取设备信息失败: {e}")
            return info

    def input_text(self, text):
        """输入文本"""
        # 先确保输入法可用
        cmd = self._get_adb_command(['shell', 'input', 'text', text])
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def press_key(self, keycode):
        """按下按键"""
        cmd = self._get_adb_command(['shell', 'input', 'keyevent', str(keycode)])
        subprocess.run(cmd)

    def back(self):
        """返回键"""
        cmd = self._get_adb_command(['go_back'])
        subprocess.run(cmd, capture_output=True, text=True, timeout=3)

    def home(self):
        """主页键"""
        self.press_key(3)

    def recent_apps(self):
        """最近应用键"""
        self.press_key(187)


class MumuGameAutomator:
    """Mumu模拟器游戏自动化控制器"""

    def __init__(self, mumu_device: int = 0, game_package: str = None,
                 mmm_path: str = r'C:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe',
                 ocr_lang: str = 'eng+chi_sim'):
        """
        初始化Mumu游戏自动化控制器

        Args:
            mumu_device: Mumu模拟器序号
            game_package: 游戏包名
        """
        self.mmm_path = mmm_path
        self.mumu_device = mumu_device
        self.game_package = game_package
        self.adb = None
        self.image_matcher = ImageMatcher()
        self.screen_width = 0
        self.screen_height = 0
        self._connect_mumu()

        self.ocr = OCRProcessor(lang=ocr_lang)
        self.ocr_type = 'tesseract'

    def _connect_mumu(self):
        """连接Mumu模拟器"""
        try:
            # 连接Mumu模拟器
            self.adb = ADBController(device_id=self.mumu_device, mmm_path=self.mmm_path)
        except subprocess.CalledProcessError:
            raise Exception("ADB命令执行失败，请检查ADB是否正确安装")

    def _update_screen_info(self):
        """更新屏幕信息"""
        try:
            info = self.adb.get_device_info()
            if 'resolution' in info:
                res_str = info['resolution']
                match = re.search(r'(\d+)x(\d+)', res_str)
                if match:
                    self.screen_width = int(match.group(1))
                    self.screen_height = int(match.group(2))
                    print(f"屏幕分辨率: {self.screen_width}x{self.screen_height}")
        except Exception as e:
            print(f"获取屏幕信息失败: {e}")

    def get_screen_text(self, region: Tuple[int, int, int, int] = None,
                        numbers: bool = False, preprocess: bool = True, with_qwen3: bool = True) -> str:

        value = None
        i = 0
        # return self.ocr.extract_text(screenshot, preprocess=preprocess, region=region)
        if numbers:
            while not value:
                screenshot = self.adb.screenshot()
                value = self.ocr.extract_numbers(screenshot, preprocess=preprocess,
                                                 region=region, with_qwen3=with_qwen3)
                i = i + 1
                if i > 5:
                    break
        else:
            while not value:
                screenshot = self.adb.screenshot()
                value = self.ocr.extract_text(screenshot, preprocess=preprocess, region=region, with_qwen3=with_qwen3)
                i = i + 1
                if i > 5:
                    break

        return value

    def start_game(self):
        """启动游戏"""
        if not self.game_package:
            print("未指定游戏包名")
            return False

        if self.adb.is_app_foreground(self.game_package):
            print("游戏已经在前台运行")
            return True

        print(f"正在启动游戏: {self.game_package}")
        self.adb.launch_app(self.game_package)
        time.sleep(5)  # 等待游戏启动

        # 检查是否启动成功
        for _ in range(10):
            if self.adb.is_app_foreground(self.game_package):
                print("游戏启动成功")
                return True
            time.sleep(2)

        print("游戏启动失败")
        return False

    def stop_game(self):
        """停止游戏"""
        if not self.game_package:
            return False

        self.adb.force_stop_app(self.game_package)
        print(f"已停止游戏: {self.game_package}")
        return True

    def restart_game(self):
        """重启游戏"""
        self.stop_game()
        time.sleep(2)
        return self.start_game()

    def get_image_pos(self, template_path: str, timeout: int = 3,
                      threshold: float = 0.8, offset_x: int = 0, offset_y: int = 0):
        # print(f"等待图像: {template_path}")
        start_time = time.time()
        template = self.image_matcher.load_template(template_path)

        while time.time() - start_time - 0.1 < timeout:

            time.sleep(1)
            screenshot = self.adb.screenshot()
            position = self.image_matcher.find_template(screenshot, template, threshold)

            if position:
                x, y = position
                x += offset_x
                y += offset_y

                return x, y

        # print(f"超时: 未找到图像 {template_path}")
        return False

    def multiple_images_pos(self, paths: dict = None, timeout: int = 0, threshold: float = 0.8):
        # print(f"等待图像: {template_path}")
        start_time = time.time()
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

        while time.time() - start_time - 0.1 < timeout:
            time.sleep(1)

        screenshot = self.adb.screenshot()
        template_keys = list(templates.keys())
        template_values = list(templates.values())
        with ThreadPoolExecutor(max_workers=9) as executor:
            result = list(executor.map(
                lambda template: self.image_matcher.find_template(screenshot, template, threshold),
                template_values
            ))
        if result:
            result = dict(zip(template_keys, result))
            return result

        # print(f"超时: 未找到图像 {template_path}")
        return False

    # 同时查找一个图片的多个位置
    def get_images_pos(self, template_path: str, timeout: int = 10,
                       threshold: float = 0.8, position_threshold: int = 8):
        # print(f"等待图像: {template_path}")
        start_time = time.time()
        template = self.image_matcher.load_template(template_path)

        while time.time() - start_time - 0.1 < timeout:
            screenshot = self.adb.screenshot()
            positions = self.image_matcher.find_all_templates(screenshot, template, threshold)

            if positions:
                positions = find_distinct_points(positions, threshold=position_threshold)
                return positions

            time.sleep(1)

        # print(f"超时: 未找到图像 {template_path}")
        return []

    def wait_and_click(self, template_path: str, timeout: int = 3,
                       hold: bool = False, hold_time: int = 3,
                       threshold: float = 0.8, offset_x: int = 0, offset_y: int = 0) -> bool:
        """
        等待并点击指定图像

        Args:
            template_path: 模板图像路径
            timeout: 超时时间(秒)
            threshold: 匹配阈值
            offset_x: X轴偏移
            offset_y: Y轴偏移
            hold: 启用长按
            hold_time: 按住时间，秒
        """
        position = self.get_image_pos(template_path=template_path, timeout=timeout,
                                      threshold=threshold, offset_x=offset_x, offset_y=offset_y)

        if position:
            x, y = position
            if hold:
                x1 = x + 1
                y1 = y + 1
                # print(f"找到图像位置: ({x}, {y}), 长按")
                self.adb.swipe(x, y, x1, y1, hold_time * 1000)
            else:

                # print(f"找到图像位置: ({x}, {y})， 点击")
                self.adb.tap(x, y)
            return True
        else:
            return False

    def click_if_exists(self, template_path: str, threshold: float = 0.8,
                        offset_x: int = 0, offset_y: int = 0) -> bool:
        """
        如果图像存在则点击

        Returns:
            是否找到并点击了图像
        """
        position = self.get_image_pos(template_path=template_path, threshold=threshold,
                                      offset_x=offset_x, offset_y=offset_y, timeout=1)

        if position:
            x, y = position
            x += offset_x
            y += offset_y
            # print(f"点击图像: {template_path} 位置: ({x}, {y})")
            self.adb.tap(x, y)
            return True
        else:
            return False

    def wait_for_image(self, template_path: str, timeout: int = 30,
                       threshold: float = 0.8) -> bool:
        position = self.get_image_pos(template_path=template_path, threshold=threshold,
                                      timeout=timeout)
        if position:
            return True
        else:
            return False

    def tap_random_area(self, x1: int, y1: int, x2: int, y2: int):
        """
        在指定区域内随机点击

        Args:
            x1, y1: 区域左上角坐标
            x2, y2: 区域右下角坐标
        """
        x = random.randint(x1, x2)
        y = random.randint(y1, y2)
        # print(f"随机点击: ({x}, {y})")
        self.adb.tap(x, y)

    def swipe_random(self, start_x1: int, start_y1: int, start_x2: int, start_y2: int,
                     end_x1: int, end_y1: int, end_x2: int, end_y2: int,
                     duration: int = 500):

        start_x = random.randint(start_x1, start_x2)
        start_y = random.randint(start_y1, start_y2)
        end_x = random.randint(end_x1, end_x2)
        end_y = random.randint(end_y1, end_y2)

        # print(f"滑动: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
        self.adb.swipe(start_x, start_y, end_x, end_y, duration)

    def save_current_screen(self, filename: str = None):
        """保存当前屏幕截图"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        screenshot = self.adb.screenshot()
        self.image_matcher.save_screenshot(screenshot, filename)
        print(f"截图已保存: {filename}")
        return filename

    def check_game_state(self, state_templates: Dict[str, str],
                         threshold: float = 0.8) -> Optional[str]:
        """
        检查游戏当前状态

        Args:
            state_templates: 状态名到模板路径的映射
            threshold: 匹配阈值

        Returns:
            状态名或None
        """
        screenshot = self.adb.screenshot()

        for state_name, template_path in state_templates.items():
            template = self.image_matcher.load_template(template_path)
            position = self.image_matcher.find_template(screenshot, template, threshold)

            if position:
                return state_name

        return None

    # TaskManager要调用的参数
    def is_ready(self):
        return self.adb.is_app_foreground('com.gof.china')

    def get_status(self):
        if self.is_ready():
            return {'is_running': True}

    def execute_sequence(self, sequence: List[Dict[str, Any]]):
        """
        执行自动化序列

        Args:
            sequence: 动作序列，每个动作是一个字典
                支持的动作类型:
                - tap: 点击
                - wait_and_click: 等待并点击
                - swipe: 滑动
                - wait: 等待
                - screenshot: 截图
                - back: 返回
                - home: 主页
        """
        for i, action in enumerate(sequence):
            action_type = action.get('type', '')
            print(f"执行动作 {i + 1}/{len(sequence)}: {action_type}")

            try:
                if action_type == 'tap':
                    self.adb.tap(action['x'], action['y'])

                elif action_type == 'wait_and_click':
                    self.wait_and_click(action['template'], timeout=action.get('timeout', 30),
                                        threshold=action.get('threshold', 0.8), offset_x=action.get('offset_x', 0),
                                        offset_y=action.get('offset_y', 0))

                elif action_type == 'swipe':
                    self.adb.swipe(
                        action['start_x'], action['start_y'],
                        action['end_x'], action['end_y'],
                        action.get('duration', 500)
                    )

                elif action_type == 'wait':
                    time.sleep(action.get('duration', 1))

                elif action_type == 'screenshot':
                    self.save_current_screen(action.get('filename'))

                elif action_type == 'back':
                    self.adb.back()

                elif action_type == 'home':
                    self.adb.home()

                elif action_type == 'random_tap':
                    self.tap_random_area(
                        action['x1'], action['y1'],
                        action['x2'], action['y2']
                    )

                elif action_type == 'random_swipe':
                    self.swipe_random(
                        action['start_x1'], action['start_y1'],
                        action['start_x2'], action['start_y2'],
                        action['end_x1'], action['end_y1'],
                        action['end_x2'], action['end_y2'],
                        action.get('duration', 500)
                    )

                # 等待动作间隔
                time.sleep(action.get('interval', 1))

            except Exception as e:
                print(f"执行动作失败: {e}")
                if action.get('continue_on_error', False):
                    continue
                else:
                    break
