import json
import re
import base64
import requests
from io import BytesIO
from PIL import Image
from typing import Dict, Any


def recognize_text_in_image(image_path: str, api_key: str) -> Dict[str, Any]:
    # Read the image file
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()

    # Prepare the request to Qwen API
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # Encode the image as base64
    import base64
    image_base64 = base64.b64encode(image_data).decode('utf-8')

    # Prepare the payload for vision model
    '''payload = {
        "model": "qwen3-vl",  # or qwen-vl-plus depending on your needs
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": "Please recognize and extract all text from this image. Return the results in JSON format."
                    }
                ]
            }
        ]
    }'''

    prompt = """请提取图片中的所有文字内容，只输出识别到的文字。

    要求：
    1. 列出所有可见文字
    2. 保持原顺序
    3. 不要解释、不要推理、不要思考
    4. 文字之间用换行分隔"""

    payload = {
        "model": "qwen3-vl",
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": 0.1,  # 降低随机性，更确定性
            "num_predict": 1000  # 停止词
        }
    }

    # Make the API request
    response = requests.post(
        # "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "http://localhost:11434/api/generate",
        headers=headers,
        json=payload
    )

    # Parse the response
    if response.status_code == 200:
        result = response.json()
        return result['response']
    else:
        return


def format_arena(text: str):
    # 清理文本
    text = text.strip("' ,")

    # 定义各部分的正则表达式模式
    header_pattern = r'^(挑战列表)\n我的实力：\s*([\d,]+)'

    # 玩家信息模式（捕获组：前缀、中文名、战斗力、得分、排行）
    player_pattern = r'(\[[^\]]+\])([^\n]+)\n([\d,\.]+万?)\n([\d,]+)\n#\s*(\d+)'

    # 结束部分模式
    footer_pattern = r'今日剩余挑战次数：\s*(\d+)\n([^\n]+)$'

    # 匹配表头
    header_match = re.search(header_pattern, text)

    # 匹配所有玩家
    player_matches = re.findall(player_pattern, text, re.MULTILINE)

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
        prefix, chinese_name, combat_power, score, rank = match

        # 计算战斗力的数值
        power_num = combat_power.replace(',', '')
        if '万' in power_num:
            power_num = float(power_num.replace('万', '')) * 10000
        else:
            power_num = float(power_num)

        player_data = {
            "full_name": f"{prefix}{chinese_name}",
            "prefix": prefix,
            "chinese_name": chinese_name,
            "combat_power": combat_power,
            "combat_power_numeric": power_num,
            "score": score,
            "score_numeric": int(score.replace(',', '')),
            "rank": f"#{rank}",
            "rank_numeric": int(rank)
        }
        players.append(player_data)

    result['players'] = players
    # 填充结束部分
    if footer_match:
        result["remaining_challenges"] = int(footer_match.group(1))
        result["refresh_button"] = footer_match.group(2)

    return result


def extra_text_qwen3(image):
    # Read the image file
    image_data = Image.fromarray(image)
    buff = BytesIO()
    image_data.save(buff, format='PNG')
    image_data2 = buff.getvalue()

    # Encode the image as base64
    image_base64 = base64.b64encode(image_data2).decode('utf-8')

    prompt = """请提取图片中的所有文字内容，只输出识别到的文字。

    要求：
    1. 列出所有可见文字
    2. 保持原顺序
    3. 不要解释、不要推理、不要思考
    4. 文字之间用换行分隔"""

    payload = {
        "model": "qwen3-vl",
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": 0.1,  # 降低随机性，更确定性
            "num_predict": 1000  # 停止词
        }
    }
    result = ''
    for _ in range(3):
        # Make the API request
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload
        )

        # Parse the response
        if response.status_code == 200:
            result = response.json()
            result = result['response']
            if result != '':
                break

    return result



def main():
    # Your API key
    API_KEY = "sk-2efd1805497a4ac3a3e5c5470e2ab676"

    # Path to your image
    IMAGE_PATH = "./tests/101.png"

    try:
        # Call the function to recognize text
        result = recognize_text_in_image(IMAGE_PATH, API_KEY)

        # Output the result in JSON format
        # print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()