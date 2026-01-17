# task_manager_gui_optimized.py - 优化版任务管理器图形界面
import json
import os
import random
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, scrolledtext, filedialog

from MumuManager import MumuGameAutomator, ADBController
from TaskList import WinterLess
from TaskQueueManager import GameTaskManager, ScheduleType


class TaskManagerGUI(tk.Tk):
    """优化版任务管理器图形界面"""

    def __init__(self):
        super().__init__()

        # 动态创建任务函数
        self._create_task_methods()

        self.mmm_path = ''

        # 构建主框架
        self.title('无尽解脱器')
        self.geometry("1000x700")
        self.colors = {}

        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建Notebook（标签页容器）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建底部控制面板
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        # 文件路径输入框
        self.file_path_var = tk.StringVar()
        ttk.Label(control_frame, text="MumuManager路径:").pack(side=tk.LEFT, padx=(0, 5))
        self.file_entry = ttk.Entry(control_frame, textvariable=self.file_path_var, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 浏览按钮
        ttk.Button(
            control_frame,
            text="配置mumu地址",
            command=self.browse_file
        ).pack(side=tk.LEFT, padx=2)

        # 执行按钮
        ttk.Button(
            control_frame,
            text="连接mumu",
            command=self.connect_mumu
        ).pack(side=tk.LEFT, padx=2)

        # 清空按钮
        self.pause_all_btn = ttk.Button(
            control_frame,
            text="⏸ 暂停全部",
            command=self.pause_resume_all
        )
        self.pause_all_btn.pack(side=tk.LEFT, padx=2)

        # 状态标签
        self.status_label = ttk.Label(control_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.game_config = "game_tasks_config.json"
        self.sys_config = "sys_config.json"

        # 设置样式
        self.setup_styles()

        # 缓存和状态
        self.task_id_map = {}  # item_id -> task_id
        self.selected_task_id = None

        # 更新控制
        self.update_interval = 2000  # 2秒更新一次
        self.partial_updates = True  # 启用部分更新

        self.task_ids = {}  # 存储功能名称到任务ID的映射

        # 从JSON文件加载任务定义并立即转换格式
        raw_task_definitions = self.load_task_definitions_from_json()
        self.task_definitions = self._convert_task_definitions(raw_task_definitions)

        self.function_groups = {}
        for group_name, functions in self.task_definitions.items():
            self.function_groups[group_name] = list(functions.keys())

        self.default_config = self.create_default_config()

        # 创建界面
        # self.create_widgets()
        self.all_paused = False

        #
        self.tab_controls = {}  # 新增：存储tab_name -> 控件字典
        self.current_tabs = {}  # 存储当前打开的tab信息

        # 启动界面更新
        self.start_update_loop()

        # 启动界面加载
        self.after(1000, self.game_init)

        # 窗口关闭事件处理
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.run()

    def game_init(self):
        try:
            # 加载配置文件
            config_file = self.sys_config
            if not os.path.exists(config_file):
                return False
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 处理meta data并得到mumu_path
            meta = config_data.pop('_metadata', None)
            if 'mumu_path' in meta:
                mmm_path = meta['mumu_path']
                self.file_path_var.set(mmm_path)
                self.mmm_path = mmm_path
            else:
                return False
            items = ['id', 'name', 'tab_name', 'state']
            for value in config_data.values():
                for item in items:
                    if item not in value:
                        return False
            for index, tab_data in config_data.items():
                if tab_data['state']:
                    self.create_tab(tab_data)
                    self.initialize_checkboxes(tab_data['tab_name'])
        finally:
            pass

    def setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        style.theme_use('clam')  # 可以使用 'clam', 'alt', 'default', 'classic'

        # 配置标签页样式
        style.configure('TNotebook.Tab', padding=[10, 5])

        # 配置按钮样式
        style.configure('TButton', padding=5)

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

    def create_widgets(self, parent, data: dict):
        """创建界面组件"""

        # 构建自己的数据块
        tab_name = data['tab_name']
        name = data['name']
        device_id = data['id']
        self.tab_controls[tab_name] = {}
        self.tab_controls[tab_name]['update_running'] = True
        self.tab_controls[tab_name]['last_history_hash'] = 0
        self.tab_controls[tab_name]['last_upcoming_hash'] = 0
        self.tab_controls[tab_name]['last_update_time'] = 0
        self.tab_controls[tab_name]['current_config'] = self.load_config(tab_name)
        self.tab_controls[tab_name]['automator'] = MumuGameAutomator(mumu_device=device_id,
                                                                     game_package="com.gof.china",
                                                                     mmm_path=self.mmm_path)
        automator = self.tab_controls[tab_name]['automator']
        automator.start_game()
        self.tab_controls[tab_name]['winter'] = WinterLess(automator)
        winter = self.tab_controls[tab_name]['winter']
        self.tab_controls[tab_name]['task_manager'] = GameTaskManager(winter, automator.adb.device_name)

        self.tab_controls[tab_name]['checkbox_vars'] = {}

        # 创建主框架
        tab_frame = ttk.Frame(parent, padding="5")
        tab_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        tab_frame.columnconfigure(1, weight=1)
        tab_frame.rowconfigure(2, weight=1)

        # 标题栏
        title_frame = ttk.Frame(tab_frame)
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky=(tk.W, tk.E))

        title_label = ttk.Label(
            title_frame,
            text=f"📋 {name}",
            font=("Arial", 14, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)

        # 状态标签
        status_label = ttk.Label(
            title_frame,
            text="状态: 运行中",
            foreground=self.colors["success"]
        )
        status_label.grid(row=0, column=1, padx=20)
        self.tab_controls[tab_name]['status_label'] = status_label

        # 控制按钮
        control_frame = ttk.Frame(title_frame)
        control_frame.grid(row=0, column=2, sticky=tk.E)

        pause_btn = ttk.Button(
            control_frame,
            text="⏸ 暂停",
            command=lambda t=tab_name: self.toggle_pause(t),
            width=8
        )
        pause_btn.grid(row=0, column=0, padx=2)
        self.tab_controls[tab_name]['pause_btn'] = pause_btn

        stop_btn = ttk.Button(
            control_frame,
            text="⏹ 停止",
            command=lambda t=tab_name: self.stop_manager(t),
            width=8
        )
        stop_btn.grid(row=0, column=1, padx=2)
        self.tab_controls[tab_name]['stop_btn'] = stop_btn

        # 统计信息栏（简化版）
        stats_frame = ttk.LabelFrame(tab_frame, text="📊 统计", padding="5")
        stats_frame.grid(row=1, column=0, columnspan=2, pady=(0, 5), sticky=(tk.W, tk.E))

        # 创建关键统计标签
        stats_labels = {}
        stats_items = [
            ("运行:", "runtime_formatted"),
            ("任务:", "total_tasks"),
            ("成功:", "total_completed"),
            ("失败:", "total_failed"),
        ]

        for i, (label_text, key) in enumerate(stats_items):
            j = int(i) * 2
            ttk.Label(stats_frame, text=label_text, font=("Arial", 9)).grid(
                row=0, column=j, sticky=tk.W, padx=(5, 2), pady=2
            )
            stats_labels[key] = ttk.Label(
                stats_frame,
                text="0",
                font=("Arial", 9)
            )
            stats_labels[key].grid(
                row=0, column=j + 1, sticky=tk.W, padx=(0, 10), pady=2
            )
        self.tab_controls[tab_name]['stats_labels'] = stats_labels

        # 创建主内容区域
        notebook = ttk.Notebook(tab_frame)
        notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 任务列表标签页
        tasks_tab = ttk.Frame(notebook)
        notebook.add(tasks_tab, text="📋 任务")

        # 任务列表工具栏
        tasks_toolbar = ttk.Frame(tasks_tab)
        tasks_toolbar.pack(fill=tk.X, padx=5, pady=(5, 2))

        self.create_group(tasks_toolbar, tab_name, "城镇内", self.function_groups["城镇内"],
                          column=0, row=0, columns=2)
        self.create_group(tasks_toolbar, tab_name, "野外", self.function_groups["野外"],
                          column=1, row=0, columns=2)
        self.create_group(tasks_toolbar, tab_name, "联盟任务", self.function_groups["联盟任务"],
                          column=0, row=1, columns=2)
        self.create_group(tasks_toolbar, tab_name, "其他", self.function_groups["其他"],
                          column=1, row=1, columns=2)
        self.create_group(tasks_toolbar, tab_name, "阶段性任务", self.function_groups["阶段性任务"],
                          column=2, row=1, columns=2)

        # 详情标签页
        details_tab = ttk.Frame(notebook)
        notebook.add(details_tab, text="📄 详情")

        # 详情内容框架
        details_frame = ttk.Frame(details_tab)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 详情文本区域（使用只读文本框，比多个标签更高效）
        details_text = scrolledtext.ScrolledText(
            details_frame,
            width=40,
            height=20,
            font=("Consolas", 9),
            state="disabled"
        )
        details_text.pack(fill=tk.BOTH, expand=True)
        self.tab_controls[tab_name]['details_text'] = details_text

        # 即将执行标签页
        upcoming_tab = ttk.Frame(notebook)
        notebook.add(upcoming_tab, text="⏰ 即将执行")

        # 即将执行列表
        upcoming_tree = ttk.Treeview(
            upcoming_tab,
            columns=("name", "next_run", "seconds_until"),
            show="headings",
            height=15
        )

        # 定义列
        upcoming_tree.heading("name", text="任务名称")
        upcoming_tree.heading("next_run", text="执行时间")
        upcoming_tree.heading("seconds_until", text="剩余时间")

        # 设置列宽
        upcoming_tree.column("name", width=200, stretch=True)
        upcoming_tree.column("next_run", width=150)
        upcoming_tree.column("seconds_until", width=100)

        # 添加滚动条
        upcoming_scrollbar = ttk.Scrollbar(upcoming_tab, orient=tk.VERTICAL, command=upcoming_tree.yview)
        upcoming_tree.configure(yscrollcommand=upcoming_scrollbar.set)

        # 布局
        upcoming_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        upcoming_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.tab_controls[tab_name]['upcoming_tree'] = upcoming_tree

        # 历史记录标签页（按需加载）
        history_tab = ttk.Frame(notebook)
        notebook.add(history_tab, text="📜 历史")

        # 历史记录工具栏
        history_toolbar = ttk.Frame(history_tab)
        history_toolbar.pack(fill=tk.X, padx=5, pady=(5, 2))

        ttk.Button(
            history_toolbar,
            text="🔄 刷新",
            command=lambda t=tab_name: self.refresh_history(t),
            width=8
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            history_toolbar,
            text="🗑️ 清空",
            command=lambda t=tab_name: self.clear_history(t),
            width=8
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            history_toolbar,
            text="💾 导出",
            command=lambda t=tab_name: self.export_history(t),
            width=8
        ).pack(side=tk.LEFT)

        # 历史记录文本框（按需加载）
        history_text = None

        # 底部状态栏
        status_bar = ttk.Frame(tab_frame)
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))

        status_message = tk.StringVar(value="就绪")
        ttk.Label(
            status_bar,
            textvariable=status_message,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Arial", 9)
        ).pack(fill=tk.X, ipady=2)
        self.tab_controls[tab_name]['history_tab'] = history_tab
        self.tab_controls[tab_name]['history_text'] = history_text
        self.tab_controls[tab_name]['status_message'] = status_message

    def create_group(self, parent, tab_name: str, group_name, functions, column, row, padx=5, pady=5, columns=2):
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
            self.tab_controls[tab_name]['checkbox_vars'][f"{group_name}_{func}"] = var

            col = i // items_per_column
            row_in_col = i % items_per_column

            # 创建复选框
            checkbox = ttk.Checkbutton(
                group_frame,
                text=func,
                variable=var,
                command=lambda t=tab_name, f=func, g=group_name: self.on_checkbox_toggle(t, f, g)
            )
            checkbox.grid(row=row_in_col, column=col, sticky='w', padx=15)

    def start_update_loop(self):
        """启动更新循环"""
        self.update_display()

    def update_display(self):
        """更新显示"""
        running_count = 0  # 统计有多少个task_manager处于running状态
        for tab_name, value in self.tab_controls.items():
            update_running = value.get('update_running', True)
            last_update_time = value.get('last_update_time', 0)
            last_upcoming_hash = value.get('last_upcoming_hash', 0)
            task_manager = value.get('task_manager', None)
            if task_manager is None:
                continue

            # 检查task_manager是否处于running状态（即未暂停）
            if task_manager.is_running and task_manager.pause_event.is_set():
                running_count += 1

            if not update_running:
                continue

            try:
                current_time = time.time()

                # 基本状态更新（每次都需要）
                self.update_basic_status(tab_name)

                # 任务列表更新（2秒一次）
                if current_time - last_update_time > 2:
                    # self.update_tasks_list()
                    self.tab_controls[tab_name]['last_update_time'] = current_time

                # 即将执行列表更新（5秒一次）
                if current_time - last_upcoming_hash > 5:
                    self.update_upcoming_list(tab_name)
                    # self.tab_controls[tab_name]['last_upcoming_hash'] = current_time

            except Exception as e:
                # 减少错误输出频率
                if random.random() < 0.1:  # 10%概率输出错误
                    print(f"更新错误: {e}")

        # 根据实际running状态更新按钮文本
        if running_count > 0:
            # 还有task_manager在running，显示"暂停全部"
            self.pause_all_btn.config(text="⏸ 暂停全部")
        else:
            # 所有task_manager都已暂停，显示"恢复全部"
            self.pause_all_btn.config(text="▶ 恢复全部")

        # 安排下一次更新
        self.after(self.update_interval, self.update_display)

    def update_basic_status(self, tab_name: str):
        """更新基本状态"""
        task_manager = self.tab_controls[tab_name]['task_manager']
        status_label = self.tab_controls[tab_name]['status_label']
        pause_btn = self.tab_controls[tab_name]['pause_btn']
        stats_labels = self.tab_controls[tab_name]['stats_labels']

        try:
            if task_manager.is_running:
                if task_manager.pause_event.is_set():
                    status_label.config(text="状态: 运行中", foreground=self.colors["success"])
                    pause_btn.config(text="⏸ 暂停", command=lambda t=tab_name: self.toggle_pause(t))
                else:
                    status_label.config(text="状态: 已暂停", foreground=self.colors["paused"])
                    pause_btn.config(text="▶ 恢复", command=lambda t=tab_name: self.toggle_pause(t))
            else:
                status_label.config(text="状态: 已停止", foreground=self.colors["error"])
                pause_btn.config(text="▶ 启动", command=lambda t=tab_name: self.start_manager(t))

            # 更新统计信息（减少频率）
            stats = task_manager.get_stats()
            for key, label in stats_labels.items():
                if key in stats:
                    label.config(text=str(stats[key]))

        except Exception:
            pass  # 静默处理

    def update_upcoming_list(self, tab_name: str):
        """更新即将执行列表（优化版）"""

        def execute_in_background():
            try:
                # 获取即将执行的任务
                task_manager = self.tab_controls[tab_name]['task_manager']
                upcoming_tree = self.tab_controls[tab_name]['upcoming_tree']
                last_upcoming_hash = self.tab_controls[tab_name]['last_upcoming_hash']

                upcoming = task_manager.get_upcoming_tasks(limit=10)

                # 计算哈希值检查是否需要更新
                current_hash = hash(str(upcoming))
                if current_hash == last_upcoming_hash and self.partial_updates:
                    return

                # 清空列表
                upcoming_tree.delete(*upcoming_tree.get_children())

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
                    upcoming_tree.insert("", "end", values=(
                        task.get("name", "未知"),
                        task.get("next_run", "N/A"),
                        time_str
                    ))

            except Exception:
                pass  # 静默处理

        threading.Thread(target=execute_in_background, daemon=True).start()

    def refresh_history(self, tab_name: str):
        """刷新历史记录"""
        history_tab = self.tab_controls[tab_name]['history_tab']
        task_manager = self.tab_controls[tab_name]['task_manager']

        # 检查历史记录文本框是否存在
        if self.tab_controls[tab_name]['history_text'] is None:
            # 创建历史记录文本框
            history_text = scrolledtext.ScrolledText(
                history_tab,
                width=40,
                height=20,
                font=("Consolas", 9),
                state="disabled"
            )
            history_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
            # 保存引用到tab_controls中
            self.tab_controls[tab_name]['history_text'] = history_text
        else:
            # 使用已存在的历史记录文本框
            history_text = self.tab_controls[tab_name]['history_text']

        # 启用文本框进行编辑
        history_text.config(state="normal")
        history_text.delete(1.0, tk.END)

        try:
            # 获取历史记录
            history = task_manager.get_history(limit=50)

            # 添加历史记录
            for record in reversed(history):
                timestamp = record.get("timestamp", "")[:19].replace("T", " ")
                task_name = record.get("task_name", "未知")
                event = record.get("event", "")
                status = record.get("status", "")

                # 格式化行
                line = f"{timestamp} {task_name}: {event}"
                if status:
                    line += f" - {status}"
                if "result" in record:
                    line += f" - {record['result']}"
                if "error" in record:
                    line += f" - {record['error']}"
                if "reason" in record:
                    line += f" - {record['reason']}"

                history_text.insert(tk.END, line + "\n")

        except Exception as e:
            history_text.insert(tk.END, f"加载历史记录失败: {e}\n")

        # 禁用文本框
        history_text.config(state="disabled")

    def clear_history(self, tab_name: str):
        """清空历史记录"""
        history_text = self.tab_controls[tab_name]['history_text']
        task_manager = self.tab_controls[tab_name]['task_manager']
        if messagebox.askyesno("确认清空", "确定要清空历史记录吗？"):
            try:
                task_manager.history.clear()
                if history_text:
                    history_text.config(state="normal")
                    history_text.delete(1.0, tk.END)
                    history_text.config(state="disabled")
                messagebox.showinfo("成功", "历史记录已清空")
            except Exception as e:
                messagebox.showerror("错误", f"清空历史记录失败: {e}")

    def export_history(self, tab_name: str):
        """导出历史记录"""
        task_manager = self.tab_controls[tab_name]['task_manager']
        # 选择保存文件
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

        if not file_path:
            return

        try:
            # 获取历史记录
            history = task_manager.get_history(limit=1000)

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

    def on_checkbox_toggle(self, tab_name, function, group):
        """复选框状态改变时的回调"""
        var_name = f"{group}_{function}"
        checkbox_vars = self.tab_controls[tab_name]['checkbox_vars']
        enabled = checkbox_vars[var_name].get()
        # state = "启用" if enabled else "禁用"

        # 更新状态标签
        # self.status_label.config(text=f"{group} - {function}: {state}", fg='blue')

        # 添加或移除任务
        self.add_or_remove_task(tab_name, group, function, enabled)

        # 自动保存配置
        self.auto_save_config(tab_name)

        # 更新统计信息
        self.update_stats(tab_name)

    def initialize_checkboxes(self, tab_name: str):
        """根据配置文件初始化复选框状态，并添加初始任务"""
        checkbox_vars = self.tab_controls[tab_name]['checkbox_vars']
        task_manager = self.tab_controls[tab_name]['task_manager']
        current_config = self.tab_controls[tab_name]['current_config']

        def execute_in_background():
            for group_name, functions in current_config.items():
                if group_name.startswith('_'):  # 跳过元数据
                    continue

                for func_name, state in functions.items():
                    var_name = f"{group_name}_{func_name}"
                    if var_name in checkbox_vars:
                        checkbox_vars[var_name].set(state)

                        # 如果启用，添加任务到任务管理器
                        if state:
                            self.add_or_remove_task(tab_name, group_name, func_name, True)
            task_manager.start()

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

    def generate_config_name(self, tab_name: str):
        config_file = os.path.basename(self.game_config)
        dir_name = os.path.dirname(self.game_config)
        name, ext = config_file.rsplit('.', 1) if '.' in config_file else (config_file, '')
        if dir_name:
            config_file = f'{dir_name}/{name}_{tab_name}.{ext}'
        else:
            config_file = f'{dir_name}{name}_{tab_name}.{ext}'
        return config_file

    def load_config(self, tab_name: str):
        """从配置文件加载配置"""
        try:
            config_file = self.generate_config_name(tab_name)
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 移除元数据部分（如果有）
                if "_metadata" in config_data:
                    config_data.pop("_metadata")

                # 验证并修复配置文件结构
                merged_config = self.validate_config(config_data)
                # last_modified = os.path.getmtime(config_file)

                # 如果配置有变化，保存修复后的配置
                if merged_config != config_data:
                    self.tab_controls[tab_name] = {'current_config': merged_config}
                    self.save_config(tab_name)
                return merged_config
            else:
                print("配置文件不存在，创建默认配置")
                default_config = self.create_default_config()
                # 创建tab_controls条目以便保存配置
                if tab_name not in self.tab_controls:
                    self.tab_controls[tab_name] = {}
                self.tab_controls[tab_name]['current_config'] = default_config
                self.tab_controls[tab_name]['checkbox_vars'] = {}
                # 保存默认配置到文件
                self.save_config(tab_name)
                return default_config

        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            print("使用默认配置")
            return self.create_default_config()

    def save_config(self, tab_name: str):
        """保存配置到文件"""
        checkbox_vars = self.tab_controls[tab_name].get('checkbox_vars', {})
        config_file = self.generate_config_name(tab_name)
        try:
            # 准备配置数据
            config_data = {}
            for group_name in self.function_groups.keys():
                config_data[group_name] = {}
                for func_name in self.function_groups[group_name]:
                    var_name = f"{group_name}_{func_name}"
                    if var_name in checkbox_vars:
                        config_data[group_name][func_name] = checkbox_vars[var_name].get()
                    else:
                        # 如果复选框变量不存在，使用默认值
                        config_data[group_name][func_name] = self.default_config.get(group_name, {}).get(func_name,
                                                                                                         False)

            # 添加元数据
            config_data["_metadata"] = {
                "last_modified": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "total_functions": len(checkbox_vars),
                "enabled_functions": sum(1 for var in checkbox_vars.values() if var.get())
            }

            # 保存到文件
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            return True

        except Exception as e:
            print(f"保存配置文件时出错: {e}")
            return False

    def validate_config(self, config_data):
        """验证并修复配置数据的结构，保留相同部分，缺失部分用默认值补充"""
        try:
            # 创建默认配置作为基础
            default_config = self.create_default_config()
            merged_config = {}

            # 遍历所有应该存在的组
            for group_name in self.function_groups.keys():
                merged_config[group_name] = {}

                # 如果配置文件中存在该组
                if group_name in config_data and isinstance(config_data[group_name], dict):
                    # 遍历该组应该包含的所有功能
                    for func_name in self.function_groups[group_name]:
                        # 如果配置文件中存在该功能且值为布尔类型，使用配置文件中的值
                        if (func_name in config_data[group_name]
                                and isinstance(config_data[group_name][func_name], bool)):
                            merged_config[group_name][func_name] = config_data[group_name][func_name]
                        else:
                            # 否则使用默认值
                            merged_config[group_name][func_name] = default_config[group_name][func_name]
                else:
                    # 组不存在，使用默认配置
                    merged_config[group_name] = default_config[group_name]

            return merged_config

        except Exception as e:
            print(f"验证配置文件时出错: {e}，使用默认配置")
            return self.create_default_config()

    def add_or_remove_task(self, tab_name: str, group_name, func_name, enabled):
        """根据复选框状态添加或移除任务"""
        task_manager = self.tab_controls[tab_name]['task_manager']

        def execute_in_background():
            task_key = f"{tab_name}_{group_name}_{func_name}"

            if enabled:
                # 添加任务到任务管理器
                if group_name in self.task_definitions and func_name in self.task_definitions[group_name]:
                    task_config = self.task_definitions[group_name][func_name]

                    # 生成唯一任务ID
                    task_id = f"{group_name}_{func_name}_{int(datetime.now().timestamp())}"

                    # 添加任务
                    if task_config["schedule_type"] is ScheduleType.CRON:
                        task_manager.add_cron_task(
                            name=f"{group_name} - {func_name}",
                            func=task_config["func"],
                            cron_expression=task_config["cron_expression"],
                            immediate=task_config.get("immediate", False),
                            enabled=True
                        )
                    else:
                        task_manager.add_task(
                            name=f"{group_name} - {func_name}",
                            func=task_config["func"],
                            interval_seconds=task_config["interval_seconds"],
                            requires_game=task_config.get("requires_game", False),
                            immediate=task_config.get("immediate", False),
                            enabled=True
                        )

                    # 保存任务ID
                    self.task_ids[task_key] = task_id
                    # print(f"已添加任务: {group_name} - {func_name}")
            else:
                # 从任务管理器移除任务
                # 查找并移除该功能对应的任务
                tasks_to_remove = []
                for task in task_manager.list_tasks():
                    if task['name'] == f"{group_name} - {func_name}":
                        tasks_to_remove.append(task['task_id'])

                for task_id in tasks_to_remove:
                    task_manager.remove_task(task_id)
                    # print(f"已移除任务: {group_name} - {func_name}")

                # 从task_ids中移除
                if task_key in self.task_ids:
                    del self.task_ids[task_key]

        threading.Thread(target=execute_in_background, daemon=True).start()

    def auto_save_config(self, tab_name: str):
        """自动保存配置到文件"""

        # 在单独的线程中保存配置，避免阻塞UI
        def save_thread():
            if self.save_config(tab_name):
                # 更新状态显示
                pass
                '''
                self.root.after(100, lambda: self.status_label.config(
                    text="配置已自动保存",
                    fg='green'
                ))'''

        threading.Thread(target=save_thread, daemon=True).start()

    def update_stats(self, tab_name: str):
        """更新统计信息"""
        checkbox_vars = self.tab_controls[tab_name]['checkbox_vars']
        enabled = sum(1 for var in checkbox_vars.values() if var.get())
        # disabled = len(checkbox_vars) - enabled

        # 更新底部标签
        if hasattr(self, 'enabled_count'):
            self.enabled_count.config(text=f"已启用: {enabled}", fg='green')
            # self.disabled_count.config(text=f"已禁用: {disabled}", fg='red')
            # self.total_count.config(text=f"总数: {len(self.checkbox_vars)}")

    def pause_resume_all(self):
        """暂停或恢复所有task_manager"""
        # 先检查当前有多少task_manager处于running状态
        running_count = 0
        for tab_name, value in self.tab_controls.items():
            task_manager = value['task_manager']
            if task_manager.pause_event.is_set():
                running_count += 1

        # 根据当前状态决定操作
        if running_count > 0:
            # 还有running的，全部暂停
            for tab_name, value in self.tab_controls.items():
                task_manager = value['task_manager']
                status_message = value['status_message']
                if task_manager.is_running:
                    task_manager.pause()
                    status_message.set("任务执行已暂停")
        else:
            # 全部已暂停，全部恢复
            for tab_name, value in self.tab_controls.items():
                task_manager = value['task_manager']
                status_message = value['status_message']
                if task_manager.is_running:
                    task_manager.resume()
                    status_message.set("任务执行已恢复")

    def toggle_pause(self, tab_name: str):
        """切换暂停/恢复"""
        task_manager = self.tab_controls[tab_name]['task_manager']
        status_message = self.tab_controls[tab_name]['status_message']

        if task_manager.is_running:
            if task_manager.pause_event.is_set():
                task_manager.pause()
                status_message.set("任务执行已暂停")
            else:
                task_manager.resume()
                status_message.set("任务执行已恢复")

    def stop_manager(self, tab_name: str):
        """停止任务管理器"""
        task_manager = self.tab_controls[tab_name]['task_manager']
        status_message = self.tab_controls[tab_name]['status_message']
        if messagebox.askyesno("确认停止", "确定要停止任务管理器吗？"):
            task_manager.stop()
            status_message.set("任务管理器已停止")

    def start_manager(self, tab_name: str):
        """启动任务管理器"""
        task_manager = self.tab_controls[tab_name]['task_manager']
        status_message = self.tab_controls[tab_name]['status_message']
        task_manager.start()
        status_message.set("任务管理器已启动")

    def run(self):
        """运行GUI"""
        self.mainloop()

    def on_closing(self):
        """窗口关闭事件"""
        if messagebox.askokcancel("退出", "确定要退出任务管理器吗？"):
            '''self.update_running = False
            for key, value in self.tab_controls:
                task_manager = value['task_manager']
                if task_manager.is_running:
                    task_manager.stop()'''
            self.destroy()

    def browse_file(self):
        """浏览并选择EXE文件"""
        file_path = filedialog.askopenfilename(
            title="选择MumuManager.exe",
            filetypes=[
                ("可执行文件", "*.exe"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.file_path_var.set(file_path)

    def connect_mumu(self):
        file_path = self.file_path_var.get()
        self.mmm_path = file_path

        if not file_path:
            messagebox.showwarning("警告", "请选择正确的MumuManager.exe")
            return

        if not os.path.exists(file_path):
            messagebox.showerror("错误", "文件不存在！")
            return

        try:
            # 调用分析函数（这里用模拟函数代替）
            adb = ADBController(0, self.mmm_path)
            result_dict = adb.get_all_devices_info()

            # 清空现有的标签页
            for tab in self.notebook.tabs():
                self.notebook.forget(tab)

            # 根据字典生成标签页
            if result_dict:
                for index, tab_data in result_dict.items():
                    if tab_data['state']:
                        self.create_tab(tab_data)
                        self.initialize_checkboxes(tab_data['tab_name'])

        except Exception as e:
            messagebox.showerror("错误", f"分析过程中发生错误:\n{str(e)}")

    def create_tab(self, tab_data):
        """创建一个新的标签页"""
        # 创建框架作为标签页内容
        name = tab_data['name']
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=name)

        # 根据数据类型创建不同的显示方式
        if isinstance(tab_data, dict):
            self.create_widgets(tab_frame, tab_data)

    def _create_task_methods(self):
        """动态创建任务方法"""
        # 定义所有需要动态创建的任务方法名
        task_methods = [
            'soldier_training', 'earth_core', 'store_purchase', 'warehouse_reward',
            'adventure_gains', 'pet_treasure', 'crystal_lab', 'deposit',
            'daily_commander_reward', 'daily_charge_reward', 'daily_task_reward',
            'hero_recruit', 'mining', 'monster_hunt', 'monster_hunter',
            'alliance_donating', 'alliance_treasure', 'world_help', 'island_gain',
            'travel_gains', 'check_hunter_status', 'set_alliance_mine',
            'alliance_mobilization', 'frozen_treasure', 'read_mails', 'update_coordinate',
            'arena_fight', 'crystal_deep', 'romulus_reward', 'intelligence', 'strength_cans'
        ]

        for method_name in task_methods:
            # 创建一个闭包来捕获method_name
            def make_task_method(name):
                def task_method(self, winter):
                    # 获取winter对象中的对应方法并调用
                    method = getattr(winter, name, None)
                    if method:
                        return method()
                    else:
                        print(f"Warning: Method {{name}} not found in winter object")
                        return None

                return task_method

            # 将动态创建的方法绑定到当前实例
            setattr(self, method_name, make_task_method(method_name).__get__(self, self.__class__))

    @staticmethod
    def load_task_definitions_from_json():
        """从JSON文件加载任务定义"""
        try:
            with open('task_definitions.json', 'r', encoding='utf-8') as f:
                task_definitions_data = json.load(f)
            return task_definitions_data
        except FileNotFoundError:
            print("警告: 未找到task_definitions.json文件，使用默认配置")
            return {}
        except json.JSONDecodeError:
            print("错误: task_definitions.json文件格式不正确")
            return {}

    def _convert_task_definitions(self, raw_definitions):
        """将从JSON加载的原始任务定义转换为内部使用的格式"""
        converted_definitions = {}

        for group_name, group_tasks in raw_definitions.items():
            converted_group = {}
            for task_name, task_config in group_tasks.items():
                # 将字符串形式的函数名转换为实际的函数引用
                if 'func_name' in task_config:
                    func_name = task_config['func_name']
                    # 从self中获取对应的函数
                    func_ref = getattr(self, func_name, None)
                    if func_ref is None:
                        print(f"警告: 未找到函数 {func_name}")
                        continue

                    # 替换函数引用并调整配置格式
                    new_config = {
                        'func': func_ref,
                        'requires_game': task_config.get('requires_game', False)
                    }

                    # 根据schedule_type处理不同类型的调度配置
                    schedule_type_str = task_config.get('schedule_type', 'INTERVAL')
                    if schedule_type_str == 'CRON':
                        new_config['schedule_type'] = ScheduleType.CRON
                        new_config['cron_expression'] = task_config.get('cron_expression', '* * * * *')
                        if 'immediate' in task_config:
                            new_config['immediate'] = task_config['immediate']
                    elif schedule_type_str == 'INTERVAL':
                        new_config['schedule_type'] = ScheduleType.INTERVAL
                        new_config['interval_seconds'] = task_config.get('interval_seconds', 60)
                        if 'immediate' in task_config:
                            new_config['immediate'] = task_config['immediate']

                    converted_group[task_name] = new_config
            converted_definitions[group_name] = converted_group

        return converted_definitions


def main():
    """主函数"""

    # 创建并运行GUI
    TaskManagerGUI()


if __name__ == "__main__":
    main()
