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
                         min_quality: int = 1, max_quality: int = 100) -> Tuple[bytes, int]:
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

        # PNG格式不支持质量参数，尝试调整尺寸
        if pil_format == 'PNG':
            # 先尝试原尺寸
            buffer = io.BytesIO()
            self.image.save(buffer, format=pil_format, optimize=True)
            data = buffer.getvalue()

            if len(data) <= target_bytes:
                return data, 100

            # 如果太大，缩小尺寸
            scale_factor = 0.9
            while len(data) > target_bytes and scale_factor >= 0.1:
                new_width = int(self.image.size[0] * scale_factor)
                new_height = int(self.image.size[1] * scale_factor)
                temp_img = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                buffer = io.BytesIO()
                temp_img.save(buffer, format=pil_format, optimize=True)
                data = buffer.getvalue()
                scale_factor -= 0.1

            return data, 100

        # JPEG/WebP 使用二分法查找合适的质量
        low, high = min_quality, max_quality
        best_quality = min_quality
        best_data = b''
        best_size = float('inf')

        # 先检查最高质量是否超过目标
        buffer = io.BytesIO()
        try:
            if pil_format == 'JPEG':
                self.image.save(buffer, format=pil_format, quality=100, optimize=True)
            else:
                self.image.save(buffer, format=pil_format, quality=100)
            max_quality_data = buffer.getvalue()

            # 如果最高质量仍然小于目标，直接返回
            if len(max_quality_data) <= target_bytes:
                print(f"最高质量(100)的大小为{len(max_quality_data)//1024}KB，小于目标{target_size_kb}KB")
                return max_quality_data, 100
        except Exception as e:
            print(f"最高质量压缩失败: {e}")

        # 检查最低质量是否满足要求
        buffer = io.BytesIO()
        try:
            if pil_format == 'JPEG':
                self.image.save(buffer, format=pil_format, quality=min_quality, optimize=True)
            else:
                self.image.save(buffer, format=pil_format, quality=min_quality)
            data = buffer.getvalue()

            # 如果最低质量也太大，需要调整尺寸
            if len(data) > target_bytes:
                print(f"警告: 即使质量={min_quality}，文件大小{len(data)//1024}KB仍超过目标{target_size_kb}KB，将自动调整尺寸")
                return self._compress_with_resize(target_bytes, pil_format, min_quality)
        except Exception as e:
            print(f"最低质量压缩失败: {e}")

        # 二分法查找合适的质量
        while low <= high:
            mid = (low + high) // 2
            buffer = io.BytesIO()

            try:
                if pil_format == 'JPEG':
                    self.image.save(buffer, format=pil_format, quality=mid, optimize=True)
                else:
                    self.image.save(buffer, format=pil_format, quality=mid)

                data = buffer.getvalue()
                current_size = len(data)

                print(f"质量={mid}, 大小={current_size//1024}KB, 目标={target_size_kb}KB")

                # 如果大小接近目标（±10%），返回
                if abs(current_size - target_bytes) < target_bytes * 0.1:
                    print(f"找到合适质量: {mid}, 大小接近目标")
                    return data, mid

                if current_size <= target_bytes:
                    # 如果当前大小更接近目标，更新最佳结果
                    if current_size > best_size or best_size == float('inf'):
                        best_quality = mid
                        best_data = data
                        best_size = current_size
                    low = mid + 1
                else:
                    # 当前大小超过目标，降低质量
                    high = mid - 1
            except Exception as e:
                print(f"压缩失败 (quality={mid}): {e}")
                high = mid - 1

        # 如果找到了合适的数据，返回
        if best_data and best_size <= target_bytes * 1.1:  # 允许10%误差
            return best_data, best_quality

        # 如果没有找到合适的，返回最低质量
        buffer = io.BytesIO()
        try:
            if pil_format == 'JPEG':
                self.image.save(buffer, format=pil_format, quality=min_quality, optimize=True)
            else:
                self.image.save(buffer, format=pil_format, quality=min_quality)
            return buffer.getvalue(), min_quality
        except:
            return b'', 0

    def _compress_with_resize(self, target_bytes: int, pil_format: str, quality: int) -> Tuple[bytes, int]:
        """通过调整尺寸来压缩图片"""
        scale_factor = 0.9

        while scale_factor >= 0.1:
            new_width = int(self.image.size[0] * scale_factor)
            new_height = int(self.image.size[1] * scale_factor)
            temp_img = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            try:
                if pil_format == 'JPEG':
                    temp_img.save(buffer, format=pil_format, quality=quality, optimize=True)
                else:
                    temp_img.save(buffer, format=pil_format, quality=quality)

                data = buffer.getvalue()
                print(f"缩放{scale_factor:.1f}倍，大小={len(data)//1024}KB")

                if len(data) <= target_bytes:
                    return data, quality

                scale_factor -= 0.1
            except Exception as e:
                print(f"调整尺寸压缩失败: {e}")
                scale_factor -= 0.1

        # 返回最小的结果
        buffer = io.BytesIO()
        temp_img = self.image.resize((int(self.image.size[0] * 0.1), int(self.image.size[1] * 0.1)),
                                     Image.Resampling.LANCZOS)
        if pil_format == 'JPEG':
            temp_img.save(buffer, format=pil_format, quality=quality, optimize=True)
        else:
            temp_img.save(buffer, format=pil_format, quality=quality)
        return buffer.getvalue(), quality

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