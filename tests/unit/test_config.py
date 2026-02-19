"""
Configuration management tests
"""

import os
import pytest
from src.config import Config


class TestConfig:
    """Test configuration loading and management"""

    def test_load_github_key_from_config(self, tmp_path):
        """Should load GitHub key from config file"""
        # Create temporary config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("github_key: test_key_12345\n")

        # Load config
        config = Config(str(config_file))

        # Verify
        assert config.config["github_key"] == "test_key_12345"

    def test_github_key_env_override(self, tmp_path, monkeypatch):
        """Should override GitHub key from environment variable"""
        # Set environment variable
        monkeypatch.setenv("GITHUB_LITELLM_KEY", "env_key_67890")

        # Create config file without github_key
        config_file = tmp_path / "config.yaml"
        config_file.write_text("model_list: []\n")

        # Load config
        config = Config(str(config_file))

        # Verify
        assert config.config["github_key"] == "env_key_67890"

    def test_github_key_default_fallback(self, tmp_path):
        """Should use default GitHub key if not in config or env"""
        # Create minimal config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("model_list: []\n")

        # Load config
        config = Config(str(config_file))

        # Verify default key is used
        assert config.config["github_key"] == "${GITHUB_LITELLM_KEY}"
