# task_manager_gui_optimized.py - 优化版任务管理器图形界面
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import json
import csv
import os
from datetime import datetime, timedelta
import time
import random

# 导入任务管理器
from TaskQueueManager import GameTaskManager, ScheduleType
from MumuManager import MumuGameAutomator
from TaskList import WinterLess


class TaskManagerGUI:
    """优化版任务管理器图形界面"""

    def __init__(self, device_id: int, mmm_path: str = r'C:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe'):

        self.root = tk.Tk()
        self.root.geometry("1000x700")

        self.config_file = "game_tasks_config.json"

        self.automator = MumuGameAutomator(mumu_device=device_id, game_package="com.gof.china",
                                           mmm_path=mmm_path)
        self.automator.start_game()
        self.winter = WinterLess(self.automator)
        self.task_manager = GameTaskManager(self.winter, self.automator.adb.device_name)
        self.root.title(self.automator.adb.device_name)

        # 设置样式
        self.setup_styles()

        # 缓存和状态
        self.task_id_map = {}  # item_id -> task_id
        self.last_update_time = 0
        self.last_history_hash = 0
        self.last_upcoming_hash = 0
        self.selected_task_id = None

        # 更新控制
        self.update_interval = 2000  # 2秒更新一次
        self.partial_updates = True  # 启用部分更新
        self.update_running = True

        self.checkbox_vars = {}
        self.task_ids = {}  # 存储功能名称到任务ID的映射

        self.task_definitions = {
            # 核心功能组
            "城镇内": {
                "练兵": {
                    "func": self.soldier_training,
                    "schedule_type": ScheduleType.INTERVAL,
                    "interval_seconds": 1800,  # 30分钟
                    "immediate": True,
                    "requires_game": True
                },
                "仓库收益": {
                    "func": self.warehouse_reward,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "27 * * * *",
                    "requires_game": True
                },
                "探险收益": {
                    "func": self.adventure_gain,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "40 */8 * * *",
                    "requires_game": True
                },
                "宠物寻宝": {
                    "func": self.pet_treasure,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "45 1,7,15,23 * * *",
                    "requires_game": True
                },
                "火晶实验": {
                    "func": self.crystal_lab,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "30 3 * * *",
                    "immediate": False,
                    "requires_game": True
                },
                "银行日存": {
                    "func": self.bank_deposit,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "30 23 * * *",
                    "requires_game": True
                },
                "统帅领取": {
                    "func": self.commander_reward,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "37 3 * * *",
                    "immediate": False,
                    "requires_game": True
                },
                "每日奖励": {
                    "func": self.daily_reward,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "39 3 * * *",
                    "immediate": False,
                    "requires_game": True
                },
                "地心探险": {
                    "func": self.earth_core,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "41 3 * * *",
                    "immediate": False,
                    "requires_game": True
                },
                "游荡商人": {
                    "func": self.store_purchase,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "43 3 * * *",
                    "requires_game": True
                },
                "免费招募": {
                    "func": self.hero_recruit,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "3 * * * *",
                    "requires_game": True
                }
            },
            # 网络功能组
            "野外": {
                "采集": {
                    "func": self.mining,
                    "schedule_type": ScheduleType.INTERVAL,
                    "interval_seconds": 590,  # 10分钟
                    "immediate": True,
                    "requires_game": True
                },
                "自动上车": {
                    "func": self.monster_hunt,
                    "schedule_type": ScheduleType.INTERVAL,
                    "interval_seconds": 30,  # 5分钟
                    "requires_game": True
                },
                "自动打巨兽": {
                    "func": self.monster_hunter,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "50 * * * *",
                    "requires_game": True
                }
            },
            # 辅助功能组
            "联盟任务": {
                "联盟捐献": {
                    "func": self.alliance_donating,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "5 */2 * * *",
                    "requires_game": True
                },
                "联盟宝箱": {
                    "func": self.alliance_treasure,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "45 */2 * * *",
                    "requires_game": True
                },
                "红包与互助": {
                    "func": self.performance_analysis_task,
                    "schedule_type": ScheduleType.INTERVAL,
                    "interval_seconds": 5,
                    "requires_game": True
                }
            },
            # 安全功能组
            "其他": {
                "晨曦岛": {
                    "func": self.island_gain,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "59 */2 * * *",
                    "requires_game": True
                },
                "更新上车记录": {
                    "func": self.check_hunter_status,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "1 * * * *",
                    "immediate": True,
                    "requires_game": True
                },
                "更新盟矿": {
                    "func": self.set_alliance_mine,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "40 7,19 * * *",
                    "requires_game": True
                },
                "阅读邮件": {
                    "func": self.read_mails,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "3 */3 * * *",
                    "requires_game": True
                }
            },
            # 工具功能组
            "阶段性任务": {
                "总动员刷任务": {
                    "func": self.alliance_mobilization,
                    "schedule_type": ScheduleType.INTERVAL,
                    "interval_seconds": 150,  # 30分钟
                    "requires_game": True
                }
            }
        }
        self.function_groups = {}
        for group_name, functions in self.task_definitions.items():
            self.function_groups[group_name] = list(functions.keys())

        self.default_config = self.create_default_config()

        # 创建界面
        self.create_widgets()

        self.current_config = self.load_config()

        # 启动界面更新
        self.start_update_loop()

        self.initialize_checkboxes()

        # 窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        """设置样式"""
        style = ttk.Style()

        # 定义颜色
        self.colors = {
            "bg": "#f0f0f0",
            "fg": "#333333",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336",
            "info": "#2196F3",
            "running": "#2196F3",
            "completed": "#4CAF50",
            "failed": "#F44336",
            "skipped": "#FF9800",
            "paused": "#9E9E9E"
        }

    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # 标题栏
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky=(tk.W, tk.E))

        title_label = ttk.Label(
            title_frame,
            text=f"📋 {self.task_manager.name}",
            font=("Arial", 14, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)

        # 状态标签
        self.status_label = ttk.Label(
            title_frame,
            text="状态: 运行中",
            foreground=self.colors["success"]
        )
        self.status_label.grid(row=0, column=1, padx=20)

        # 控制按钮
        control_frame = ttk.Frame(title_frame)
        control_frame.grid(row=0, column=2, sticky=tk.E)

        self.pause_btn = ttk.Button(
            control_frame,
            text="⏸ 暂停",
            command=self.toggle_pause,
            width=8
        )
        self.pause_btn.grid(row=0, column=0, padx=2)

        self.stop_btn = ttk.Button(
            control_frame,
            text="⏹ 停止",
            command=self.stop_manager,
            width=8
        )
        self.stop_btn.grid(row=0, column=1, padx=2)

        # 统计信息栏（简化版）
        stats_frame = ttk.LabelFrame(main_frame, text="📊 统计", padding="5")
        stats_frame.grid(row=1, column=0, columnspan=2, pady=(0, 5), sticky=(tk.W, tk.E))

        # 创建关键统计标签
        self.stats_labels = {}
        stats_items = [
            ("运行:", "runtime_formatted"),
            ("任务:", "total_tasks"),
            ("成功:", "total_completed"),
            ("失败:", "total_failed"),
        ]

        for i, (label_text, key) in enumerate(stats_items):
            ttk.Label(stats_frame, text=label_text, font=("Arial", 9)).grid(
                row=0, column=i * 2, sticky=tk.W, padx=(5, 2), pady=2
            )
            self.stats_labels[key] = ttk.Label(
                stats_frame,
                text="0",
                font=("Arial", 9)
            )
            self.stats_labels[key].grid(
                row=0, column=i * 2 + 1, sticky=tk.W, padx=(0, 10), pady=2
            )

        # 创建主内容区域
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 任务列表标签页
        tasks_tab = ttk.Frame(notebook)
        notebook.add(tasks_tab, text="📋 任务")

        # 任务列表工具栏
        tasks_toolbar = ttk.Frame(tasks_tab)
        tasks_toolbar.pack(fill=tk.X, padx=5, pady=(5, 2))

        self.create_group(tasks_toolbar, "城镇内", self.function_groups["城镇内"],
                           column=0, row=0, columns=2)
        self.create_group(tasks_toolbar, "野外", self.function_groups["野外"],
                           column=1, row=0, columns=2)
        self.create_group(tasks_toolbar, "联盟任务", self.function_groups["联盟任务"],
                           column=0, row=1, columns=2)
        self.create_group(tasks_toolbar, "其他", self.function_groups["其他"],
                           column=1, row=1, columns=2)
        self.create_group(tasks_toolbar, "阶段性任务", self.function_groups["阶段性任务"],
                           column=2, row=1, columns=2)

        # 详情标签页
        details_tab = ttk.Frame(notebook)
        notebook.add(details_tab, text="📄 详情")

        # 详情内容框架
        details_frame = ttk.Frame(details_tab)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 详情文本区域（使用只读文本框，比多个标签更高效）
        self.details_text = scrolledtext.ScrolledText(
            details_frame,
            width=40,
            height=20,
            font=("Consolas", 9),
            state="disabled"
        )
        self.details_text.pack(fill=tk.BOTH, expand=True)

        # 即将执行标签页
        upcoming_tab = ttk.Frame(notebook)
        notebook.add(upcoming_tab, text="⏰ 即将执行")

        # 即将执行列表
        self.upcoming_tree = ttk.Treeview(
            upcoming_tab,
            columns=("name", "next_run", "seconds_until"),
            show="headings",
            height=15
        )

        # 定义列
        self.upcoming_tree.heading("name", text="任务名称")
        self.upcoming_tree.heading("next_run", text="执行时间")
        self.upcoming_tree.heading("seconds_until", text="剩余时间")

        # 设置列宽
        self.upcoming_tree.column("name", width=200, stretch=True)
        self.upcoming_tree.column("next_run", width=150)
        self.upcoming_tree.column("seconds_until", width=100)

        # 添加滚动条
        upcoming_scrollbar = ttk.Scrollbar(upcoming_tab, orient=tk.VERTICAL, command=self.upcoming_tree.yview)
        self.upcoming_tree.configure(yscrollcommand=upcoming_scrollbar.set)

        # 布局
        self.upcoming_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        upcoming_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # 历史记录标签页（按需加载）
        self.history_tab = ttk.Frame(notebook)
        notebook.add(self.history_tab, text="📜 历史")

        # 历史记录工具栏
        history_toolbar = ttk.Frame(self.history_tab)
        history_toolbar.pack(fill=tk.X, padx=5, pady=(5, 2))

        ttk.Button(
            history_toolbar,
            text="🔄 刷新",
            command=self.refresh_history,
            width=8
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            history_toolbar,
            text="🗑️ 清空",
            command=self.clear_history,
            width=8
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            history_toolbar,
            text="💾 导出",
            command=self.export_history,
            width=8
        ).pack(side=tk.LEFT)

        # 历史记录文本框（按需加载）
        self.history_text = None

        # 底部状态栏
        status_bar = ttk.Frame(main_frame)
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))

        self.status_message = tk.StringVar(value="就绪")
        ttk.Label(
            status_bar,
            textvariable=self.status_message,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Arial", 9)
        ).pack(fill=tk.X, ipady=2)

    def create_group(self, parent, group_name, functions, column, row, padx=5, pady=5, columns=2):
        group_frame = ttk.LabelFrame(
            parent,
            text=f" {group_name}",
            style='Group.TLabelframe'
        )
        group_frame.grid(
            row=row, column=column,
            sticky='nsew', padx=padx, pady=pady
        )

        for i in range(columns):
            group_frame.grid_columnconfigure(i, weight=1)

        # 创建复选框并分配到多列
        func_count = len(functions)
        items_per_column = (func_count + columns - 1) // columns

        for i, func in enumerate(functions):
            var = tk.BooleanVar()
            self.checkbox_vars[f"{group_name}_{func}"] = var

            col = i // items_per_column
            row_in_col = i % items_per_column

            # 创建复选框
            checkbox = ttk.Checkbutton(
                group_frame,
                text=func,
                variable=var,
                command=lambda f=func, g=group_name: self.on_checkbox_toggle(f, g)
            )
            checkbox.grid(row=row_in_col, column=col, sticky='w', padx=15)

    def start_update_loop(self):
        """启动更新循环"""
        self.update_display()

    def update_display(self):
        """更新显示"""
        if not self.update_running:
            return

        try:
            current_time = time.time()

            # 基本状态更新（每次都需要）
            self.update_basic_status()

            # 任务列表更新（2秒一次）
            if current_time - self.last_update_time > 2:
                # self.update_tasks_list()
                self.last_update_time = current_time

            # 即将执行列表更新（5秒一次）
            if current_time - self.last_upcoming_hash > 5:
                self.update_upcoming_list()
                self.last_upcoming_hash = current_time

            # 如果选中了任务，更新详情
            if self.selected_task_id:
                self.update_task_details()

        except Exception as e:
            # 减少错误输出频率
            if random.random() < 0.1:  # 10%概率输出错误
                print(f"更新错误: {e}")

        # 安排下一次更新
        self.root.after(self.update_interval, self.update_display)

    def update_basic_status(self):
        """更新基本状态"""
        try:
            if self.task_manager.is_running:
                if self.task_manager.pause_event.is_set():
                    self.status_label.config(text="状态: 运行中", foreground=self.colors["success"])
                    self.pause_btn.config(text="⏸ 暂停", command=self.toggle_pause)
                else:
                    self.status_label.config(text="状态: 已暂停", foreground=self.colors["paused"])
                    self.pause_btn.config(text="▶ 恢复", command=self.toggle_pause)
            else:
                self.status_label.config(text="状态: 已停止", foreground=self.colors["error"])
                self.pause_btn.config(text="▶ 启动", command=self.start_manager)

            # 更新统计信息（减少频率）
            stats = self.task_manager.get_stats()
            for key, label in self.stats_labels.items():
                if key in stats:
                    label.config(text=str(stats[key]))

        except Exception as e:
            pass  # 静默处理

    def get_task_status(self, task_info):
        """获取任务状态"""
        if self.task_manager.running_task and self.task_manager.running_task.task_id == task_info["task_id"]:
            return "运行中", self.colors["running"]
        elif not task_info.get("enabled", False):
            return "已禁用", self.colors["paused"]
        else:
            return "等待中", self.colors["info"]

    def update_upcoming_list(self):
        """更新即将执行列表（优化版）"""
        def execute_in_background():
            try:
                # 获取即将执行的任务
                upcoming = self.task_manager.get_upcoming_tasks(limit=10)

                # 计算哈希值检查是否需要更新
                current_hash = hash(str(upcoming))
                if current_hash == self.last_upcoming_hash and self.partial_updates:
                    return

                self.last_upcoming_hash = current_hash

                # 清空列表
                self.upcoming_tree.delete(*self.upcoming_tree.get_children())

                # 添加到列表
                for task in upcoming:
                    # 格式化剩余时间
                    seconds = task.get("seconds_until", 0)
                    if seconds < 60:
                        time_str = f"{int(seconds)}秒"
                    elif seconds < 3600:
                        time_str = f"{int(seconds / 60)}分钟"
                    else:
                        hours = int(seconds / 3600)
                        minutes = int((seconds % 3600) / 60)
                        time_str = f"{hours}小时{minutes}分钟"

                    # 添加任务到树
                    self.upcoming_tree.insert("", "end", values=(
                        task.get("name", "未知"),
                        task.get("next_run", "N/A"),
                        time_str
                    ))

            except Exception as e:
                pass  # 静默处理
        threading.Thread(target=execute_in_background, daemon=True).start()

    def update_task_details(self):
        """更新任务详情（按需加载）"""
        if not self.selected_task_id:
            return

        try:
            # 获取任务详情
            task_info = self.task_manager.get_task_info(self.selected_task_id)
            if not task_info:
                return

            # 启用文本框进行编辑
            self.details_text.config(state="normal")
            self.details_text.delete(1.0, tk.END)

            # 格式化任务详情
            details_lines = [
                f"任务ID: {task_info.get('task_id', '-')}",
                f"任务名称: {task_info.get('name', '-')}",
                f"调度方式: {task_info.get('schedule_description', '-')}",
                f"下次执行: {task_info.get('next_run', '-')}",
                f"上次执行: {task_info.get('last_run_time', '-')}",
                f"执行次数: {task_info.get('execution_count', 0)}",
                f"平均耗时: {task_info.get('average_execution_time', 0):.2f}秒",
                f"重试次数: {task_info.get('retry_count', 0)}/{task_info.get('max_retries', 3)}",
                f"优先级: {task_info.get('priority', 5)}",
                f"需游戏运行: {'是' if task_info.get('requires_game', True) else '否'}",
                f"状态: {'启用' if task_info.get('enabled', False) else '禁用'}",
                f"最后结果: {task_info.get('last_result', '-')}",
            ]

            # 添加任务数据
            if task_info.get('data'):
                details_lines.append("\n任务数据:")
                for key, value in task_info['data'].items():
                    details_lines.append(f"  {key}: {value}")

            # 插入详情
            self.details_text.insert(tk.END, "\n".join(details_lines))
            self.details_text.config(state="disabled")

        except Exception as e:
            pass  # 静默处理

    def refresh_history(self):
        """刷新历史记录"""
        if self.history_text is None:
            # 延迟创建历史记录文本框
            self.history_text = scrolledtext.ScrolledText(
                self.history_tab,
                width=40,
                height=20,
                font=("Consolas", 9),
                state="disabled"
            )
            self.history_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # 启用文本框进行编辑
        self.history_text.config(state="normal")
        self.history_text.delete(1.0, tk.END)

        try:
            # 获取历史记录
            history = self.task_manager.get_history(limit=50)

            # 添加历史记录
            for record in reversed(history):
                timestamp = record.get("timestamp", "")[:19].replace("T", " ")
                task_name = record.get("task_name", "未知")
                event = record.get("event", "")
                status = record.get("status", "")

                # 格式化行
                line = f"{timestamp} {task_name}: {event}"
                if "result" in record:
                    line += f" - {record['result']}"
                if "error" in record:
                    line += f" - {record['error']}"
                if "reason" in record:
                    line += f" - {record['reason']}"

                self.history_text.insert(tk.END, line + "\n")

        except Exception as e:
            self.history_text.insert(tk.END, f"加载历史记录失败: {e}\n")

        # 禁用文本框
        self.history_text.config(state="disabled")

    def clear_history(self):
        """清空历史记录"""
        if messagebox.askyesno("确认清空", "确定要清空历史记录吗？"):
            try:
                self.task_manager.history.clear()
                if self.history_text:
                    self.history_text.config(state="normal")
                    self.history_text.delete(1.0, tk.END)
                    self.history_text.config(state="disabled")
                messagebox.showinfo("成功", "历史记录已清空")
            except Exception as e:
                messagebox.showerror("错误", f"清空历史记录失败: {e}")

    def export_history(self):
        """导出历史记录"""
        # 选择保存文件
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

        if not file_path:
            return

        try:
            # 获取历史记录
            history = self.task_manager.get_history(limit=1000)

            with open(file_path, "w", encoding="utf-8") as f:
                for record in history:
                    timestamp = record.get("timestamp", "")[:19].replace("T", " ")
                    task_name = record.get("task_name", "未知")
                    event = record.get("event", "")
                    status = record.get("status", "")

                    line = f"{timestamp} - {task_name} - {event} - {status}"
                    if "result" in record:
                        line += f" - {record['result']}"
                    if "error" in record:
                        line += f" - {record['error']}"
                    if "reason" in record:
                        line += f" - {record['reason']}"

                    f.write(line + "\n")

            messagebox.showinfo("成功", f"历史记录已导出到: {file_path}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")


    def on_checkbox_toggle(self, function, group):
        """复选框状态改变时的回调"""
        var_name = f"{group}_{function}"
        enabled = self.checkbox_vars[var_name].get()
        state = "启用" if enabled else "禁用"

        # 更新状态标签
        # self.status_label.config(text=f"{group} - {function}: {state}", fg='blue')

        # 添加或移除任务
        self.add_or_remove_task(group, function, enabled)

        # 自动保存配置
        self.auto_save_config()

        # 更新统计信息
        self.update_stats()

    def initialize_checkboxes(self):
        """根据配置文件初始化复选框状态，并添加初始任务"""
        def execute_in_background():
            for group_name, functions in self.current_config.items():
                if group_name.startswith('_'):  # 跳过元数据
                    continue

                for func_name, state in functions.items():
                    var_name = f"{group_name}_{func_name}"
                    if var_name in self.checkbox_vars:
                        self.checkbox_vars[var_name].set(state)

                        # 如果启用，添加任务到任务管理器
                        if state:
                            self.add_or_remove_task(group_name, func_name, True)
            self.task_manager.start()
        threading.Thread(target=execute_in_background, daemon=True).start()

    def create_default_config(self):
        """创建默认配置"""
        config = {}
        for group_name, functions in self.task_definitions.items():
            config[group_name] = {}
            for func_name in functions:
                # 默认情况下，大部分功能不启用
                config[group_name][func_name] = False
        return config

    def load_config(self):
        """从配置文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 移除元数据部分（如果有）
                if "_metadata" in config_data:
                    config_data.pop("_metadata")

                # 验证配置文件结构
                if self.validate_config(config_data):
                    last_modified = os.path.getmtime(self.config_file)
                    last_modified_str = datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"已从配置文件加载配置 (最后修改时间: {last_modified_str})")
                    return config_data
                else:
                    print("配置文件格式无效，使用默认配置")
                    return self.create_default_config()
            else:
                print("配置文件不存在，使用默认配置")
                return self.create_default_config()

        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            print("使用默认配置")
            return self.create_default_config()

    def save_config(self):
        """保存配置到文件"""
        try:
            # 准备配置数据
            config_data = {}
            for group_name in self.function_groups.keys():
                config_data[group_name] = {}
                for func_name in self.function_groups[group_name]:
                    var_name = f"{group_name}_{func_name}"
                    if var_name in self.checkbox_vars:
                        config_data[group_name][func_name] = self.checkbox_vars[var_name].get()
                    else:
                        # 如果复选框变量不存在，使用默认值
                        config_data[group_name][func_name] = self.default_config.get(group_name, {}).get(func_name,
                                                                                                         False)

            # 添加元数据
            config_data["_metadata"] = {
                "last_modified": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "total_functions": len(self.checkbox_vars),
                "enabled_functions": sum(1 for var in self.checkbox_vars.values() if var.get())
            }

            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            print(f"配置已保存到: {self.config_file}")
            return True

        except Exception as e:
            print(f"保存配置文件时出错: {e}")
            return False

    def validate_config(self, config_data):
        """验证配置数据的结构"""
        try:
            # 检查是否包含所有必要的组
            for group_name in self.function_groups.keys():
                if group_name not in config_data:
                    print(f"配置文件中缺少组: {group_name}")
                    return False

                # 检查每个组是否包含所有功能
                group_config = config_data[group_name]
                for func_name in self.function_groups[group_name]:
                    if func_name not in group_config:
                        print(f"组 '{group_name}' 中缺少功能: {func_name}")
                        return False

                    # 检查值是否为布尔类型
                    if not isinstance(group_config[func_name], bool):
                        print(f"组 '{group_name}' 中功能 '{func_name}' 的值不是布尔类型")
                        return False

            return True

        except Exception as e:
            print(f"验证配置文件时出错: {e}")
            return False

    def add_or_remove_task(self, group_name, func_name, enabled):
        """根据复选框状态添加或移除任务"""
        def execute_in_background():
            task_key = f"{group_name}_{func_name}"

            if enabled:
                # 添加任务到任务管理器
                if group_name in self.task_definitions and func_name in self.task_definitions[group_name]:
                    task_config = self.task_definitions[group_name][func_name]

                    # 生成唯一任务ID
                    task_id = f"{group_name}_{func_name}_{int(datetime.now().timestamp())}"

                    # 添加任务
                    if task_config["schedule_type"] is ScheduleType.CRON:
                        self.task_manager.add_cron_task(
                            name=f"{group_name} - {func_name}",
                            func=task_config["func"],
                            cron_expression=task_config["cron_expression"],
                            immediate=task_config.get("immediate", False),
                            enabled=True
                        )
                    else:
                        self.task_manager.add_task(
                            name=f"{group_name} - {func_name}",
                            func=task_config["func"],
                            interval_seconds=task_config["interval_seconds"],
                            requires_game=task_config.get("requires_game", False),
                            immediate=task_config.get("immediate", False),
                            enabled=True
                        )

                    # 保存任务ID
                    self.task_ids[task_key] = task_id
                    print(f"已添加任务: {group_name} - {func_name}")
            else:
                # 从任务管理器移除任务
                # 查找并移除该功能对应的任务
                tasks_to_remove = []
                for task in self.task_manager.list_tasks():
                    if task['name'] == f"{group_name} - {func_name}":
                        tasks_to_remove.append(task['task_id'])

                for task_id in tasks_to_remove:
                    self.task_manager.remove_task(task_id)
                    print(f"已移除任务: {group_name} - {func_name}")

                # 从task_ids中移除
                if task_key in self.task_ids:
                    del self.task_ids[task_key]

        threading.Thread(target=execute_in_background, daemon=True).start()

    def auto_save_config(self):
        """自动保存配置到文件"""

        # 在单独的线程中保存配置，避免阻塞UI
        def save_thread():
            if self.save_config():
                # 更新状态显示
                pass
                '''
                self.root.after(100, lambda: self.status_label.config(
                    text="配置已自动保存",
                    fg='green'
                ))'''

        threading.Thread(target=save_thread, daemon=True).start()

    def update_stats(self):
        """更新统计信息"""
        enabled = sum(1 for var in self.checkbox_vars.values() if var.get())
        disabled = len(self.checkbox_vars) - enabled

        # 更新底部标签
        if hasattr(self, 'enabled_count'):
            self.enabled_count.config(text=f"已启用: {enabled}", fg='green')
            # self.disabled_count.config(text=f"已禁用: {disabled}", fg='red')
            # self.total_count.config(text=f"总数: {len(self.checkbox_vars)}")

    def toggle_pause(self):
        """切换暂停/恢复"""
        if self.task_manager.is_running:
            if self.task_manager.pause_event.is_set():
                self.task_manager.pause()
                self.status_message.set("任务执行已暂停")
            else:
                self.task_manager.resume()
                self.status_message.set("任务执行已恢复")

    def stop_manager(self):
        """停止任务管理器"""
        if messagebox.askyesno("确认停止", "确定要停止任务管理器吗？"):
            self.task_manager.stop()
            self.status_message.set("任务管理器已停止")

    def start_manager(self):
        """启动任务管理器"""
        self.task_manager.start()
        self.status_message.set("任务管理器已启动")

    def run(self):
        """运行GUI"""
        self.root.mainloop()

    def on_closing(self):
        """窗口关闭事件"""
        if messagebox.askokcancel("退出", "确定要退出任务管理器吗？"):
            self.update_running = False
            if self.task_manager.is_running:
                self.task_manager.stop()
            self.root.destroy()



    # =============== 任务函数定义 ===============
    def soldier_training(self, winter):
        return winter.soldier_training()

    def earth_core(self, winter):
        """数据处理任务"""
        return winter.earth_core()

    def store_purchase(self, winter):
        """数据处理任务"""
        return winter.store_purchase()

    def warehouse_reward(self, winter):
        return winter.warehouse_reward()

    def adventure_gain(self, winter):
        """数据存储任务"""
        return winter.adventure_gains()

    def pet_treasure(self, winter):
        return winter.pet_treasure()

    def crystal_lab(self, winter):
        return winter.crystal_lab()

    def bank_deposit(self, winter):
        return winter.deposit()

    def commander_reward(self, winter):
        return winter.commander_reward()

    def daily_reward(self, winter):
        return self.winter.charge_reward()

    def hero_recruit(self, winter):
        return winter.hero_recruit()

    def mining(self, winter):
        return winter.mining()

    def monster_hunt(self, winter):
        return winter.monster_hunt()

    def monster_hunter(self, winter):
        return winter.monster_hunter()

    def alliance_donating(self, winter):
        return winter.alliance_donating()

    def alliance_treasure(self, winter):
        return winter.alliance_treasure()

    def performance_analysis_task(self, winter):
        """性能分析任务"""
        return winter.world_help()

    def island_gain(self, winter):
        """用户认证任务"""
        return winter.island_gain()

    def check_hunter_status(self, winter):
        """数据加密任务"""
        return winter.check_hunter_status()

    def set_alliance_mine(self, winter):
        return winter.set_alliance_mine()

    def alliance_mobilization(self, winter):
        """数据导出任务"""
        return winter.alliance_mobilization()

    def read_mails(self, winter):
        """数据导出任务"""
        return winter.read_mails()


def main():
    """主函数"""

    # 创建并运行GUI
    gui = TaskManagerGUI(device_id=0, mmm_path=r'E:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe')
    print("任务管理器GUI已启动，资源占用已优化")
    print("按Ctrl+C或关闭窗口退出")

    try:
        gui.run()
    except KeyboardInterrupt:
        print("正在关闭任务管理器...")
        gui.root.destroy()


if __name__ == "__main__":
    main()