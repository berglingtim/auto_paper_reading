# 测试临时文件收进工作区 .pytest_tmp，不写系统临时目录
# (src 包导入路径由 pytest.ini 的 pythonpath=src 提供)
from pathlib import Path


def pytest_configure(config):
    # 测试临时文件收进工作区 .pytest_tmp，不写系统临时目录
    config.option.basetemp = str(Path(__file__).resolve().parent / ".pytest_tmp")
