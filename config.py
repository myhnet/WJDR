import os
import json
import configparser
from functions import load_json_config
from datetime import datetime
from MumuManager import MumuGameAutomator
from WinterLess import WinterLess


class ConfigManager:
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.game_config = "game_tasks_config.json"
        self.function_groups = {}
        self.task_definitions = self.get_task_config()
        for group_name, functions in self.task_definitions.items():
            self.function_groups[group_name] = list(functions.keys())
        self.tab_controls = {}
        self.bear_hero = {}
        self.sys_config = self.get_sys_config()
        self.mmm_path = self.sys_config.pop('_metadata', None)['mumu_path']
        self.load_config()
    
    def load_config(self):
        """从配置文件加载配置"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            self.create_default_config()

        sys_config = self.sys_config
        for item in sys_config.items():
            tab_name = item[1]['tab_name']
            device_id = item[1]['id']
            self.bear_hero[device_id] = {
                'archer': None,
                'infantry': None,
                'cavalry': 'Mia'
            }
            self.tab_controls[tab_name] = {}
            self.tab_controls[tab_name]['automator'] = MumuGameAutomator(mumu_device=device_id,
                                                                         game_package="com.gof.china",
                                                                         mmm_path=self.mmm_path)
            automator = self.tab_controls[tab_name]['automator']
            automator.start_game()
            self.tab_controls[tab_name]['winter'] = WinterLess(automator)
            self.tab_controls[tab_name]['checkbox_vars'] = {}
            self.tab_controls[tab_name]['update_running'] = False
            self.tab_controls[tab_name]['last_history_hash'] = 0
            self.tab_controls[tab_name]['last_upcoming_hash'] = 0
            self.tab_controls[tab_name]['last_update_time'] = 0
            self.tab_controls[tab_name]['current_config'] = self.load_player_config(tab_name)

            # 处理bear_settings
            bear_settings = self.tab_controls[tab_name]['bear_settings']
            if bear_settings['enabled']:
                if bear_settings['archer_enabled']:
                    self.bear_hero[device_id]['archer'] = bear_settings['archer_hero']
                if bear_settings['infantry_enabled']:
                    self.bear_hero[device_id]['infantry'] = bear_settings['infantry_hero']
                if bear_settings['cavalry_enabled']:
                    self.bear_hero[device_id]['cavalry'] = bear_settings['cavalry_hero']

    def create_default_config(self):
        """创建默认配置文件"""
        self.config['DEFAULT'] = {
            'sys_config': 'sys_config.json',
            'task_config': 'task_definitions.json'
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
        print(f"默认配置文件 {self.config_file} 已创建")
    
    def get(self, section, key, fallback=None):
        """获取配置值"""
        return self.config.get(section, key, fallback=fallback)
    
    def get_sys_config(self):
        """获取系统配置文件路径"""
        config_path = self.get('DEFAULT', 'sys_config', 'sys_config.json')
        return load_json_config(config_path)
    
    def get_task_config(self):
        """获取任务配置文件路径"""
        config_path = self.get('DEFAULT', 'task_config', 'task_definitions.json')
        return load_json_config(config_path)

    def create_task_default_config(self):
        """创建默认配置"""
        config = {}
        for group_name, functions in self.task_definitions.items():
            config[group_name] = {}
            for func_name in functions:
                # 默认情况下，大部分功能不启用
                config[group_name][func_name] = False
        return config

    def generate_config_name(self, t_name: str):
        config_file = os.path.basename(self.game_config)
        dir_name = os.path.dirname(self.game_config)
        name, ext = config_file.rsplit('.', 1) if '.' in config_file else (config_file, '')
        if dir_name:
            config_file = f'{dir_name}/{name}_{t_name}.{ext}'
        else:
            config_file = f'{dir_name}{name}_{t_name}.{ext}'
        return config_file

    def validate_config(self, config_data):
        """验证并修复配置数据的结构，保留相同部分，缺失部分用默认值补充"""
        try:
            # 创建默认配置作为基础
            default_config = self.create_task_default_config()
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
            return self.create_task_default_config()

    def load_player_config(self, tab_name: str):
        """从配置文件加载配置"""
        try:
            config_file = self.generate_config_name(tab_name)
            config_data = load_json_config(config_file)
            if config_data:

                # 移除元数据部分（如果有）
                if "_metadata" in config_data:
                    config_data.pop("_metadata")
                if "bear_settings" in config_data:
                    self.tab_controls[tab_name]['bear_settings'] = config_data.pop("bear_settings")

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
                default_config = self.create_task_default_config()
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
            return self.create_task_default_config()

    def save_config(self, tab_name: str):
        """保存配置到文件"""
        checkbox_vars = self.tab_controls[tab_name].get('checkbox_vars', {})
        bear_setting = self.tab_controls[tab_name].get('bear_settings', {})
        config_file = self.generate_config_name(tab_name)
        default_config = self.create_task_default_config()
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
                        config_data[group_name][func_name] = default_config.get(group_name, {}).get(func_name, False)

            # 打熊配置
            config_data["bear_settings"] = {
                "enabled": bear_setting['enabled_var'].get(),
                "start_hour": bear_setting['start_hour_var'].get(),
                "start_minute": bear_setting['start_minute_var'].get(),
                "archer_enabled": bear_setting['archer_var'].get(),
                "archer_hero": bear_setting['archer_hero_var'].get(),
                "shield_enabled": bear_setting['shield_var'].get(),
                "shield_hero": bear_setting['shield_hero_var'].get(),
                "spearman_enabled": bear_setting['spearman_var'].get(),
                "spearman_hero": bear_setting['spearman_hero_var'].get()
            }

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


# 创建全局配置管理器实例
config_manager = ConfigManager()


# 便捷函数


# 测试加载配置
SYS_CONFIG = config_manager.get_sys_config()
TASK_DEFINITION = config_manager.task_definitions
SYS_CONFIG.pop('_metadata', None)

MMM_PATH = config_manager.mmm_path
BEAR_HERO = config_manager.bear_hero
TAB_CONTROLS = config_manager.tab_controls


if __name__ == "__main__":
    print("系统配置内容:", SYS_CONFIG)
    print("任务配置内容:", TASK_DEFINITION)
    print("熊战士配置内容:", BEAR_HERO)
    print("TAB_CONTROLS", TAB_CONTROLS)
