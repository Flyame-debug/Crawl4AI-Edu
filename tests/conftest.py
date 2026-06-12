"""
文件名: conftest.py
作用: pytest 全局配置，提供 Django 测试环境基础 fixtures
"""

import pytest


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    作用: 使所有测试默认拥有数据库访问权限
    """
    pass
