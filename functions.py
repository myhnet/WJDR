import os
import json
import time
import functools


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
