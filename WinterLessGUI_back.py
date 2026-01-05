import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
import threading

# 导入您的TaskQueueManager类
from TaskQueueManager import GameTaskManager, ScheduleType
from MumuManager import MumuGameAutomator
from TaskList import WinterLess


class FunctionControlGUI:
    def __init__(self, root, device_id: int, mmm_path: str = r'C:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe'):
        self.root = root

        # 配置文件路径
        self.config_file = "game_tasks_config.json"

        # 初始化游戏自动化器和任务管理器
        self.automator = MumuGameAutomator(mumu_device=device_id, game_package="com.gof.china",
                                           mmm_path=mmm_path)
        self.automator.start_game()
        self.winter = WinterLess(self.automator)
        self.task_manager = GameTaskManager(self.winter, self.automator.adb.device_name)
        self.root.title(self.automator.adb.device_name)

        # 任务定义：每个功能对应的任务配置
        self.task_definitions = {
            # 核心功能组
            "城镇内": {
                "练兵": {
                    "func": self.soldier_training,
                    "schedule_type": ScheduleType.INTERVAL,
                    "interval_seconds": 1800,  # 30分钟
                    "immediate": False,
                    "requires_game": True
                },
                "仓库收益": {
                    "func": self.warehouse_reward,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "26 * * * *",
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
                    "func": self.store_purchase,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "39 3 * * *",
                    "immediate": False,
                    "requires_game": True
                },
                "游荡商人": {
                    "func": self.earth_core,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "39 3 * * *",
                    "requires_game": True
                },
                "免费招募": {
                    "func": self.hero_recruit,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "11 * * * *",
                    "requires_game": True
                }
            },
            # 网络功能组
            "野外": {
                "采集": {
                    "func": self.mining,
                    "schedule_type": ScheduleType.INTERVAL,
                    "interval_seconds": 590,  # 10分钟
                    "requires_game": True
                },
                "自动上车": {
                    "func": self.monster_hunt,
                    "schedule_type": ScheduleType.INTERVAL,
                    "interval_seconds": 15,  # 5分钟
                    "requires_game": True
                },
                "自动打巨兽": {
                    "func": self.monster_hunter,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "50 */2 * * *",
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
                    "interval_seconds": 2,
                    "immediate": True,
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
                    "immediate": False,
                    "requires_game": True
                },
                "更新盟矿": {
                    "func": self.set_alliance_mine,
                    "schedule_type": ScheduleType.CRON,
                    "cron_expression": "40 7,19 * * *",
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

        # 功能组结构
        self.function_groups = {}
        for group_name, functions in self.task_definitions.items():
            self.function_groups[group_name] = list(functions.keys())

        # 默认配置
        self.default_config = self.create_default_config()

        # 获取屏幕尺寸并设置窗口大小
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 设置窗口大小为1920x1080
        window_width = 1024
        window_height = 768

        # 计算窗口位置使其居中
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 存储复选框状态和对应的任务ID
        self.checkbox_vars = {}
        self.task_ids = {}  # 存储功能名称到任务ID的映射

        # 加载配置
        self.current_config = self.load_config()

        # 设置界面布局
        self.setup_ui()

        # 启动任务管理器
        self.task_manager.start()

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

    def create_default_config(self):
        """创建默认配置"""
        config = {}
        for group_name, functions in self.task_definitions.items():
            config[group_name] = {}
            for func_name in functions:
                # 默认情况下，大部分功能不启用
                config[group_name][func_name] = False
        return config

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
                            requires_game=task_config.get("requires_game", True),
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

    def pause_or_resume_task(self):
        if self.task_manager.pause_event.is_set():
            self.task_manager.pause()
            self.pause_btn.config(text='▶ 恢复', bg='#4CAF50')
        else:
            self.task_manager.resume()
            self.pause_btn.config(text='⏸ 暂停', bg='#9E9E9E')

    def stop_or_start_task(self):
        if self.task_manager.pause_event.is_set():
            self.task_manager.stop()
            self.stop_btn.config(text='▶ 启动', bg='#4CAF50')
        else:
            self.task_manager.start()
            self.stop_btn.config(text='⏹ 停止', bg='#9E9E9E')

    def on_checkbox_toggle(self, function, group):
        """复选框状态改变时的回调"""
        var_name = f"{group}_{function}"
        enabled = self.checkbox_vars[var_name].get()
        state = "启用" if enabled else "禁用"

        # 更新状态标签
        self.status_label.config(text=f"{group} - {function}: {state}", fg='blue')

        # 添加或移除任务
        self.add_or_remove_task(group, function, enabled)

        # 自动保存配置
        self.auto_save_config()

        # 更新统计信息
        self.update_stats()

    def auto_save_config(self):
        """自动保存配置到文件"""

        # 在单独的线程中保存配置，避免阻塞UI
        def save_thread():
            if self.save_config():
                # 更新状态显示
                self.root.after(100, lambda: self.status_label.config(
                    text="配置已自动保存",
                    fg='green'
                ))

        threading.Thread(target=save_thread, daemon=True).start()

    def setup_ui(self):
        # 设置字体
        self.title_font = ("Microsoft YaHei", 18, "bold")
        self.group_font = ("Microsoft YaHei", 14, "bold")
        self.large_font = ("Microsoft YaHei", 12)
        self.small_font = ("Microsoft YaHei", 10)

        # 1. 顶部区域 - 标题和状态
        top_frame = tk.Frame(self.root, height=100, bg='#f0f0f0')
        
        top_frame.pack(side=tk.TOP, fill=tk.X)
        top_frame.pack_propagate(False)  # 固定高度

        # 配置文件状态
        config_status = "已加载配置文件" if os.path.exists(self.config_file) else "使用默认配置"
        config_color = "green" if os.path.exists(self.config_file) else "orange"

        title_frame = tk.Frame(top_frame, bg='#f0f0f0')
        title_frame.pack(side=tk.LEFT, padx=40, pady=0)

        title_label = tk.Label(title_frame, text=self.automator.adb.device_name,
                               font=self.title_font,
                               bg='#f0f0f0')
        title_label.pack(anchor='w')
        # 任务管理器状态
        self.task_status_label = tk.Label(title_frame, text="任务管理器: 运行中",
                                          font=("Microsoft YaHei", 10),
                                          bg='#f0f0f0', fg='green')
        self.task_status_label.pack(anchor='w')

        # 状态标签
        self.status_label = tk.Label(top_frame, text="系统就绪 | 等待用户操作",
                                     font=self.small_font,
                                     bg='#f0f0f0', fg='green')
        self.status_label.pack(side=tk.RIGHT, padx=40, pady=20)

        self.pause_btn = tk.Button(top_frame, text="⏸ 暂停",
                                   command=self.pause_or_resume_task,
                                   font=self.large_font,
                                   width=12, height=2,
                                   bg='#9E9E9E', fg='white')
        self.pause_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # 2. 中间主区域
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=False, padx=40, pady=20)

        # 第一行：核心功能和网络功能
        row1_frame = tk.Frame(main_frame, bg='white')
        row1_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 20))

        # 第二行：辅助功能、安全功能和工具功能
        row2_frame = tk.Frame(main_frame, bg='white')
        row2_frame.pack(fill=tk.BOTH, expand=True)

        # 配置第一行的权重
        row1_frame.grid_columnconfigure(0, weight=3)  # 核心功能占3份
        row1_frame.grid_columnconfigure(1, weight=1)  # 网络功能占1份

        # 配置第二行的权重
        row2_frame.grid_columnconfigure(0, weight=2)  # 辅助功能占2份
        row2_frame.grid_columnconfigure(1, weight=1)  # 安全功能占1份
        row2_frame.grid_columnconfigure(2, weight=1)  # 工具功能占1份

        # 创建功能组
        self.create_group(row1_frame, "城镇内", self.function_groups["城镇内"],
                          column=0, row=0, is_large=True, columns=2)

        self.create_group(row1_frame, "野外", self.function_groups["野外"],
                          column=1, row=0, is_large=False, columns=2)

        self.create_group(row2_frame, "联盟任务", self.function_groups["联盟任务"],
                          column=0, row=0, is_large=True, columns=2)

        self.create_group(row2_frame, "其他", self.function_groups["其他"],
                          column=1, row=0, is_large=False, columns=2)

        self.create_group(row2_frame, "阶段性任务", self.function_groups["阶段性任务"],
                          column=2, row=0, is_large=False, columns=2)

        # 3. 底部区域 - 控制按钮和信息
        bottom_frame = tk.Frame(self.root, height=100, bg='#f0f0f0')
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        bottom_frame.pack_propagate(False)  # 固定高度

        # 左侧：任务信息
        task_info_frame = tk.Frame(bottom_frame, bg='#f0f0f0')
        task_info_frame.pack(side=tk.LEFT, fill=tk.Y, padx=40, pady=10)

        self.active_tasks_label = tk.Label(task_info_frame, text="活动任务: 0",
                                           font=self.small_font, bg='#f0f0f0', fg='blue')
        self.active_tasks_label.pack(anchor='w', pady=2)

        self.next_task_label = tk.Label(task_info_frame, text="下一个任务: 无",
                                        font=self.small_font, bg='#f0f0f0')
        self.next_task_label.pack(anchor='w', pady=2)

        # 配置文件信息
        config_info_frame = tk.Frame(bottom_frame, bg='#f0f0f0')
        config_info_frame.pack(side=tk.LEFT, fill=tk.Y, padx=40, pady=10)

        self.config_file_label = tk.Label(config_info_frame, text=f"配置文件: {self.config_file}",
                                          font=("Microsoft YaHei", 9), bg='#f0f0f0')
        self.config_file_label.pack(anchor='w', pady=2)

        self.config_status_label = tk.Label(config_info_frame, text=config_status,
                                            font=("Microsoft YaHei", 9), bg='#f0f0f0', fg=config_color)
        self.config_status_label.pack(anchor='w', pady=2)

        # 中间区域：操作按钮
        select_frame = tk.Frame(bottom_frame, bg='#f0f0f0')
        select_frame.pack(side=tk.LEFT, expand=True, pady=10)

        select_all_btn = tk.Button(select_frame, text="启用所有",
                                   command=self.select_all,
                                   font=self.small_font,
                                   width=6, height=1,
                                   bg='#4CAF50', fg='white')
        select_all_btn.pack(side=tk.LEFT, padx=5, pady=5)

        deselect_all_btn = tk.Button(select_frame, text="禁用所有",
                                     command=self.deselect_all,
                                     font=self.small_font,
                                     width=6, height=1,
                                     bg='#FF9800', fg='white')
        deselect_all_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # 右侧：任务管理器控制
        action_frame = tk.Frame(bottom_frame, bg='#f0f0f0')
        action_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=40, pady=10)

        self.task_stats_btn = tk.Button(action_frame, text="任务统计",
                                        command=self.show_task_stats,
                                        font=self.small_font,
                                        width=6, height=1,
                                        bg='#9C27B0', fg='white')
        self.task_stats_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        self.stop_btn = tk.Button(action_frame, text="⏹ 停止",
                                   command=self.stop_or_start_task,
                                   font=self.small_font,
                                   width=6, height=1,
                                   bg='#DC143C', fg='white')
        self.stop_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # 初始化复选框状态
        self.initialize_checkboxes()

        # 更新统计信息
        self.update_stats()

        # 启动定时更新任务状态
        self.update_task_status()

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_group(self, parent, group_name, functions, column, row, is_large, columns=2):
        """创建功能组，支持多列布局"""
        # 组框架
        group_frame = tk.LabelFrame(parent, text=group_name,
                                    font=self.group_font,
                                    padx=20, pady=15,
                                    bg='white', bd=2, relief=tk.GROOVE)
        group_frame.grid(row=row, column=column, sticky='nsew', padx=10, pady=10)

        # 配置组框架的网格权重
        for i in range(columns):
            group_frame.grid_columnconfigure(i, weight=1)

        # 创建复选框并分配到多列
        func_font = self.large_font if is_large else self.small_font
        func_count = len(functions)

        # 计算每列应该有多少个项目
        items_per_column = (func_count + columns - 1) // columns

        for i, func in enumerate(functions):
            var = tk.BooleanVar()
            self.checkbox_vars[f"{group_name}_{func}"] = var

            # 确定当前项目应该放在哪一列哪一行
            col = i // items_per_column
            row_in_col = i % items_per_column

            # 创建复选框
            checkbox = tk.Checkbutton(group_frame, text=func,
                                      variable=var,
                                      command=lambda f=func, g=group_name: self.on_checkbox_toggle(f, g),
                                      font=func_font,
                                      bg='white',
                                      anchor='w',
                                      padx=10, pady=8)
            checkbox.grid(row=row_in_col, column=col, sticky='w', padx=15)

    def initialize_checkboxes(self):
        """根据配置文件初始化复选框状态，并添加初始任务"""
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

    def update_stats(self):
        """更新统计信息"""
        enabled = sum(1 for var in self.checkbox_vars.values() if var.get())
        disabled = len(self.checkbox_vars) - enabled

        # 更新底部标签
        if hasattr(self, 'enabled_count'):
            self.enabled_count.config(text=f"已启用: {enabled}", fg='green')
            self.disabled_count.config(text=f"已禁用: {disabled}", fg='red')
            self.total_count.config(text=f"总数: {len(self.checkbox_vars)}")

    def update_task_status(self):
        """定期更新任务状态显示"""
        def execute_in_background():
            try:
                # 获取任务管理器状态
                # stats = self.task_manager.get_stats()

                # 更新活动任务数
                active_tasks = sum(1 for task in self.task_manager.list_tasks() if task.get('enabled', False))
                self.active_tasks_label.config(text=f"活动任务: {active_tasks}")

                # 更新下一个任务
                upcoming = self.task_manager.get_upcoming_tasks(1)
                if upcoming:
                    next_task = upcoming[0]
                    task_name = next_task['name']
                    seconds_until = int(next_task['seconds_until'])
                    self.next_task_label.config(
                        text=f"下一个任务: {task_name} ({seconds_until}秒后)"
                    )
                else:
                    self.next_task_label.config(text="下一个任务: 无")

                # 更新任务管理器状态
                if self.task_manager.is_running:
                    self.task_status_label.config(text="任务管理器: 运行中", fg='green')
                else:
                    self.task_status_label.config(text="任务管理器: 已停止", fg='red')

            except Exception as e:
                print(f"更新任务状态时出错: {e}")

            # 1秒后再次更新
            self.root.after(1000, self.update_task_status)
        threading.Thread(target=execute_in_background, daemon=True).start()

    def load_config_from_file(self):
        """从配置文件重新加载配置"""
        if not os.path.exists(self.config_file):
            messagebox.showwarning("配置文件不存在",
                                   f"配置文件 {self.config_file} 不存在。\n请先保存配置或使用默认配置。")
            return

        # 确认对话框
        if not messagebox.askyesno("确认", "确定要从配置文件重新加载配置吗？\n当前未保存的更改将会丢失。"):
            return

        # 重新加载配置
        self.current_config = self.load_config()

        # 更新复选框状态
        self.initialize_checkboxes()

        # 更新状态
        self.update_stats()
        self.config_status_label.config(text="已重新加载配置文件", fg='green')
        self.status_label.config(text="配置已从文件重新加载", fg='blue')

        # 显示成功消息
        messagebox.showinfo("成功", "配置已从文件重新加载")

    def show_task_stats(self):
        """显示任务统计信息"""
        try:
            # 创建统计窗口
            stats_window = tk.Toplevel(self.root)
            stats_window.title("任务统计信息")
            stats_window.geometry("800x600")

            # 居中显示
            stats_window.update_idletasks()
            x = (self.root.winfo_width() - stats_window.winfo_width()) // 2 + self.root.winfo_x()
            y = (self.root.winfo_height() - stats_window.winfo_height()) // 2 + self.root.winfo_y()
            stats_window.geometry(f"+{x}+{y}")

            # 标题
            tk.Label(stats_window, text="任务管理器统计信息",
                     font=("Microsoft YaHei", 16, "bold")).pack(pady=10)

            # 统计信息框架
            stats_frame = tk.Frame(stats_window)
            stats_frame.pack(fill=tk.X, padx=20, pady=10)

            # 基本信息
            stats = self.task_manager.get_stats()
            tk.Label(stats_frame, text=f"运行时间: {stats.get('runtime_formatted', 'N/A')}",
                     font=self.small_font).pack(anchor='w', pady=2)
            tk.Label(stats_frame, text=f"总任务数: {stats.get('total_tasks', 0)}",
                     font=self.small_font).pack(anchor='w', pady=2)
            tk.Label(stats_frame, text=f"已执行任务: {stats.get('total_executed', 0)}",
                     font=self.small_font).pack(anchor='w', pady=2)
            tk.Label(stats_frame, text=f"已完成: {stats.get('total_completed', 0)}",
                     font=self.small_font, fg='green').pack(anchor='w', pady=2)
            tk.Label(stats_frame, text=f"已失败: {stats.get('total_failed', 0)}",
                     font=self.small_font, fg='red').pack(anchor='w', pady=2)
            tk.Label(stats_frame, text=f"已跳过: {stats.get('total_skipped', 0)}",
                     font=self.small_font).pack(anchor='w', pady=2)

            # 创建切换标签和任务列表的容器
            list_container = tk.Frame(stats_window)
            list_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

            # 创建切换标签的框架（与任务列表同级）
            switch_frame = tk.Frame(list_container)
            switch_frame.pack(fill=tk.X, pady=(0, 10))

            # 添加切换标签
            switch_label = tk.Label(
                switch_frame,
                text="历史任务",
                font=("Microsoft YaHei", 12, "bold"),
                fg="blue",
                cursor="hand2"  # 添加手型光标提示可点击
            )
            switch_label.pack(anchor='w')

            # 绑定点击事件
            switch_label.bind("<Button-1>", lambda e: self.toggle_task_list(list_frame2))

            # 创建带滚动条的任务列表框架
            list_frame2 = tk.Frame(list_container)
            list_frame2.pack(fill=tk.BOTH, expand=True)

            # 创建Treeview
            columns2 = ("last_run", "name", "type", "status", "result", "duration", "reason")
            tree = ttk.Treeview(list_frame2, columns=columns2, show="headings")

            # 定义列
            tree.heading("last_run", text="上次执行")
            tree.heading("name", text="任务名称")
            tree.heading("type", text="任务类型")
            tree.heading("status", text="状态")
            tree.heading("result", text="执行结果")
            tree.heading("duration", text="时长")
            tree.heading("reason", text="原因")

            tree.column("last_run", width=150)
            tree.column("name", width=100)
            tree.column("type", width=50)
            tree.column("status", width=50)
            tree.column("result", width=200)
            tree.column("duration", width=50)
            tree.column("reason", width=50)

            # 添加滚动条
            scrollbar = ttk.Scrollbar(list_frame2, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # 添加任务数据
            tasks = self.task_manager.get_history(50)

            for task in tasks:
                reason = task.get('error') if task.get('error') else task.get('reason', '')
                tree.insert("", "end", values=(
                    task.get('timestamp', ''),
                    task.get('task_name', ''),
                    task.get('schedule_type', ''),
                    task.get('status', ''),
                    task.get('result', ''),
                    int(task.get('duration', 0)),
                    task.get('reason', '')
                ))

            # 保存treeview的引用以便在切换时使用
            list_frame2.treeview = tree
            list_frame2.scrollbar = scrollbar

            # 添加切换标签
            switch_label = tk.Label(
                switch_frame,
                text="任务列表",
                font=("Microsoft YaHei", 12, "bold"),
                fg="blue",
                cursor="hand2"  # 添加手型光标提示可点击
            )
            switch_label.pack(anchor='w')

            # 绑定点击事件
            switch_label.bind("<Button-1>", lambda e: self.toggle_task_list(list_frame))

            # 创建带滚动条的任务列表框架
            list_frame = tk.Frame(list_container)
            list_frame.pack(fill=tk.BOTH, expand=True)

            # 创建Treeview
            columns = ("name", "status", "next_run", "executions", "last_result")
            tree = ttk.Treeview(list_frame, columns=columns, show="headings")

            # 定义列
            tree.heading("name", text="任务名称")
            tree.heading("status", text="状态")
            tree.heading("next_run", text="下次执行")
            tree.heading("executions", text="执行次数")
            tree.heading("last_result", text="最后一次执行结果")

            tree.column("name", width=100)
            tree.column("status", width=50)
            tree.column("next_run", width=150)
            tree.column("executions", width=50)
            tree.column("last_result", width=200)

            # 添加滚动条
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # 添加任务数据
            tasks = self.task_manager.list_tasks()

            for task in tasks:
                status = "启用" if task.get('enabled', False) else "禁用"
                tree.insert("", "end", values=(
                    task.get('name', 'N/A'),
                    status,
                    task.get('next_run', 'N/A'),
                    task.get('execution_count', 0),
                    task.get('last_result', 'N/A')
                ))

            # 保存treeview的引用以便在切换时使用
            list_frame.treeview = tree
            list_frame.scrollbar = scrollbar

            # 关闭按钮
            tk.Button(stats_window, text="关闭",
                      command=stats_window.destroy,
                      font=self.small_font,
                      width=15, bg='#2196F3', fg='white').pack(pady=20)

        except Exception as e:
            messagebox.showerror("错误", f"获取任务统计信息时出错: {e}")

    def toggle_task_list(self, list_frame):
        """切换任务列表的显示/隐藏状态"""
        if list_frame.winfo_ismapped():
            # 如果当前是显示状态，则隐藏
            list_frame.pack_forget()
        else:
            # 如果当前是隐藏状态，则显示
            list_frame.pack(fill=tk.BOTH, expand=True)

    def select_all(self):
        """启用所有功能"""
        for var in self.checkbox_vars.values():
            var.set(True)

        # 添加所有任务
        for group_name, functions in self.function_groups.items():
            for func_name in functions:
                self.add_or_remove_task(group_name, func_name, True)

        self.status_label.config(text="已启用所有功能", fg='green')
        self.update_stats()
        self.auto_save_config()

    def deselect_all(self):
        """禁用所有功能"""
        for var in self.checkbox_vars.values():
            var.set(False)

        # 移除所有任务
        for group_name, functions in self.function_groups.items():
            for func_name in functions:
                self.add_or_remove_task(group_name, func_name, False)

        self.status_label.config(text="已禁用所有功能", fg='orange')
        self.update_stats()
        self.auto_save_config()

    def reset_config(self):
        """重置为默认配置"""
        if not messagebox.askyesno("确认", "确定要重置为默认配置吗？\n当前未保存的更改将会丢失。"):
            return

        # 使用默认配置
        self.current_config = self.create_default_config()

        # 移除所有现有任务
        for group_name, functions in self.function_groups.items():
            for func_name in functions:
                self.add_or_remove_task(group_name, func_name, False)

        # 更新复选框状态
        self.initialize_checkboxes()

        # 更新状态
        self.update_stats()
        self.config_status_label.config(text="已重置为默认配置", fg='orange')
        self.status_label.config(text="已重置为默认配置", fg='blue')

        # 自动保存
        self.auto_save_config()

        # 显示消息
        messagebox.showinfo("重置成功", "已重置为默认配置")

    def apply_config(self):
        """应用配置（兼容旧版本）"""
        self.auto_save_config()
        messagebox.showinfo("成功", "配置已自动保存")

    def on_closing(self):
        """关闭窗口前的确认"""
        # 停止任务管理器
        self.task_manager.stop()

        # 保存配置
        self.save_config()

        if messagebox.askokcancel("退出系统", "确定要退出游戏任务控制系统吗？"):
            self.root.destroy()


def main():
    root = tk.Tk()
    app = FunctionControlGUI(root)

    # 设置窗口图标（如果有的话）
    try:
        root.iconbitmap('icon.ico')  # Windows系统
    except:
        pass

    # 启动主循环
    root.mainloop()


if __name__ == "__main__":
    main()