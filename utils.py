"""
工具函数模块
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List


def generate_output_filename(input_path: str, output_dir: str, suffix: str = '_compressed',
                             output_format: str = 'JPEG') -> str:
    """
    生成输出文件名

    Args:
        input_path: 输入文件路径
        output_dir: 输出目录
        suffix: 文件名后缀
        output_format: 输出格式

    Returns:
        输出文件的完整路径
    """
    input_path = Path(input_path)
    base_name = input_path.stem

    # 格式扩展名映射
    format_ext_map = {
        'JPEG': '.jpg',
        'PNG': '.png',
        'WebP': '.webp',
        'BMP': '.bmp',
        'GIF': '.gif'
    }

    ext = format_ext_map.get(output_format, '.jpg')
    output_name = f"{base_name}{suffix}{ext}"

    return os.path.join(output_dir, output_name)


def ensure_directory(path: str) -> bool:
    """确保目录存在，不存在则创建"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except:
        return False


def get_unique_filename(file_path: str) -> str:
    """获取唯一文件名，如果文件已存在则添加数字后缀"""
    if not os.path.exists(file_path):
        return file_path

    path = Path(file_path)
    directory = path.parent
    base_name = path.stem
    ext = path.suffix

    counter = 1
    while True:
        new_name = f"{base_name}_{counter}{ext}"
        new_path = directory / new_name
        if not new_path.exists():
            return str(new_path)
        counter += 1


def format_file_size(size_kb: int) -> str:
    """格式化文件大小显示"""
    if size_kb < 1024:
        return f"{size_kb} KB"
    else:
        size_mb = size_kb / 1024
        return f"{size_mb:.2f} MB"


def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
    """计算压缩比例"""
    if original_size == 0:
        return 0.0
    return (1 - compressed_size / original_size) * 100


def validate_image_files(file_paths: List[str]) -> List[str]:
    """验证图片文件列表，返回有效的文件路径"""
    valid_files = []
    supported_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff', '.tif'}

    for path in file_paths:
        if os.path.isfile(path):
            ext = Path(path).suffix.lower()
            if ext in supported_exts:
                valid_files.append(path)

    return valid_files


def get_timestamp_filename(prefix: str = 'image') -> str:
    """生成基于时间戳的文件名"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{prefix}_{timestamp}"


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, total: int = 0):
        self.total = total
        self.current = 0
        self.completed = 0
        self.failed = 0

    def update(self, success: bool = True):
        """更新进度"""
        self.current += 1
        if success:
            self.completed += 1
        else:
            self.failed += 1

    def get_percentage(self) -> int:
        """获取进度百分比"""
        if self.total == 0:
            return 0
        return int((self.current / self.total) * 100)

    def reset(self, total: int = 0):
        """重置进度"""
        self.total = total
        self.current = 0
        self.completed = 0
        self.failed = 0