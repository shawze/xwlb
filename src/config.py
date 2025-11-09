# -*- coding: utf-8 -*-
import configparser
import os


class Config(object):
    """此类用于加载和管理 .ini 配置文件。"""

    def __init__(self, config_file='config.ini'):
        self._path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', config_file))
        if not os.path.exists(self._path):
            raise FileNotFoundError(f"配置文件未找到: {self._path}")
        self._config = configparser.ConfigParser()
        self._config.read(self._path, encoding='utf-8')

    def get(self, section, name, strip_blank=True, strip_quote=True):
        """获取一个配置项的值。"""
        s = self._config.get(section, name)
        if strip_blank:
            s = s.strip()
        if strip_quote:
            s = s.strip("'").strip('"')
        return s

    def getboolean(self, section, name):
        """获取一个布尔类型的配置项。"""
        return self._config.getboolean(section, name)

    def save_config(self, section, name, value):
        """保存一个配置项。"""
        try:
            self._config.set(section, name, value)
            with open(self._path, 'w') as fp:
                self._config.write(fp)
        except Exception as e:
            return e

    def add_section(self, section):
        """添加一个新的配置段。"""
        self._config.add_section(section)


# 创建一个全局单例
global_config = Config()

def load_stage_config(config: Config) -> dict:
    """从配置文件加载工作流阶段控制相关的配置。"""
    cfg = {}
    try:
        # 读取凭证
        credential_keys = ["XUEQIU_COOKIE", "EASTMONEY_CTOKEN", "EASTMONEY_UTOKEN"]
        for key in credential_keys:
            try:
                cfg[key] = config.get('Credentials', key)
            except (configparser.NoSectionError, configparser.NoOptionError):
                cfg[key] = None # 如果没找到，则设为 None

        # 读取主要流程开关
        stage_keys = ["publish_wechat_work", "publish_wechat_mp", "publish_xueqiu", "publish_eastmoney", "use_gemini_analyzer_proxy"]
        for key in stage_keys:
            cfg[key] = config.getboolean('StageControl', key)
            
        # 读取调试与缓存控制开关
        debug_keys = [
            "force_fetch_news", "force_fetch_contents", "force_rerun_analysis",
            "force_regenerate_cover", "force_publish_work", "force_publish_mp",
            "force_publish_xueqiu", "force_publish_eastmoney"
        ]
        for key in debug_keys:
            cfg[key] = config.getboolean('DebugControl', key)
            
    except Exception as e:
        print(f"加载 STAGE_CONFIG 失败，请检查 config.ini 文件: {e}")
        # 在失败时提供一个默认的安全配置
        return {
            "publish_wechat_work": False, "publish_wechat_mp": False, "publish_xueqiu": False, "publish_eastmoney": False,
            "use_gemini_analyzer_proxy": False,
            "force_fetch_news": False, "force_fetch_contents": False, "force_rerun_analysis": False,
            "force_regenerate_cover": False, "force_publish_work": False, "force_publish_mp": False,
            "force_publish_xueqiu": False, "force_publish_eastmoney": False,
            "XUEQIU_COOKIE": None, "EASTMONEY_CTOKEN": None, "EASTMONEY_UTOKEN": None
        }
    return cfg

# 加载并创建一个全局的工作流阶段配置字典
STAGE_CONFIG = load_stage_config(global_config)
