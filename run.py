#!/usr/bin/env python3
"""项目入口：把 src 加入模块搜索路径后调用 CLI。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from auto_paper_reading.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
