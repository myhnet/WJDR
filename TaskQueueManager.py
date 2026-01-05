# task_manager.py - 修复版任务队列管理器，添加定时功能
import heapq
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time as dt_time
from enum import Enum
from typing import Callable, Dict, Any, Optional, List, Union

# 导入您的MumuGameAutomator类
from MumuManager import MumuGameAutomator
from TaskList import WinterLess


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    WAITING = "waiting"
    PAUSED = "paused"


class ScheduleType(Enum):
    """调度类型"""
    INTERVAL = "interval"  # 间隔执行
    DAILY = "daily"  # 每日固定时间
    WEEKLY = "weekly"  # 每周固定时间
    CRON = "cron"  # Cron表达式


# noinspection PyBroadException
@dataclass(order=True)
class Task:
    """任务定义"""
    # 必须参数（无默认值）
    scheduled_time: datetime  # 排序字段
    task_id: str = field(compare=False)
    name: str = field(compare=False)
    func: Callable = field(compare=False)

    # 可选参数（有默认值）
    schedule_type: ScheduleType = field(default=ScheduleType.INTERVAL, compare=False)
    interval_seconds: float = field(default=0, compare=False)  # 间隔任务参数
    fixed_time: Optional[dt_time] = field(default=None, compare=False)  # 每日固定时间
    weekdays: Optional[List[int]] = field(default=None, compare=False)  # 0-6, 0=周一
    cron_expression: Optional[str] = field(default=None, compare=False)  # cron表达式

    # 状态和统计参数
    last_run_time: Optional[datetime] = field(default=None, compare=False)
    last_result: Any = field(default=None, compare=False)
    max_retries: int = field(default=3, compare=False)
    retry_count: int = field(default=0, compare=False)
    requires_game: bool = field(default=True, compare=False)
    priority: int = field(default=5, compare=False)  # 1-10, 1最高
    enabled: bool = field(default=True, compare=False)
    data: Dict[str, Any] = field(default_factory=dict, compare=False)
    execution_count: int = field(default=0, compare=False)
    total_execution_time: float = field(default=0, compare=False)
    average_execution_time: float = field(default=0, compare=False)

    @property
    def is_long_interval(self) -> bool:
        """判断是否为长间隔任务"""
        if self.schedule_type == ScheduleType.INTERVAL:
            return self.interval_seconds > 15
        return True  # 定时任务默认视为长间隔

    @property
    def next_run_str(self) -> str:
        """下次运行时间字符串"""
        if self.scheduled_time:
            return self.scheduled_time.strftime("%Y-%m-%d %H:%M:%S")
        return "N/A"

    @property
    def schedule_description(self) -> str:
        """调度描述"""
        if self.schedule_type == ScheduleType.INTERVAL:
            return f"每 {self.interval_seconds} 秒执行"
        elif self.schedule_type == ScheduleType.DAILY and self.fixed_time:
            return f"每日 {self.fixed_time.strftime('%H:%M')} 执行"
        elif self.schedule_type == ScheduleType.WEEKLY and self.fixed_time and self.weekdays:
            weekdays_str = ",".join(["一", "二", "三", "四", "五", "六", "日"][d] for d in self.weekdays)
            return f"每周{weekdays_str} {self.fixed_time.strftime('%H:%M')} 执行"
        elif self.schedule_type == ScheduleType.CRON and self.cron_expression:
            return f"Cron: {self.cron_expression}"
        return "未知调度"

    def calculate_next_run(self) -> datetime:
        """计算下次运行时间"""
        now = datetime.now()

        if self.schedule_type == ScheduleType.INTERVAL:
            return now + timedelta(seconds=self.interval_seconds)

        elif self.schedule_type == ScheduleType.DAILY and self.fixed_time:
            # 每日固定时间
            next_run = datetime.combine(now.date(), self.fixed_time)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run

        elif self.schedule_type == ScheduleType.WEEKLY and self.fixed_time and self.weekdays:
            # 每周固定时间
            # today_weekday = now.weekday()  # 0=周一, 6=周日

            # 查找下一个符合条件的日期
            for days_ahead in range(0, 8):  # 包括今天，最多看7天
                next_date = now.date() + timedelta(days=days_ahead)
                next_weekday = next_date.weekday()

                if next_weekday in self.weekdays:
                    next_run = datetime.combine(next_date, self.fixed_time)
                    # 如果今天的固定时间还没过，且今天是符合条件的星期
                    if days_ahead == 0 and now.time() < self.fixed_time:
                        return next_run
                    elif days_ahead > 0:
                        return next_run

        elif self.schedule_type == ScheduleType.CRON and self.cron_expression:
            # 简化版cron解析（支持分钟、小时、日、月、星期）
            try:
                return self._parse_cron_expression()
            except Exception:
                # 解析失败，使用默认间隔
                return now + timedelta(seconds=3600)  # 1小时

        # 默认：1小时后
        return now + timedelta(seconds=3600)

    def _parse_cron_expression(self) -> datetime:
        """解析cron表达式"""
        now = datetime.now()
        parts = self.cron_expression.strip().split()

        if len(parts) != 5:
            raise ValueError(f"无效的cron表达式: {self.cron_expression}")

        minute, hour, day, month, weekday = parts

        def parse_field(field: str, min_val: int, max_val: int) -> List[int]:
            """解析cron字段"""
            if field == "*":
                return list(range(min_val, max_val + 1))

            result = []
            for part in field.split(","):
                if "/" in part:
                    # 步长 */5
                    step_part = part.split("/")
                    step = int(step_part[1])
                    result.extend(range(min_val, max_val + 1, step))
                elif "-" in part:
                    # 范围 1-5
                    start, end = map(int, part.split("-"))
                    result.extend(range(start, end + 1))
                else:
                    result.append(int(part))

            return [v for v in result if min_val <= v <= max_val]

        # 解析各个字段
        minutes = parse_field(minute, 0, 59)
        hours = parse_field(hour, 0, 23)
        days = parse_field(day, 1, 31)
        months = parse_field(month, 1, 12)
        weekdays = parse_field(weekday, 0, 6)  # 0=周日, 6=周六

        # 查找下一个匹配的时间
        for delta_days in range(0, 366):  # 最多看一年
            check_date = now.date() + timedelta(days=delta_days)

            # 检查月份
            if check_date.month not in months:
                continue

            # 检查日期
            if check_date.day not in days:
                continue

            # 检查星期
            if (check_date.weekday() + 1) % 7 not in weekdays:  # 转换为cron星期格式
                continue

            # 查找匹配的小时和分钟
            for h in sorted(hours):
                for m in sorted(minutes):
                    candidate = datetime.combine(check_date, dt_time(hour=h, minute=m))
                    if candidate > now:
                        return candidate

        # 如果没有找到，返回一年后
        return now + timedelta(days=365)

    def schedule_next(self) -> None:
        """安排下次执行"""
        self.scheduled_time = self.calculate_next_run()
        self.last_run_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "schedule_type": self.schedule_type.value,
            "interval_seconds": self.interval_seconds,
            "fixed_time": self.fixed_time.strftime("%H:%M") if self.fixed_time else None,
            "weekdays": self.weekdays,
            "cron_expression": self.cron_expression,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "last_result": str(self.last_result) if self.last_result else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "requires_game": self.requires_game,
            "priority": self.priority,
            "enabled": self.enabled,
            "is_long_interval": self.is_long_interval,
            "next_run": self.next_run_str,
            "schedule_description": self.schedule_description,
            "execution_count": self.execution_count,
            "average_execution_time": self.average_execution_time
        }


class TaskCallback:
    """任务回调处理器"""
    def __init__(self, task_owner):
        self.task_owner = task_owner

    def on_task_start(self, task: Task):
        if task.is_long_interval:
            print(f"{datetime.now().isoformat()}[{self.task_owner}][回调] 任务开始: {task.name} ID: {task.task_id}")

    def on_task_complete(self, task: Task, result):
        if task.is_long_interval:
            print(f"{datetime.now().isoformat()}[{self.task_owner}][回调] 任务完成: {task.name}, 结果: {result}")

    def on_task_skip(self, task: Task, reason: str):
        print(f"{datetime.now().isoformat()}[{self.task_owner}][回调] 任务跳过: {task.name}, 原因: {reason}")

    def on_task_fail(self, task: Task, error: str):
        print(f"{datetime.now().isoformat()}[{self.task_owner}][回调] 任务失败: {task.name}, 错误: {error}")

    def on_game_event(self, event: str, data: Dict[str, Any]):
        print(f"{datetime.now().isoformat()}[{self.task_owner}][回调] 游戏事件: {event}, 数据: {data}")


class GameTaskManager:
    """游戏任务队列管理器"""

    def __init__(self, automator: WinterLess, name: str = "GameTaskManager"):
        """
        初始化任务管理器

        Args:
            automator: MumuGameAutomator实例
            name: 管理器名称
        """
        self.automator = automator
        self.name = name

        # 任务存储
        self.tasks: Dict[str, Task] = {}
        self.task_queue = []  # 优先队列
        self.waiting_queue = deque()  # 等待队列（长间隔任务）

        # 执行状态
        self.running_task: Optional[Task] = None
        self.history = deque(maxlen=1000)  # 执行历史

        # 控制
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # 默认不暂停

        # 线程
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running = False

        # 统计
        self.stats = {
            "total_executed": 0,
            "total_completed": 0,
            "total_skipped": 0,
            "total_failed": 0,
            "total_waiting": 0,
            "start_time": datetime.now(),
            "last_update": datetime.now()
        }

        # 回调
        self.callbacks = TaskCallback(task_owner=self.name)

        # 游戏状态监控
        self.game_monitor_thread: Optional[threading.Thread] = None
        self.game_check_interval = 5  # 秒

        print(f"[{self.name}] 初始化完成，关联游戏")

    # ==================== 任务管理 ====================

    def add_task(
            self,
            name: str,
            func: Callable,
            interval_seconds: float = 0,
            schedule_type: ScheduleType = ScheduleType.INTERVAL,
            fixed_time: Union[str, dt_time, None] = None,
            weekdays: Optional[List[int]] = None,
            cron_expression: Optional[str] = None,
            requires_game: bool = True,
            immediate: bool = False,
            max_retries: int = 3,
            priority: int = 5,
            enabled: bool = True,
            data: Optional[Dict[str, Any]] = None,
            debug: bool = False
    ) -> str:
        """
        添加新任务

        Args:
            name: 任务名称
            func: 任务函数
            interval_seconds: 执行间隔（秒）- 用于INTERVAL类型
            schedule_type: 调度类型
            fixed_time: 固定时间，支持字符串格式 "HH:MM" 或 dt_time对象
            weekdays: 星期几执行，0=周一, 6=周日
            cron_expression: Cron表达式，如 "0 4 * * *" 表示每天4点
            requires_game: 是否需要游戏运行
            immediate: 是否立即执行一次
            max_retries: 最大重试次数
            priority: 优先级（1-10，1最高）
            enabled: 是否启用
            data: 附加数据
            debug: 启用调试

        Returns:
            任务ID
        """
        with self.lock:
            task_id = f"{name}_{uuid.uuid4().hex[:12]}"

            # 处理fixed_time参数
            fixed_time_obj = None
            if fixed_time:
                if isinstance(fixed_time, str):
                    try:
                        hour, minute = map(int, fixed_time.split(":"))
                        fixed_time_obj = dt_time(hour=hour, minute=minute)
                    except ValueError:
                        raise ValueError(f"无效的时间格式: {fixed_time}，请使用 HH:MM 格式")
                elif isinstance(fixed_time, dt_time):
                    fixed_time_obj = fixed_time

            # 计算首次执行时间
            scheduled_time = datetime.now()
            if not immediate:
                # 创建临时任务对象来计算首次执行时间
                temp_task = Task(
                    scheduled_time=scheduled_time,
                    task_id=task_id,
                    name=name,
                    func=func,
                    schedule_type=schedule_type,
                    interval_seconds=interval_seconds,
                    fixed_time=fixed_time_obj,
                    weekdays=weekdays,
                    cron_expression=cron_expression
                )
                scheduled_time = temp_task.calculate_next_run()

            # 创建任务
            task = Task(
                scheduled_time=scheduled_time,
                task_id=task_id,
                name=name,
                func=func,
                schedule_type=schedule_type,
                interval_seconds=interval_seconds,
                fixed_time=fixed_time_obj,
                weekdays=weekdays,
                cron_expression=cron_expression,
                requires_game=requires_game,
                max_retries=max_retries,
                priority=priority,
                enabled=enabled,
                data=data or {}
            )

            # 添加到管理
            self.tasks[task_id] = task
            heapq.heappush(self.task_queue, task)

            if debug:
                print(f"[{self.name}] 添加任务: {name}")
                print(f"  ID: {task_id}, 类型: {schedule_type.value}")
                print(f"  调度: {task.schedule_description}")
                print(f"  需游戏运行: {requires_game}, 优先级: {priority}")
                print(f"  下次执行: {task.next_run_str}")
            return task_id

    def add_daily_task(
            self,
            name: str,
            func: Callable,
            time_str: str,  # "HH:MM"格式
            **kwargs
    ) -> str:
        """
        添加每日定时任务

        Args:
            name: 任务名称
            func: 任务函数
            time_str: 执行时间，格式 "HH:MM"
            **kwargs: 其他参数传递给add_task

        Returns:
            任务ID
        """
        return self.add_task(
            name=name,
            func=func,
            schedule_type=ScheduleType.DAILY,
            fixed_time=time_str,
            **kwargs
        )

    def add_weekly_task(
            self,
            name: str,
            func: Callable,
            time_str: str,  # "HH:MM"格式
            weekdays: List[int],  # 0=周一, 6=周日
            **kwargs
    ) -> str:
        """
        添加每周定时任务

        Args:
            name: 任务名称
            func: 任务函数
            time_str: 执行时间，格式 "HH:MM"
            weekdays: 执行星期，如[0, 2, 4]表示周一、三、五
            **kwargs: 其他参数传递给add_task

        Returns:
            任务ID
        """
        return self.add_task(
            name=name,
            func=func,
            schedule_type=ScheduleType.WEEKLY,
            fixed_time=time_str,
            weekdays=weekdays,
            **kwargs
        )

    def add_cron_task(
            self,
            name: str,
            func: Callable,
            cron_expression: str,  # "0 4 * * *" 表示每天4点
            **kwargs
    ) -> str:
        """
        添加Cron表达式任务

        Args:
            name: 任务名称
            func: 任务函数
            cron_expression: Cron表达式
            **kwargs: 其他参数传递给add_task

        Returns:
            任务ID
        """
        return self.add_task(
            name=name,
            func=func,
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression,
            **kwargs
        )

    # 示例：添加早上4点执行的任务
    def add_4am_task(self, name: str, func: Callable, **kwargs) -> str:
        """添加每天早上4点执行的任务"""
        return self.add_daily_task(name, func, "04:00", **kwargs)

    def remove_task(self, task_id: str, debug: bool = False) -> bool:
        """移除任务"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks.pop(task_id)
                new_queue = [task for task in self.task_queue if task.task_id != task_id]
                heapq.heapify(new_queue)
                self.task_queue = new_queue
                if debug:
                    print(f"[{self.name}] 移除任务: {task.name} (ID: {task_id})")
                return True
            return False

    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].enabled = True
                print(f"[{self.name}] 启用任务: {self.tasks[task_id].name}")
                return True
            return False

    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].enabled = False
                print(f"[{self.name}] 禁用任务: {self.tasks[task_id].name}")
                return True
            return False

    def update_task_schedule(self, task_id: str, **kwargs) -> bool:
        """更新任务调度设置"""
        with self.lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]

            # 更新字段
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            # 重新计算下次执行时间
            task.schedule_next()

            # 重新放入队列
            self._reschedule_task(task)

            print(f"[{self.name}] 更新任务调度: {task.name}")
            print(f"  新调度: {task.schedule_description}")
            print(f"  下次执行: {task.next_run_str}")

            return True

    def _reschedule_task(self, task: Task) -> None:
        """重新安排任务到队列"""
        # 从当前队列中移除（如果有）
        new_queue = []
        for t in self.task_queue:
            if t.task_id != task.task_id:
                new_queue.append(t)

        # 重新堆化
        self.task_queue = new_queue
        heapq.heapify(self.task_queue)

        # 添加任务
        heapq.heappush(self.task_queue, task)

    # ==================== 任务执行逻辑 ====================

    def _should_skip_task(self, task: Task) -> tuple[bool, str]:
        """
        判断任务是否应该跳过

        返回: (是否跳过, 原因)
        """
        # 任务未启用
        if not task.enabled:
            return True, "任务未启用"

        # 检查游戏状态（在检查运行任务之前）
        if task.requires_game and not self.automator.is_ready():
            return True, "游戏未就绪"

        # 有任务正在运行
        if self.running_task is not None:
            # 短间隔任务跳过
            if not task.is_long_interval:
                return True, "短间隔任务冲突（正在执行其他任务）"
            # 长间隔任务放入等待队列
            return True, "长间隔任务排队"

        return False, ""

    def _execute_task(self, task: Task) -> None:
        """执行单个任务"""
        task_start_time = datetime.now()
        task.execution_count += 1

        try:
            # 记录开始
            self._log_task_start(task)

            # 回调
            self.callbacks.on_task_start(task)

            # 执行任务函数
            result = task.func(self.automator)

            # 计算执行时间
            execution_time = (datetime.now() - task_start_time).total_seconds()
            task.total_execution_time += execution_time
            if task.execution_count > 0:
                task.average_execution_time = task.total_execution_time / task.execution_count

            # 更新任务状态
            task.last_result = result
            task.retry_count = 0  # 重置重试计数

            # 记录完成
            self._log_task_complete(task, result, task_start_time)

            # 回调
            self.callbacks.on_task_complete(task, result)

            if task.is_long_interval:
                print(f"{datetime.now().isoformat()}[{self.name}] ✓ 任务完成: {task.name}, 耗时: {execution_time:.2f}秒")

        except Exception as e:
            # 计算执行时间
            execution_time = (datetime.now() - task_start_time).total_seconds()
            task.total_execution_time += execution_time
            if task.execution_count > 0:
                task.average_execution_time = task.total_execution_time / task.execution_count

            # 记录失败
            error_msg = f"{type(e).__name__}: {str(e)}"
            self._log_task_fail(task, error_msg, task_start_time)

            # 回调
            self.callbacks.on_task_fail(task, error_msg)

            print(f"[{self.name}] ✗ 任务失败: {task.name} - {error_msg}")

            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                retry_delay = min(task.interval_seconds * task.retry_count, 300)  # 最多5分钟

                # 对于定时任务，使用最小重试延迟
                if task.schedule_type != ScheduleType.INTERVAL:
                    retry_delay = min(60 * task.retry_count, 300)  # 最多5分钟

                task.scheduled_time = datetime.now() + timedelta(seconds=retry_delay)

                # 重新放入队列
                heapq.heappush(self.task_queue, task)

                print(f"[{self.name}] 准备重试 ({task.retry_count}/{task.max_retries}): {task.name}")
            else:
                print(f"[{self.name}] 重试次数耗尽，任务禁用: {task.name}")
                task.enabled = False

    def _process_task_queue(self) -> None:
        """处理任务队列"""
        while not self.stop_event.is_set():
            # 等待暂停信号
            self.pause_event.wait()

            with self.lock:
                current_time = datetime.now()

                # 检查是否有任务到执行时间
                while self.task_queue and self.task_queue[0].scheduled_time <= current_time:
                    task = heapq.heappop(self.task_queue)

                    # 检查是否应该跳过
                    should_skip, reason = self._should_skip_task(task)

                    if should_skip:
                        # 记录跳过
                        self._log_task_skip(task, reason)
                        self.callbacks.on_task_skip(task, reason)

                        # 如果是长间隔任务，放入等待队列
                        if task.is_long_interval and "排队" in reason:
                            self.waiting_queue.append(task)
                            print(f"[{self.name}] 长间隔任务排队: {task.name}")
                            continue

                        # 对于被跳过的任务，只有在不是因为排队原因时才重新安排
                        # 这样可以避免因为游戏未就绪等永久性问题导致的无限循环
                        if reason != "游戏未就绪" or not task.requires_game:
                            # 重新安排下次执行
                            task.schedule_next()
                            heapq.heappush(self.task_queue, task)
                        else:
                            # 如果是因为游戏未就绪，记录警告但不重新添加到队列
                            print(f"[{self.name}] 任务因游戏未就绪被跳过: {task.name}, 不会重新安排直到游戏就绪")
                        continue

                    # 执行任务
                    self.running_task = task

                    # 执行任务（在锁外执行，避免阻塞队列）
                    try:
                        self._execute_task(task)
                    finally:
                        self.running_task = None

                    # 重新安排下次执行
                    task.schedule_next()
                    heapq.heappush(self.task_queue, task)

                # 检查等待队列
                # 即使有任务正在运行，也要尝试处理等待队列中的长间隔任务
                # 因为长间隔任务可以排队等待执行
                if self.waiting_queue:
                    task = self.waiting_queue.popleft()
                    print(f"[{self.name}] 检查等待队列中的任务: {task.name}")

                    # 检查是否可以执行此任务
                    should_skip, reason = self._should_skip_task(task)
                    
                    if should_skip and reason != "长间隔任务排队":  # 如果不是因为排队原因导致的跳过
                        # 如果是因为游戏未就绪或其他原因跳过，放回等待队列末尾
                        self.waiting_queue.append(task)
                        print(f"[{self.name}] 等待队列任务被跳过: {task.name}, 原因: {reason}")
                    else:
                        # 执行任务
                        self.running_task = task
                        try:
                            self._execute_task(task)
                        finally:
                            self.running_task = None

                        # 重新安排
                        task.schedule_next()
                        heapq.heappush(self.task_queue, task)

            # 短暂休眠
            time.sleep(0.1)

            # 每隔一定次数的循环执行清理任务（每100次循环）
            if hasattr(self, '_cleanup_counter'):
                self._cleanup_counter += 1
            else:
                self._cleanup_counter = 1
            
            if self._cleanup_counter % 100 == 0:  # 每100次循环执行一次清理
                cleaned = self.cleanup_tasks()
                if cleaned > 0:
                    print(f"[{self.name}] 清理了 {cleaned} 个无效任务")

    # ==================== 日志记录 ====================

    def _log_task_start(self, task: Task) -> None:
        """记录任务开始"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task.task_id,
            "task_name": task.name,
            "schedule_type": task.schedule_type.value,
            "event": "start",
            "status": "running"
        }
        self.history.append(record)

    def _log_task_complete(self, task: Task, result: Any, start_time: datetime) -> None:
        """记录任务完成"""
        duration = (datetime.now() - start_time).total_seconds()

        record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task.task_id,
            "task_name": task.name,
            "schedule_type": task.schedule_type.value,
            "event": "complete",
            "status": "completed",
            "result": str(result),
            "duration": duration
        }
        self.history.append(record)
        self.stats["total_completed"] += 1
        self.stats["total_executed"] += 1

    def _log_task_fail(self, task: Task, error: str, start_time: datetime) -> None:
        """记录任务失败"""
        duration = (datetime.now() - start_time).total_seconds()

        record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task.task_id,
            "task_name": task.name,
            "schedule_type": task.schedule_type.value,
            "event": "fail",
            "status": "failed",
            "error": error,
            "duration": duration
        }
        self.history.append(record)
        self.stats["total_failed"] += 1
        self.stats["total_executed"] += 1

    def _log_task_skip(self, task: Task, reason: str) -> None:
        """记录任务跳过"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task.task_id,
            "task_name": task.name,
            "schedule_type": task.schedule_type.value,
            "event": "skip",
            "status": "skipped",
            "reason": reason
        }
        self.history.append(record)
        self.stats["total_skipped"] += 1

    def cleanup_tasks(self) -> int:
        """清理无效或错误的任务，返回清理的任务数量"""
        with self.lock:
            cleaned_count = 0
            valid_tasks = []
            
            for task in self.task_queue:
                # 检查任务是否有效
                if task.task_id in self.tasks:
                    valid_tasks.append(task)
                else:
                    # 从队列中移除已不存在的任务
                    cleaned_count += 1
                    print(f"[{self.name}] 清理无效任务: {task.name} (ID: {task.task_id})")
            
            # 重建队列
            self.task_queue = valid_tasks
            heapq.heapify(self.task_queue)
            
            return cleaned_count

    # ==================== 控制方法 ====================

    def start(self) -> None:
        """启动任务管理器"""
        if self.is_running:
            print(f"[{self.name}] 已经在运行中")
            return

        print(f"[{self.name}] 启动任务管理器...")

        self.stop_event.clear()
        self.is_running = True

        # 启动工作线程
        self.worker_thread = threading.Thread(
            target=self._process_task_queue,
            name=f"{self.name}-Worker",
            daemon=True
        )
        self.worker_thread.start()

        # 启动游戏监控线程
        self._start_game_monitor()

        print(f"[{self.name}] 任务管理器已启动，任务数: {len(self.tasks)}")

    def stop(self, wait: bool = True) -> None:
        """停止任务管理器"""
        if not self.is_running:
            return

        print(f"[{self.name}] 停止任务管理器...")

        self.stop_event.set()
        self.is_running = False

        # 停止游戏监控
        self._stop_game_monitor()

        if wait and self.worker_thread:
            self.worker_thread.join(timeout=5.0)

        print(f"[{self.name}] 任务管理器已停止")

    def pause(self) -> None:
        """暂停任务执行"""
        self.pause_event.clear()
        print(f"[{self.name}] 任务执行已暂停")

    def resume(self) -> None:
        """恢复任务执行"""
        self.pause_event.set()
        print(f"[{self.name}] 任务执行已恢复")

    # ==================== 游戏监控 ====================

    def _start_game_monitor(self) -> None:
        """启动游戏状态监控"""
        self.game_monitor_thread = threading.Thread(
            target=self._monitor_game_status,
            name=f"{self.name}-GameMonitor",
            daemon=True
        )
        self.game_monitor_thread.start()

    def _stop_game_monitor(self) -> None:
        """停止游戏监控"""
        if self.game_monitor_thread:
            # 通过设置标志停止
            pass

    def _monitor_game_status(self) -> None:
        """监控游戏状态"""
        while not self.stop_event.is_set():
            try:
                # 获取游戏状态
                status = self.automator.get_status()

                # 游戏状态变化处理
                if not status["is_running"] and self.running_task:
                    # 游戏意外关闭，停止当前任务
                    print(f"[{self.name}] 警告: 游戏意外关闭")

                # 更新统计
                self.stats["last_update"] = datetime.now()

            except Exception as e:
                print(f"[{self.name}] 游戏监控错误: {e}")

            # 等待下次检查
            time.sleep(self.game_check_interval)

    # ==================== 查询方法 ====================

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        with self.lock:
            if task_id in self.tasks:
                return self.tasks[task_id].to_dict()
            return None

    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        with self.lock:
            return [task.to_dict() for task in self.tasks.values()]

    def get_running_task(self) -> Optional[Dict[str, Any]]:
        """获取当前运行的任务"""
        with self.lock:
            if self.running_task:
                return self.running_task.to_dict()
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        runtime = (datetime.now() - self.stats["start_time"]).total_seconds()

        return {
            **self.stats,
            "runtime_seconds": runtime,
            "runtime_formatted": self._format_runtime(runtime),
            "total_tasks": len(self.tasks),
            "queue_size": len(self.task_queue),
            "waiting_queue_size": len(self.waiting_queue),
            "is_running": self.is_running,
            "running_task": self.running_task.name if self.running_task else None
        }

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return list(self.history)[-limit:]

    def get_upcoming_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取即将执行的任务"""
        with self.lock:
            upcoming = []
            now = datetime.now()

            # 从队列中取前limit个
            for task in sorted(self.task_queue, key=lambda x: x.scheduled_time)[:limit]:
                if task.scheduled_time > now:
                    task_info = task.to_dict()
                    task_info["seconds_until"] = (task.scheduled_time - now).total_seconds()
                    upcoming.append(task_info)

            return upcoming

    def _format_runtime(self, seconds: float) -> str:
        """格式化运行时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# ==================== 使用示例 ====================
def example_usage():
    """使用示例"""
    # 创建虚拟的automator
    automator = MumuGameAutomator()
    manager = GameTaskManager(automator, "示例管理器")

    # 定义一些示例任务函数
    def daily_check():
        return "检查完成"

    def weekly_backup():
        print("执行每周备份...")
        return "备份完成"

    def cleanup_task():
        print("执行清理任务...")
        return "清理完成"

    # 添加定时任务
    # 1. 每天4点执行的任务
    manager.add_4am_task("每日4点检查", daily_check)

    # 2. 每天早上9点执行
    manager.add_daily_task("早上9点任务", daily_check, "09:00")

    # 3. 每周一、三、五的14:30执行
    manager.add_weekly_task("周任务", weekly_backup, "14:30", weekdays=[0, 2, 4])

    # 4. 使用cron表达式：每天0点执行
    manager.add_cron_task("午夜任务", cleanup_task, "0 0 * * *")

    # 5. 传统的间隔任务
    manager.add_task("间隔任务", cleanup_task, interval_seconds=300)

    # 启动管理器
    manager.start()

    # 运行一段时间后停止
    import time
    time.sleep(10)

    # 查看任务列表
    tasks = manager.list_tasks()
    for task in tasks:
        print(f"任务: {task['name']}, 下次执行: {task['next_run']}")

    # 查看即将执行的任务
    upcoming = manager.get_upcoming_tasks(5)
    print(f"\n即将执行的任务:")
    for task in upcoming:
        print(f"  {task['name']}: {task['next_run']} ({task['seconds_until']:.0f}秒后)")

    # 停止管理器
    manager.stop()


if __name__ == "__main__":
    example_usage()
