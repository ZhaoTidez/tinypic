"""
图片处理核心模块
实现压缩、格式转换、尺寸调整等功能
"""

import os
from pathlib import Path
from PIL import Image
from typing import Tuple, Optional, List
import io


class ImageProcessor:
    """图片处理器核心类"""

    SUPPORTED_FORMATS = {
        'JPEG': '.jpg',
        'PNG': '.png',
        'WebP': '.webp',
        'BMP': '.bmp',
        'GIF': '.gif',
        'TIFF': '.tiff'
    }

    def __init__(self):
        self.image: Optional[Image.Image] = None
        self.original_path: Optional[str] = None
        self.original_size: Tuple[int, int] = (0, 0)

    def load_image(self, file_path: str) -> bool:
        """加载图片文件"""
        try:
            self.image = Image.open(file_path)
            self.original_path = file_path
            self.original_size = self.image.size
            # 转换为RGB模式（如果需要）
            if self.image.mode not in ('RGB', 'L'):
                self.image = self.image.convert('RGB')
            return True
        except Exception as e:
            print(f"加载图片失败: {e}")
            return False

    def resize_image(self, width: Optional[int] = None, height: Optional[int] = None,
                     keep_aspect_ratio: bool = True) -> bool:
        """调整图片尺寸"""
        if not self.image:
            return False

        try:
            if width and height:
                if keep_aspect_ratio:
                    # 保持宽高比，计算合适的尺寸
                    orig_width, orig_height = self.image.size
                    ratio_w = width / orig_width
                    ratio_h = height / orig_height
                    ratio = min(ratio_w, ratio_h)
                    new_width = int(orig_width * ratio)
                    new_height = int(orig_height * ratio)
                else:
                    new_width, new_height = width, height
            elif width:
                # 只指定宽度
                orig_width, orig_height = self.image.size
                ratio = width / orig_width
                new_width = width
                new_height = int(orig_height * ratio)
            elif height:
                # 只指定高度
                orig_width, orig_height = self.image.size
                ratio = height / orig_height
                new_width = int(orig_width * ratio)
                new_height = height
            else:
                return False

            # 使用高质量的LANCZOS重采样
            self.image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            return True
        except Exception as e:
            print(f"调整尺寸失败: {e}")
            return False

    def compress_to_size(self, target_size_kb: int, output_format: str = 'JPEG',
                         min_quality: int = 1, max_quality: int = 95) -> Tuple[bytes, int]:
        """
        压缩图片到目标大小
        使用二分法逼近目标文件大小
        返回: (图片字节数据, 实际质量)
        """
        if not self.image:
            return b'', 0

        target_bytes = target_size_kb * 1024

        # 确定图片格式
        format_map = {
            'JPEG': 'JPEG',
            'PNG': 'PNG',
            'WebP': 'WEBP',
            'BMP': 'BMP',
            'GIF': 'GIF'
        }
        pil_format = format_map.get(output_format, 'JPEG')

        # PNG格式不支持质量参数，直接保存
        if pil_format == 'PNG':
            buffer = io.BytesIO()
            self.image.save(buffer, format=pil_format, optimize=True)
            return buffer.getvalue(), 100

        # 二分法查找合适的质量
        low, high = min_quality, max_quality
        best_quality = min_quality
        best_data = b''

        while low <= high:
            mid = (low + high) // 2
            buffer = io.BytesIO()

            try:
                if pil_format == 'JPEG':
                    self.image.save(buffer, format=pil_format, quality=mid, optimize=True)
                elif pil_format == 'WEBP':
                    self.image.save(buffer, format=pil_format, quality=mid)
                else:
                    self.image.save(buffer, format=pil_format)

                data = buffer.getvalue()
                current_size = len(data)

                # 如果大小接近目标，返回
                if abs(current_size - target_bytes) < target_bytes * 0.05:  # 5%误差
                    return data, mid

                if current_size <= target_bytes:
                    best_quality = mid
                    best_data = data
                    low = mid + 1
                else:
                    high = mid - 1
            except Exception as e:
                print(f"压缩失败 (quality={mid}): {e}")
                high = mid - 1

        # 如果没找到合适的，使用最佳质量
        if best_data:
            return best_data, best_quality

        # 最后尝试最低质量
        buffer = io.BytesIO()
        try:
            self.image.save(buffer, format=pil_format, quality=min_quality)
            return buffer.getvalue(), min_quality
        except:
            return b'', 0

    def compress_with_quality(self, quality: int, output_format: str = 'JPEG') -> bytes:
        """使用指定质量压缩图片"""
        if not self.image:
            return b''

        buffer = io.BytesIO()
        format_map = {
            'JPEG': 'JPEG',
            'WebP': 'WEBP',
            'PNG': 'PNG'
        }
        pil_format = format_map.get(output_format, 'JPEG')

        try:
            if pil_format == 'PNG':
                self.image.save(buffer, format=pil_format, optimize=True)
            elif pil_format == 'JPEG':
                self.image.save(buffer, format=pil_format, quality=quality, optimize=True)
            elif pil_format == 'WEBP':
                self.image.save(buffer, format=pil_format, quality=quality)

            return buffer.getvalue()
        except Exception as e:
            print(f"压缩失败: {e}")
            return b''

    def save_image(self, output_path: str, quality: int = 85, output_format: Optional[str] = None) -> bool:
        """保存图片到指定路径"""
        if not self.image:
            return False

        try:
            # 确定输出格式
            if output_format:
                format_map = {
                    'JPEG': 'JPEG',
                    'PNG': 'PNG',
                    'WebP': 'WEBP',
                    'BMP': 'BMP',
                    'GIF': 'GIF'
                }
                pil_format = format_map.get(output_format, 'JPEG')
            else:
                # 从文件扩展名推断格式
                ext = Path(output_path).suffix.upper()
                format_map = {
                    '.JPG': 'JPEG',
                    '.JPEG': 'JPEG',
                    '.PNG': 'PNG',
                    '.WEBP': 'WEBP',
                    '.BMP': 'BMP',
                    '.GIF': 'GIF'
                }
                pil_format = format_map.get(ext, 'JPEG')

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 保存图片
            if pil_format == 'PNG':
                self.image.save(output_path, format=pil_format, optimize=True)
            elif pil_format == 'JPEG':
                self.image.save(output_path, format=pil_format, quality=quality, optimize=True)
            elif pil_format == 'WEBP':
                self.image.save(output_path, format=pil_format, quality=quality)
            else:
                self.image.save(output_path, format=pil_format)

            return True
        except Exception as e:
            print(f"保存图片失败: {e}")
            return False

    def get_image_info(self) -> dict:
        """获取图片信息"""
        if not self.image:
            return {}

        return {
            'width': self.image.size[0],
            'height': self.image.size[1],
            'mode': self.image.mode,
            'format': self.image.format if hasattr(self.image, 'format') else 'Unknown',
            'original_path': self.original_path
        }

    @staticmethod
    def get_file_size_kb(file_path: str) -> int:
        """获取文件大小（KB）"""
        try:
            return os.path.getsize(file_path) // 1024
        except:
            return 0

    @staticmethod
    def is_supported_format(file_path: str) -> bool:
        """检查文件格式是否支持"""
        try:
            ext = Path(file_path).suffix.lower()
            supported_exts = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff', '.tif']
            return ext in supported_exts
        except:
            return False


class BatchProcessor:
    """批量图片处理器"""

    def __init__(self):
        self.processors: List[ImageProcessor] = []
        self.results: List[dict] = []

    def add_image(self, file_path: str) -> bool:
        """添加图片到处理队列"""
        processor = ImageProcessor()
        if processor.load_image(file_path):
            self.processors.append(processor)
            return True
        return False

    def process_single(self, processor: ImageProcessor, output_path: str,
                       target_size_kb: Optional[int] = None,
                       width: Optional[int] = None, height: Optional[int] = None,
                       quality: Optional[int] = None,
                       output_format: str = 'JPEG',
                       keep_aspect_ratio: bool = True) -> dict:
        """处理单个图片"""
        result = {
            'input_path': processor.original_path,
            'output_path': output_path,
            'success': False,
            'original_size': processor.get_image_info(),
            'message': ''
        }

        try:
            # 调整尺寸
            if width or height:
                if not processor.resize_image(width, height, keep_aspect_ratio):
                    result['message'] = '调整尺寸失败'
                    return result

            # 压缩并保存
            if target_size_kb:
                data, actual_quality = processor.compress_to_size(target_size_kb, output_format)
                if data:
                    with open(output_path, 'wb') as f:
                        f.write(data)
                    result['success'] = True
                    result['quality'] = actual_quality
                    result['output_size_kb'] = len(data) // 1024
                else:
                    result['message'] = '压缩失败'
            elif quality:
                if processor.save_image(output_path, quality, output_format):
                    result['success'] = True
                    result['quality'] = quality
                    result['output_size_kb'] = ImageProcessor.get_file_size_kb(output_path)
                else:
                    result['message'] = '保存失败'
            else:
                if processor.save_image(output_path, 85, output_format):
                    result['success'] = True
                    result['output_size_kb'] = ImageProcessor.get_file_size_kb(output_path)
                else:
                    result['message'] = '保存失败'

        except Exception as e:
            result['message'] = f'处理异常: {str(e)}'

        return result