"""
图片压缩器 GUI 界面
功能完整的图形用户界面
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QComboBox, QSpinBox, QCheckBox, QLineEdit, QFileDialog,
    QProgressBar, QTabWidget, QMessageBox, QSplitter, QFrame,
    QScrollArea, QGridLayout, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMimeData, QSize
from PyQt5.QtGui import QPixmap, QIcon, QImage, QDragEnterEvent, QDropEvent
from PIL import Image
from pathlib import Path
from typing import List, Optional
import threading

from image_processor import ImageProcessor, BatchProcessor
from utils import (
    generate_output_filename, format_file_size, calculate_compression_ratio,
    validate_image_files, ProgressTracker
)


class PreviewDialog(QDialog):
    """图片预览对比对话框"""

    def __init__(self, original_path: str, compressed_path: str, parent=None):
        super().__init__(parent)
        self.original_path = original_path
        self.compressed_path = compressed_path
        self.init_ui()

    def init_ui(self):
        """初始化预览界面"""
        self.setWindowTitle('图片对比预览')
        self.setMinimumSize(1000, 600)

        layout = QHBoxLayout(self)

        # 原图预览
        original_group = QGroupBox("原图")
        original_layout = QVBoxLayout(original_group)
        self.original_label = QLabel()
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setScaledContents(False)
        original_layout.addWidget(self.original_label)

        # 获取原图信息
        orig_img = Image.open(self.original_path)
        orig_size_kb = os.path.getsize(self.original_path) // 1024
        orig_info = QLabel(f"尺寸: {orig_img.size[0]}x{orig_img.size[1]}\n大小: {format_file_size(orig_size_kb)}")
        orig_info.setAlignment(Qt.AlignCenter)
        original_layout.addWidget(orig_info)

        layout.addWidget(original_group)

        # 压缩后预览
        compressed_group = QGroupBox("压缩后")
        compressed_layout = QVBoxLayout(compressed_group)
        self.compressed_label = QLabel()
        self.compressed_label.setAlignment(Qt.AlignCenter)
        self.compressed_label.setScaledContents(False)
        compressed_layout.addWidget(self.compressed_label)

        # 获取压缩后图片信息
        comp_img = Image.open(self.compressed_path)
        comp_size_kb = os.path.getsize(self.compressed_path) // 1024
        ratio = calculate_compression_ratio(orig_size_kb, comp_size_kb)
        comp_info = QLabel(
            f"尺寸: {comp_img.size[0]}x{comp_img.size[1]}\n大小: {format_file_size(comp_size_kb)}\n压缩率: {ratio:.1f}%")
        comp_info.setAlignment(Qt.AlignCenter)
        compressed_layout.addWidget(comp_info)

        layout.addWidget(compressed_group)

        # 加载图片
        self.load_images()

        # 关闭按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)

    def load_images(self):
        """加载并显示图片"""
        try:
            # 原图
            orig_img = Image.open(self.original_path)
            orig_img.thumbnail((450, 450), Image.Resampling.LANCZOS)

            # 确保图片是RGB模式
            if orig_img.mode != 'RGB':
                orig_img = orig_img.convert('RGB')

            # 转换为QImage
            data = orig_img.tobytes('raw', 'RGB')
            qimg = QImage(data, orig_img.size[0], orig_img.size[1],
                         orig_img.size[0] * 3, QImage.Format_RGB888)
            orig_pixmap = QPixmap.fromImage(qimg)
            self.original_label.setPixmap(orig_pixmap)

            # 压缩后
            comp_img = Image.open(self.compressed_path)
            comp_img.thumbnail((450, 450), Image.Resampling.LANCZOS)

            # 确保图片是RGB模式
            if comp_img.mode != 'RGB':
                comp_img = comp_img.convert('RGB')

            # 转换为QImage
            data = comp_img.tobytes('raw', 'RGB')
            qimg = QImage(data, comp_img.size[0], comp_img.size[1],
                         comp_img.size[0] * 3, QImage.Format_RGB888)
            comp_pixmap = QPixmap.fromImage(qimg)
            self.compressed_label.setPixmap(comp_pixmap)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'加载图片失败: {str(e)}')


class CompressionWorker(QThread):
    """压缩工作线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, files: List[str], output_dir: str, settings: dict):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.settings = settings

    def run(self):
        """执行压缩任务"""
        results = []
        batch_processor = BatchProcessor()

        for i, file_path in enumerate(self.files):
            try:
                processor = ImageProcessor()
                if processor.load_image(file_path):
                    output_path = generate_output_filename(
                        file_path,
                        self.output_dir,
                        '_compressed',
                        self.settings.get('format', 'JPEG')
                    )

                    # 调整尺寸
                    width = self.settings.get('width')
                    height = self.settings.get('height')
                    if width or height:
                        processor.resize_image(
                            width, height,
                            self.settings.get('keep_aspect_ratio', True)
                        )

                    # 压缩
                    target_size = self.settings.get('target_size_kb')
                    quality = self.settings.get('quality', 85)
                    output_format = self.settings.get('format', 'JPEG')

                    if target_size:
                        data, actual_quality = processor.compress_to_size(target_size, output_format)
                        if data:
                            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                            with open(output_path, 'wb') as f:
                                f.write(data)
                            results.append({
                                'input_path': file_path,
                                'output_path': output_path,
                                'success': True,
                                'original_size_kb': ImageProcessor.get_file_size_kb(file_path),
                                'output_size_kb': len(data) // 1024
                            })
                        else:
                            results.append({
                                'input_path': file_path,
                                'output_path': output_path,
                                'success': False,
                                'message': '压缩失败'
                            })
                    else:
                        if processor.save_image(output_path, quality, output_format):
                            results.append({
                                'input_path': file_path,
                                'output_path': output_path,
                                'success': True,
                                'original_size_kb': ImageProcessor.get_file_size_kb(file_path),
                                'output_size_kb': ImageProcessor.get_file_size_kb(output_path)
                            })
                        else:
                            results.append({
                                'input_path': file_path,
                                'output_path': output_path,
                                'success': False,
                                'message': '保存失败'
                            })
                else:
                    results.append({
                        'input_path': file_path,
                        'success': False,
                        'message': '加载图片失败'
                    })

            except Exception as e:
                results.append({
                    'input_path': file_path,
                    'success': False,
                    'message': str(e)
                })

            self.progress.emit(int((i + 1) / len(self.files) * 100))

        self.finished.emit(results)


class FileListWidget(QListWidget):
    """支持拖放的文件列表控件"""

    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        self.setSelectionMode(QListWidget.ExtendedSelection)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """放置事件"""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                files.append(file_path)

        if files:
            self.files_dropped.emit(files)


class ImageCompressorApp(QMainWindow):
    """图片压缩器主应用程序"""

    def __init__(self):
        super().__init__()
        self.files: List[str] = []
        self.worker: Optional[CompressionWorker] = None
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('TinyPic - 图片压缩工具')
        self.setGeometry(100, 100, 1200, 800)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧：文件列表区域
        left_panel = self.create_file_list_panel()
        main_layout.addWidget(left_panel, stretch=2)

        # 右侧：设置区域
        right_panel = self.create_settings_panel()
        main_layout.addWidget(right_panel, stretch=1)

    def create_file_list_panel(self) -> QWidget:
        """创建文件列表面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 标题
        title_label = QLabel('图片文件列表')
        title_label.setStyleSheet('font-weight: bold; font-size: 14px;')
        layout.addWidget(title_label)

        # 文件列表（支持拖放）
        self.file_list = FileListWidget()
        self.file_list.files_dropped.connect(self.handle_files_dropped)
        layout.addWidget(self.file_list)

        # 按钮区域
        button_layout = QHBoxLayout()

        add_btn = QPushButton('添加文件')
        add_btn.clicked.connect(self.add_files)
        button_layout.addWidget(add_btn)

        add_folder_btn = QPushButton('添加文件夹')
        add_folder_btn.clicked.connect(self.add_folder)
        button_layout.addWidget(add_folder_btn)

        clear_btn = QPushButton('清空列表')
        clear_btn.clicked.connect(self.clear_files)
        button_layout.addWidget(clear_btn)

        layout.addLayout(button_layout)

        # 文件计数
        self.file_count_label = QLabel('已选择 0 个文件')
        layout.addWidget(self.file_count_label)

        return panel

    def create_settings_panel(self) -> QWidget:
        """创建设置面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # 压缩设置组
        compress_group = self.create_compress_settings()
        scroll_layout.addWidget(compress_group)

        # 格式设置组
        format_group = self.create_format_settings()
        scroll_layout.addWidget(format_group)

        # 尺寸设置组
        size_group = self.create_size_settings()
        scroll_layout.addWidget(size_group)

        # 输出设置组
        output_group = self.create_output_settings()
        scroll_layout.addWidget(output_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # 底部操作区域
        action_layout = QVBoxLayout()

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        action_layout.addWidget(self.progress_bar)

        # 压缩按钮
        self.compress_btn = QPushButton('开始压缩')
        self.compress_btn.setStyleSheet('font-size: 16px; padding: 10px;')
        self.compress_btn.clicked.connect(self.start_compression)
        action_layout.addWidget(self.compress_btn)

        layout.addLayout(action_layout)

        return panel

    def create_compress_settings(self) -> QGroupBox:
        """创建压缩设置组"""
        group = QGroupBox('压缩设置')
        layout = QVBoxLayout(group)

        # 压缩模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel('压缩模式:'))

        self.compress_mode = QComboBox()
        self.compress_mode.addItems(['按文件大小', '按质量'])
        self.compress_mode.currentIndexChanged.connect(self.on_compress_mode_changed)
        mode_layout.addWidget(self.compress_mode)

        layout.addLayout(mode_layout)

        # 目标大小设置
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel('目标大小 (KB):'))

        self.target_size_spin = QSpinBox()
        self.target_size_spin.setRange(1, 10000)
        self.target_size_spin.setValue(100)
        size_layout.addWidget(self.target_size_spin)

        layout.addLayout(size_layout)

        # 质量设置
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel('压缩质量:'))

        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(85)
        self.quality_spin.setEnabled(False)  # 默认禁用，按大小压缩
        quality_layout.addWidget(self.quality_spin)

        layout.addLayout(quality_layout)

        return group

    def create_format_settings(self) -> QGroupBox:
        """创建格式设置组"""
        group = QGroupBox('输出格式')
        layout = QVBoxLayout(group)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel('输出格式:'))

        self.format_combo = QComboBox()
        self.format_combo.addItems(['JPEG', 'PNG', 'WebP', 'BMP', 'GIF'])
        format_layout.addWidget(self.format_combo)

        layout.addLayout(format_layout)

        # 格式说明
        format_info = QLabel(
            'JPEG: 适合照片，文件小\nPNG: 支持透明，质量高\nWebP: 新格式，兼顾质量和大小')
        format_info.setStyleSheet('color: gray; font-size: 11px;')
        layout.addWidget(format_info)

        return group

    def create_size_settings(self) -> QGroupBox:
        """创建尺寸设置组"""
        group = QGroupBox('尺寸调整 (可选)')
        layout = QVBoxLayout(group)

        # 宽度设置
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel('宽度 (px):'))

        self.width_spin = QSpinBox()
        self.width_spin.setRange(0, 10000)
        self.width_spin.setValue(0)
        self.width_spin.setSpecialValueText('自动')
        width_layout.addWidget(self.width_spin)

        layout.addLayout(width_layout)

        # 高度设置
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel('高度 (px):'))

        self.height_spin = QSpinBox()
        self.height_spin.setRange(0, 10000)
        self.height_spin.setValue(0)
        self.height_spin.setSpecialValueText('自动')
        height_layout.addWidget(self.height_spin)

        layout.addLayout(height_layout)

        # 保持宽高比
        self.keep_ratio_check = QCheckBox('保持宽高比')
        self.keep_ratio_check.setChecked(True)
        layout.addWidget(self.keep_ratio_check)

        return group

    def create_output_settings(self) -> QGroupBox:
        """创建输出设置组"""
        group = QGroupBox('输出设置')
        layout = QVBoxLayout(group)

        # 输出路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel('保存位置:'))

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText('选择输出目录...')
        path_layout.addWidget(self.output_path_edit)

        browse_btn = QPushButton('浏览...')
        browse_btn.clicked.connect(self.browse_output_dir)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # 使用原目录选项
        self.use_source_dir_check = QCheckBox('使用源文件目录')
        self.use_source_dir_check.setChecked(True)
        self.use_source_dir_check.stateChanged.connect(self.on_use_source_dir_changed)
        layout.addWidget(self.use_source_dir_check)

        return group

    def on_compress_mode_changed(self, index: int):
        """压缩模式改变时的响应"""
        # 0: 按文件大小, 1: 按质量
        self.target_size_spin.setEnabled(index == 0)
        self.quality_spin.setEnabled(index == 1)

    def on_use_source_dir_changed(self, state: int):
        """使用源目录选项改变时的响应"""
        self.output_path_edit.setEnabled(state == Qt.Unchecked)

    def add_files(self):
        """添加文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, '选择图片文件', '',
            '图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tiff);;所有文件 (*.*)'
        )
        if files:
            self.add_files_to_list(files)

    def add_folder(self):
        """添加文件夹"""
        folder = QFileDialog.getExistingDirectory(self, '选择文件夹')
        if folder:
            # 获取文件夹中的所有图片文件
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.bmp', '*.gif', '*.tiff', '*.tif']:
                image_files.extend(Path(folder).glob(ext))

            if image_files:
                self.add_files_to_list([str(f) for f in image_files])
            else:
                QMessageBox.information(self, '提示', '所选文件夹中没有找到图片文件')

    def handle_files_dropped(self, files: List[str]):
        """处理拖放的文件"""
        valid_files = validate_image_files(files)
        if valid_files:
            self.add_files_to_list(valid_files)
        else:
            QMessageBox.warning(self, '警告', '没有找到有效的图片文件')

    def add_files_to_list(self, files: List[str]):
        """添加文件到列表"""
        for file_path in files:
            if file_path not in self.files:
                self.files.append(file_path)
                item = QListWidgetItem(os.path.basename(file_path))
                item.setData(Qt.UserRole, file_path)
                self.file_list.addItem(item)

        self.update_file_count()

    def clear_files(self):
        """清空文件列表"""
        self.files.clear()
        self.file_list.clear()
        self.update_file_count()

    def update_file_count(self):
        """更新文件计数"""
        self.file_count_label.setText(f'已选择 {len(self.files)} 个文件')

    def browse_output_dir(self):
        """浏览输出目录"""
        directory = QFileDialog.getExistingDirectory(self, '选择输出目录')
        if directory:
            self.output_path_edit.setText(directory)

    def get_output_directory(self) -> str:
        """获取输出目录"""
        if self.use_source_dir_check.isChecked() and self.files:
            return os.path.dirname(self.files[0])
        return self.output_path_edit.text() or os.path.expanduser('~')

    def start_compression(self):
        """开始压缩"""
        if not self.files:
            QMessageBox.warning(self, '警告', '请先添加要压缩的图片文件')
            return

        # 获取设置
        settings = {
            'mode': self.compress_mode.currentIndex(),
            'target_size_kb': self.target_size_spin.value() if self.compress_mode.currentIndex() == 0 else None,
            'quality': self.quality_spin.value() if self.compress_mode.currentIndex() == 1 else 85,
            'format': self.format_combo.currentText(),
            'width': self.width_spin.value() if self.width_spin.value() > 0 else None,
            'height': self.height_spin.value() if self.height_spin.value() > 0 else None,
            'keep_aspect_ratio': self.keep_ratio_check.isChecked()
        }

        output_dir = self.get_output_directory()

        # 禁用界面
        self.compress_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        # 启动工作线程
        self.worker = CompressionWorker(self.files.copy(), output_dir, settings)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_compression_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_progress(self, value: int):
        """进度更新"""
        self.progress_bar.setValue(value)

    def on_compression_finished(self, results: List[dict]):
        """压缩完成"""
        self.compress_btn.setEnabled(True)
        self.progress_bar.setValue(100)

        # 统计结果
        success_count = sum(1 for r in results if r.get('success'))
        fail_count = len(results) - success_count

        # 显示结果
        if fail_count == 0:
            message = f'压缩完成！成功处理 {success_count} 个文件'
        else:
            message = f'压缩完成！成功 {success_count} 个，失败 {fail_count} 个'

        # 询问是否打开输出目录
        reply = QMessageBox.question(
            self, '压缩完成', f'{message}\n\n是否打开输出目录？',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            output_dir = self.get_output_directory()
            os.startfile(output_dir)

        # 如果有成功的文件，询问是否预览
        if success_count > 0:
            reply = QMessageBox.question(
                self, '预览', '是否预览压缩效果？',
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 找到第一个成功的文件进行预览
                for result in results:
                    if result.get('success'):
                        preview_dialog = PreviewDialog(
                            result['input_path'],
                            result['output_path'],
                            self
                        )
                        preview_dialog.exec_()
                        break

    def on_error(self, error_msg: str):
        """错误处理"""
        self.compress_btn.setEnabled(True)
        QMessageBox.critical(self, '错误', f'压缩过程出错: {error_msg}')


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格

    # 设置应用信息
    app.setApplicationName('TinyPic')
    app.setApplicationVersion('1.0.0')

    # 创建并显示主窗口
    window = ImageCompressorApp()
    window.show()

    sys.exit(app.exec_())