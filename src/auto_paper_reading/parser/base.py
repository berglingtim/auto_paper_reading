"""解析器抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import PaperDocument


class BaseParser(ABC):
    """所有解析器的统一接口：输入文件路径，输出 PaperDocument。"""

    @abstractmethod
    def parse(self, path: Path, work_dir: Path | None = None) -> PaperDocument:
        """解析论文。

        Args:
            path: 论文文件路径。
            work_dir: 工作目录，用于存放裁剪图片等中间产物；为 None 则不裁剪图片。
        """
        raise NotImplementedError
