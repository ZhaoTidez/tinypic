import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import os
import threading

class ImageCompressor:
    def __init__(self, root):
        self.root = root
        self.root.title("图片压缩工具")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # 初始化变量
        self.input_file = ""
        self.output_file = ""
        self.target_size = tk.IntVar(value=100)  # 默认100KB
        self.quality = tk.IntVar(value=85)  # 默认质量85%
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面
        self.create_widgets()
        
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("Title.TLabel", font=("Arial", 12, "bold"))
        style.configure("Normal.TLabel", font=("Arial", 10))
        
    def create_widgets(self):
        """创建界面组件"""
        # 标题
        title_label = ttk.Label(self.root, text="图片压缩工具", style="Title.TLabel")
        title_label.pack(pady=10)
        
        # 输入文件选择区域
        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(input_frame, text="选择图片文件:").grid(row=0, column=0, sticky="w")
        self.input_entry = ttk.Entry(input_frame, width=40)
        self.input_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        
        input_btn = ttk.Button(input_frame, text="浏览", command=self.select_input_file)
        input_btn.grid(row=1, column=1)
        
        # 压缩设置区域
        settings_frame = ttk.LabelFrame(self.root, text="压缩设置")
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        # 目标大小设置
        ttk.Label(settings_frame, text="目标大小 (KB):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        size_scale = ttk.Scale(settings_frame, from_=10, to=1000, variable=self.target_size, orient="horizontal")
        size_scale.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        self.size_label = ttk.Label(settings_frame, text="100 KB")
        self.size_label.grid(row=0, column=2, padx=10, pady=5)
        
        # 质量设置
        ttk.Label(settings_frame, text="图片质量 (%):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        quality_scale = ttk.Scale(settings_frame, from_=10, to=100, variable=self.quality, orient="horizontal")
        quality_scale.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        self.quality_label = ttk.Label(settings_frame, text="85%")
        self.quality_label.grid(row=1, column=2, padx=10, pady=5)
        
        # 输出文件选择区域
        output_frame = ttk.Frame(self.root)
        output_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(output_frame, text="输出文件:").grid(row=0, column=0, sticky="w")
        self.output_entry = ttk.Entry(output_frame, width=40)
        self.output_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        
        output_btn = ttk.Button(output_frame, text="浏览", command=self.select_output_file)
        output_btn.grid(row=1, column=1)
        
        # 进度条
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=460, mode="determinate")
        self.progress.pack(pady=10)
        
        # 状态标签
        self.status_label = ttk.Label(self.root, text="准备就绪")
        self.status_label.pack(pady=5)
        
        # 按钮区域
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20)
        
        compress_btn = ttk.Button(button_frame, text="开始压缩", command=self.start_compression)
        compress_btn.grid(row=0, column=0, padx=10)
        
        reset_btn = ttk.Button(button_frame, text="重置", command=self.reset)
        reset_btn.grid(row=0, column=1, padx=10)
        
        # 绑定事件
        size_scale.configure(command=self.update_size_label)
        quality_scale.configure(command=self.update_quality_label)
        
        # 配置网格权重
        input_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        settings_frame.columnconfigure(1, weight=1)
        
    def select_input_file(self):
        """选择输入文件"""
        filetypes = [
            ("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
            ("所有文件", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="选择要压缩的图片",
            filetypes=filetypes
        )
        
        if filename:
            self.input_file = filename
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filename)
            
            # 自动设置输出文件名
            name, ext = os.path.splitext(filename)
            self.output_file = f"{name}_compressed{ext}"
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, self.output_file)
            
    def select_output_file(self):
        """选择输出文件"""
        if not self.input_file:
            messagebox.showwarning("警告", "请先选择输入文件")
            return
            
        filetypes = [
            ("JPEG文件", "*.jpg *.jpeg"),
            ("PNG文件", "*.png"),
            ("所有文件", "*.*")
        ]
        
        filename = filedialog.asksaveasfilename(
            title="保存压缩后的图片",
            defaultextension=".jpg",
            filetypes=filetypes,
            initialfile=os.path.basename(self.output_file)
        )
        
        if filename:
            self.output_file = filename
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, filename)
            
    def update_size_label(self, value):
        """更新大小标签"""
        self.size_label.config(text=f"{int(float(value))} KB")
        
    def update_quality_label(self, value):
        """更新质量标签"""
        self.quality_label.config(text=f"{int(float(value))}%")
        
    def start_compression(self):
        """开始压缩"""
        if not self.input_file:
            messagebox.showwarning("警告", "请选择要压缩的图片文件")
            return
            
        if not self.output_file:
            messagebox.showwarning("警告", "请设置输出文件路径")
            return
            
        # 在新线程中执行压缩，避免界面卡顿
        thread = threading.Thread(target=self.compress_image)
        thread.daemon = True
        thread.start()
        
    def compress_image(self):
        """压缩图片的核心逻辑"""
        try:
            self.update_status("正在加载图片...")
            self.progress["value"] = 10
            
            # 打开图片
            with Image.open(self.input_file) as img:
                # 转换模式为RGB（处理RGBA等模式）
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                self.update_status("正在计算压缩参数...")
                self.progress["value"] = 30
                
                # 获取目标大小（字节）
                target_size_bytes = self.target_size.get() * 1024
                
                # 初始质量设置
                quality = self.quality.get()
                
                self.update_status("正在压缩图片...")
                self.progress["value"] = 60
                
                # 保存图片
                img.save(self.output_file, quality=quality, optimize=True)
                
                # 检查文件大小
                current_size = os.path.getsize(self.output_file)
                
                # 如果文件仍然太大，进行二次压缩
                if current_size > target_size_bytes:
                    self.update_status("进行二次优化...")
                    self.progress["value"] = 80
                    
                    # 逐步降低质量直到达到目标大小
                    while current_size > target_size_bytes and quality > 10:
                        quality -= 5
                        img.save(self.output_file, quality=quality, optimize=True)
                        current_size = os.path.getsize(self.output_file)
                
                self.progress["value"] = 100
                self.update_status("压缩完成!")
                
                # 显示压缩结果
                original_size = os.path.getsize(self.input_file)
                compression_ratio = (original_size - current_size) / original_size * 100
                
                messagebox.showinfo(
                    "压缩完成",
                    f"压缩成功!\n\n"
                    f"原文件大小: {original_size/1024:.1f} KB\n"
                    f"压缩后大小: {current_size/1024:.1f} KB\n"
                    f"压缩率: {compression_ratio:.1f}%\n"
                    f"输出文件: {self.output_file}"
                )
                
        except Exception as e:
            self.update_status("压缩失败")
            messagebox.showerror("错误", f"压缩过程中出现错误:\n{str(e)}")
            self.progress["value"] = 0
            
    def update_status(self, message):
        """更新状态标签（线程安全）"""
        def update():
            self.status_label.config(text=message)
            self.root.update_idletasks()
            
        self.root.after(0, update)
        
    def reset(self):
        """重置界面"""
        self.input_file = ""
        self.output_file = ""
        self.input_entry.delete(0, tk.END)
        self.output_entry.delete(0, tk.END)
        self.target_size.set(100)
        self.quality.set(85)
        self.progress["value"] = 0
        self.update_status("准备就绪")
        self.update_size_label(100)
        self.update_quality_label(85)

def main():
    """主函数"""
    root = tk.Tk()
    app = ImageCompressor(root)
    root.mainloop()

if __name__ == "__main__":
    main()