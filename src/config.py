"""
Configuration management module

功能:
- 加载配置文件
- API Key 管理（主/備用）
- 環境變量覆蓋
"""

import os
import yaml


class Config:
    """配置管理類"""

    DEFAULT_GITHUB_KEY = "${GITHUB_LITELLM_KEY}"

    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化配置

        Args:
            config_path: 配置文件路徑
        """
        self.config = self._load_config(config_path)

    def _load_config(self, path: str) -> dict:
        """
        加載配置文件

        Args:
            path: 配置文件路徑

        Returns:
            配置字典
        """
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # GitHub Key: 配置優先，環境變量兜底，最後使用默認值
        github_key = config.get("github_key")
        if not github_key:
            github_key = os.getenv("GITHUB_LITELLM_KEY", self.DEFAULT_GITHUB_KEY)

        config["github_key"] = github_key
        return config
