import os
import json
import time
import functools


def load_json_config(config_path):
    """加载JSON配置文件"""
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件 {config_path} 失败: {e}")
            return {}
    else:
        print(f"配置文件 {config_path} 不存在")
        return {}


def get_english_name(chinese_name):
    """
    根据中文名获取首字母大写的英文名
    参数:
        chinese_name (str): 英雄的中文名
    返回:
        str: 对应的首字母大写的英文名，如果未找到则返回None
    """
    return CHINESE_TO_ENGLISH_MAP.get(chinese_name)


def get_chinese_name(english_name):
    """
    根据英文名获取中文名
    参数:
        english_name (str): 英雄的英文名
    返回:
        str: 对应的中文名，如果未找到则返回None
    """
    return ENGLISH_TO_CHINESE_MAP.get(english_name)


def get_heroes_by_type(hero_type):
    """
    根据类型获取该类型的所有英雄
    参数:
        type_ (str): 英雄类型，如 'infantry', 'cavalry', 'archer'
    返回:
        list: 该类型所有英雄的中文名列表
    """
    return HEROES_BY_TYPE.get(hero_type, [])


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


def get_tasklist_function(func_name):
    """获取TaskList类中的函数并创建一个包装函数"""

    # 获取TaskList类中对应的方法
    # 由于任务管理器会使用这些函数，我们需要创建一个能访问TaskList实例的包装函数
    def wrapper(winterless_instance):
        # winterless_instance 实际上是TaskList实例
        method = getattr(winterless_instance, func_name, None)
        if method:
            return method()
        else:
            print(f"Warning: Method {func_name} not found in TaskList object")
            return None

    return wrapper


HEROES_DATA = load_json_config('heroes_data.json')
CHINESE_TO_ENGLISH_MAP = {hero["chinese_name"]: hero["english_name"] for hero in HEROES_DATA}
ENGLISH_TO_CHINESE_MAP = {hero["english_name"]: hero["chinese_name"] for hero in HEROES_DATA}
HEROES_BY_TYPE = {}
for hero in HEROES_DATA:
    type_ = hero["hero_type"]
    if type_ not in HEROES_BY_TYPE:
        HEROES_BY_TYPE[type_] = []
    HEROES_BY_TYPE[type_].append(hero["chinese_name"])