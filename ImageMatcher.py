import numpy as np
import cv2

from PIL import Image
from typing import Optional, Tuple, List


class ImageMatcher:
    """图像匹配工具类"""

    @staticmethod
    def find_template(screenshot: np.ndarray, template: np.ndarray,
                      threshold: float = 0.8, color_threshold: float = 0.8) -> Optional[Tuple[int, int]]:
        """
        在屏幕截图中查找模板图像

        Args:
            screenshot: 屏幕截图(numpy数组)
            template: 模板图像(numpy数组)
            threshold: 匹配阈值(0-1之间)
            color_threshold: 匹配阈值(0-1之间)

        Returns:
            匹配位置的坐标(x, y)或None
        """
        # 转换为灰度图
        if len(screenshot.shape) == 3:
            screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
        else:
            screenshot_gray = screenshot

        if len(template.shape) == 3:
            template_gray = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
        else:
            template_gray = template

        # 模板匹配
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            # 返回中心点坐标
            h, w = template_gray.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return center_x, center_y

        return None

    @staticmethod
    def find_all_templates(screenshot: np.ndarray, template: np.ndarray,
                           threshold: float = 0.8) -> List[Tuple[int, int]]:
        """
        在屏幕截图中查找所有匹配的模板图像

        Returns:
            匹配位置列表[(x1, y1), (x2, y2), ...]
        """
        if len(screenshot.shape) == 3:
            screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
        else:
            screenshot_gray = screenshot

        if len(template.shape) == 3:
            template_gray = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
        else:
            template_gray = template

        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)

        matches = []
        h, w = template_gray.shape[:2]

        # 对匹配结果进行非极大值抑制
        for pt in zip(*locations[::-1]):
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2
            matches.append((center_x, center_y))

        return matches

    @staticmethod
    def save_screenshot(screenshot: np.ndarray, filename: str):
        """保存截图"""
        Image.fromarray(screenshot).save(filename)

    @staticmethod
    def load_template(filename: str) -> np.ndarray:
        """加载模板图像"""
        return np.array(Image.open(filename))
