from datetime import datetime, timedelta, time as dt_time

from typing import Callable, Dict, Any, Optional, List, Union


class Test:
    def __init__(self):
        self.task_definitions = {
            # 网络功能组
            "野外": {
                "采集": {
                    "interval_seconds": 590,  # 10分钟
                    "requires_game": True
                },
                "自动上车": {
                    "interval_seconds": 30,  # 5分钟
                    "requires_game": True
                },
                "自动打巨兽": {
                    "cron_expression": "50 */2 * * *",
                    "immediate": True,
                    "requires_game": True
                }
            }
        }

    def execute(self):
        task_config = self.task_definitions['野外']['自动打巨兽']
        immediate = task_config.get("immediate", False)
        print(immediate)



myTest = Test()
myTest.execute()