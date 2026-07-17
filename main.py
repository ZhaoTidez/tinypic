"""
TinyPic - 图片压缩工具
主程序入口

功能特性:
- 图片压缩: 支持按文件大小或质量压缩
- 格式转换: 支持JPEG、PNG、WebP、BMP、GIF等格式
- 尺寸调整: 自定义宽度和高度，支持保持宽高比
- 批量处理: 支持同时处理多个图片文件
- 预览对比: 压缩前后图片对比预览
- 拖放支持: 支持文件和文件夹拖放添加
- 进度显示: 实时显示处理进度
"""

import sys
import os

# 确保能找到项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import main

if __name__ == '__main__':
    main()