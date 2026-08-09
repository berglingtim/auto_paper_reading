# 让测试能找到 src 下的包
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def pytest_configure(config):
    # 测试临时文件收进工作区 .pytest_tmp，不写系统临时目录
    config.option.basetemp = str(Path(__file__).resolve().parent / ".pytest_tmp")
