import numpy as np
import cv2
import re
import base64
import requests
from PIL import Image
from io import BytesIO


from typing import Tuple, List, Dict, Optional, Union

try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("警告: pytesseract 未安装，OCR功能将不可用")


class OCRProcessor:
    """OCR处理器类"""

    def __init__(self, lang: str = 'eng+chi_sim', config: str = ''):
        """
        初始化OCR处理器

        Args:
            lang: 语言代码，如 'eng' (英文), 'chi_sim' (简体中文), 'eng+chi_sim' (中英混合)
            config: Tesseract配置参数
        """
        self.lang = lang
        self.config = config
        self.available = TESSERACT_AVAILABLE

        if not self.available:
            print("警告: Tesseract OCR不可用，请安装: pip install pytesseract")
            print("同时需要安装Tesseract引擎: https://github.com/UB-Mannheim/tesseract/wiki")

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        预处理图像以提高OCR识别率

        Args:
            image: 输入图像(numpy数组)

        Returns:
            预处理后的图像
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 应用多种预处理技术
        # processed = gray.copy()
        processed = cv2.GaussianBlur(gray, (5, 5), 0)

        # 1. 自适应二值化
        processed = cv2.adaptiveThreshold(
            processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # 2. 去噪
        # processed = cv2.medianBlur(processed, 3)

        # 3. 形态学操作（可选）
        kernel = np.ones((3, 3), np.uint8)
        processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)

        return processed

    def extract_text(self, image: np.ndarray,
                     preprocess: bool = True,
                     region: Tuple[int, int, int, int] = None, with_qwen3: bool = True) -> str:
        """
        从图像中提取文本

        Args:
            image: 输入图像
            preprocess: 是否进行预处理
            region: 区域(x1, y1, x2, y2)，如果为None则处理整张图片
            with_qwen3: 是否使用Qwen3模型

        Returns:
            识别的文本
        """
        if not self.available:
            return ""

        try:
            # 如果指定了区域，裁剪图像
            if region is not None:
                x1, y1, x2, y2 = region
                image = image[y1:y2, x1:x2]

            if with_qwen3:
                image_data = Image.fromarray(image)
                buff = BytesIO()
                image_data.save(buff, format='PNG')
                image_data2 = buff.getvalue()

                # Encode the image as base64
                image_base64 = base64.b64encode(image_data2).decode('utf-8')
                result = self.extract_text_qwen3(image_base64)
                return result

            # 预处理图像
            if preprocess:
                image = self.preprocess_image(image)
            else:
                if len(image.shape) == 3:
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

            # 将numpy数组转换为PIL图像
            pil_image = Image.fromarray(image)

            # 使用Tesseract进行OCR
            text = pytesseract.image_to_string(
                pil_image,
                lang=self.lang,
                config=self.config
            )

            return text.strip()

        except Exception as e:
            print(f"OCR识别失败: {e}")
            return ""

    @staticmethod
    def extract_text_qwen3(image_base64) -> str:
        prompt = """请详细描述这张图片中的文字内容。
        要求：
        1. 列出所有可见文字
        2. 保持原顺序
        3. 不要解释、不要推理、不要思考
        4. 文字之间用换行分隔
        
        请以清晰、有条理的方式输出，直接描述文字内容。"""

        payload = {
            "model": "qwen3-vl",
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            # "options": {
            #    "temperature": 0.2,  # 降低随机性，更确定性
            #    "num_predict": 5000,
            #    "stop": ["<|im_end|>", "<|endoftext|>"]
            # }
        }

        # Make the API request
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload
        )

        # Parse the response
        if response.status_code == 200:
            result = response.json()
            # print(result)
            return result['response']
        else:
            return ''

    def extract_text_with_confidence(self, image: np.ndarray,
                                     preprocess: bool = True,
                                     region: Tuple[int, int, int, int] = None) -> List[Dict]:
        """
        提取文本并返回置信度信息

        Returns:
            列表，每个元素为{'text': 文本, 'confidence': 置信度, 'bbox': 边界框}
        """
        if not self.available:
            return []

        try:
            # 如果指定了区域，裁剪图像
            if region is not None:
                x1, y1, x2, y2 = region
                image = image[y1:y2, x1:x2]

            # 预处理图像
            if preprocess:
                image = self.preprocess_image(image)
            else:
                if len(image.shape) == 3:
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

            # 将numpy数组转换为PIL图像
            pil_image = Image.fromarray(image)

            # 获取详细的OCR数据
            data = pytesseract.image_to_data(
                pil_image,
                lang=self.lang,
                config=self.config,
                output_type=pytesseract.Output.DICT
            )

            results = []
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])

                if text and conf > 0:  # 过滤空文本和低置信度
                    results.append({
                        'text': text,
                        'confidence': conf,
                        'bbox': (
                            data['left'][i],
                            data['top'][i],
                            data['left'][i] + data['width'][i],
                            data['top'][i] + data['height'][i]
                        )
                    })

            return results

        except Exception as e:
            print(f"详细OCR识别失败: {e}")
            return []

    def find_text_position(self, image: np.ndarray, target_text: str,
                           preprocess: bool = True,
                           threshold: float = 60.0,
                           region: Tuple[int, int, int, int] = None) -> Optional[Tuple[int, int]]:
        """
        查找指定文本在图像中的位置

        Args:
            image: 输入图像
            target_text: 要查找的文本
            preprocess: 是否预处理
            threshold: 置信度阈值
            region: 搜索区域

        Returns:
            文本中心坐标(x, y)，如果未找到则返回None
        """
        results = self.extract_text_with_confidence(
            image, preprocess=preprocess, region=region
        )

        target_text_lower = target_text.lower()

        for result in results:
            # 检查文本是否包含目标文本（不区分大小写）
            if target_text_lower in result['text'].lower() and result['confidence'] >= threshold:
                bbox = result['bbox']
                center_x = (bbox[0] + bbox[2]) // 2
                center_y = (bbox[1] + bbox[3]) // 2

                # 如果指定了区域，调整坐标
                if region is not None:
                    center_x += region[0]
                    center_y += region[1]

                return (center_x, center_y)

        return None

    def extract_numbers(self, image: np.ndarray, preprocess: bool = True,
                        region: Tuple[int, int, int, int] = None, with_qwen3=False) -> List[Union[int, float]]:
        """
        从图像中提取数字

        Returns:
            提取到的数字列表
        """
        text = self.extract_text(image, preprocess=preprocess, region=region, with_qwen3=with_qwen3)

        # 使用正则表达式提取所有数字
        numbers = []
        for match in re.finditer(r'[-+]?\d*\.?\d+', text):
            try:
                num = float(match.group())
                if num.is_integer():
                    numbers.append(int(num))
                else:
                    numbers.append(num)
            except ValueError:
                continue

        return numbers

    def save_ocr_debug_image(self, image: np.ndarray,
                             output_path: str = "ocr_debug.png",
                             region: Tuple[int, int, int, int] = None,
                             draw_boxes: bool = True):
        """
        保存OCR调试图像，显示识别到的文本区域

        Args:
            image: 原始图像
            output_path: 输出路径
            region: 感兴趣区域
            draw_boxes: 是否绘制边界框
        """
        if region is not None:
            x1, y1, x2, y2 = region
            roi = image[y1:y2, x1:x2].copy()
        else:
            roi = image.copy()
            x1, y1 = 0, 0

        debug_image = roi.copy()

        if draw_boxes:
            results = self.extract_text_with_confidence(roi, preprocess=False)

            for result in results:
                bbox = result['bbox']
                text = result['text']
                conf = result['confidence']

                # 绘制边界框
                cv2.rectangle(debug_image,
                              (bbox[0], bbox[1]),
                              (bbox[2], bbox[3]),
                              (0, 255, 0), 2)

                # 添加文本标签
                label = f"{text} ({conf}%)"
                cv2.putText(debug_image, label,
                            (bbox[0], bbox[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (0, 0, 255), 2)

        # 保存图像
        Image.fromarray(debug_image).save(output_path)
        print(f"OCR调试图像已保存: {output_path}")
