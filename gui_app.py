# -*- encoding=utf8 -*-
__author__ = "x"

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import os
from datetime import datetime, timedelta
import schedule
from loguru import logger
import sys
import subprocess

# 导入原有的模块
from main import MCCAA, DeviceManager


class MCCAAGUIApp:
    """
    MCCAA游戏脚本GUI应用
    提供任务按钮执行和定时任务功能
    """
    
    def __init__(self, root):
        """
        初始化GUI应用
        
        :param root: tkinter根窗口
        """
        self.root = root
        self.root.title("MCCAA游戏脚本管理器")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 任务列表定义
        self.task_definitions = {
            "start": "启动游戏",
            "exercise": "演习", 
            "change": "合成黑匣",
            "trade": "换票",
            "task": "领取日常任务"
        }
        
        # 设备管理器和游戏实例
        self.device_manager = None
        self.mccaa_instance = None
        self.is_device_connected = False
        
        # 定时任务相关
        self.scheduler_thread = None
        self.is_scheduler_running = False
        self.selected_tasks = []
        self.timer_interval = 60  # 默认60分钟
        
        # 创建GUI界面
        self.create_widgets()
        
        # 设置日志输出到GUI
        self.setup_logging()
        
    def create_widgets(self):
        """
        创建GUI组件
        """
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左右分割的PanedWindow
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 左侧功能区域（带滚动条）
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)
        
        # 创建滚动区域
        canvas = tk.Canvas(left_frame, width=400)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 鼠标滚轮绑定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 右侧日志区域
        right_frame = ttk.LabelFrame(paned_window, text="运行日志", padding="5")
        paned_window.add(right_frame, weight=1)
        
        # 日志显示区域
        log_frame = ttk.Frame(right_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=20, 
            width=50,
            state="disabled",
            wrap=tk.WORD,
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 日志控制按钮
        log_control_frame = ttk.Frame(right_frame)
        log_control_frame.pack(fill=tk.X)
        
        ttk.Button(log_control_frame, text="清除日志", command=self.clear_log).pack(side=tk.LEFT)
        
        # 在滚动区域内创建功能组件
        self.create_function_widgets()
        
        # 设置初始分割比例（左侧60%，右侧40%）
        self.root.after(100, lambda: paned_window.sashpos(0, 480))
        
    def create_function_widgets(self):
        """
        在滚动区域内创建功能组件
        """
        # 设备连接区域
        device_frame = ttk.LabelFrame(self.scrollable_frame, text="设备连接", padding="5")
        device_frame.pack(fill=tk.X, pady=(0, 10))
        
        device_control_frame = ttk.Frame(device_frame)
        device_control_frame.pack(fill=tk.X)
        
        self.connect_btn = ttk.Button(device_control_frame, text="连接设备", command=self.connect_device)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.device_status_label = ttk.Label(device_control_frame, text="设备未连接", foreground="red")
        self.device_status_label.pack(side=tk.LEFT)
        
        # 任务执行区域
        task_frame = ttk.LabelFrame(self.scrollable_frame, text="任务执行", padding="5")
        task_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 创建任务按钮网格
        task_grid_frame = ttk.Frame(task_frame)
        task_grid_frame.pack(fill=tk.X)
        
        # 配置列权重
        task_grid_frame.columnconfigure(0, weight=1)
        task_grid_frame.columnconfigure(1, weight=1)
        
        # 创建任务按钮
        for i, (task_key, task_name) in enumerate(self.task_definitions.items()):
            btn = ttk.Button(task_grid_frame, text=task_name, 
                           command=lambda key=task_key: self.execute_single_task(key))
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # 执行所有任务按钮
        all_tasks_btn = ttk.Button(task_frame, text="执行所有任务", 
                                 command=self.execute_all_tasks)
        all_tasks_btn.pack(fill=tk.X, padx=5, pady=(10, 0))
        
        # 定时任务区域
        timer_frame = ttk.LabelFrame(self.scrollable_frame, text="定时任务", padding="5")
        timer_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 任务选择
        ttk.Label(timer_frame, text="选择定时执行的任务:").pack(anchor=tk.W, pady=(0, 5))
        
        # 任务选择网格
        task_select_frame = ttk.Frame(timer_frame)
        task_select_frame.pack(fill=tk.X)
        task_select_frame.columnconfigure(0, weight=1)
        task_select_frame.columnconfigure(1, weight=1)
        
        self.task_vars = {}
        for i, (task_key, task_name) in enumerate(self.task_definitions.items()):
            var = tk.BooleanVar()
            self.task_vars[task_key] = var
            cb = ttk.Checkbutton(task_select_frame, text=task_name, variable=var)
            cb.grid(row=i//2, column=i%2, sticky=tk.W, padx=5, pady=2)
        
        # 时间间隔设置
        interval_frame = ttk.Frame(timer_frame)
        interval_frame.pack(fill=tk.X, pady=(10, 5))
        
        ttk.Label(interval_frame, text="执行间隔:").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value="60")
        interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=10)
        interval_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Label(interval_frame, text="分钟").pack(side=tk.LEFT)
        
        # 定时任务控制按钮
        timer_control_frame = ttk.Frame(timer_frame)
        timer_control_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.start_timer_btn = ttk.Button(timer_control_frame, text="开始定时任务", 
                                        command=self.start_timer)
        self.start_timer_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_timer_btn = ttk.Button(timer_control_frame, text="停止定时任务", 
                                       command=self.stop_timer, state="disabled")
        self.stop_timer_btn.pack(side=tk.LEFT)
        
        # 状态显示
        self.timer_status_label = ttk.Label(timer_frame, text="定时任务未启动")
        self.timer_status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 预留扩展区域示例
        future_frame = ttk.LabelFrame(self.scrollable_frame, text="扩展功能", padding="5")
        future_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(future_frame, text="这里可以添加更多功能...", foreground="gray").pack(anchor=tk.W)
        

        
    def setup_logging(self):
        """
        设置日志输出到GUI
        """
        # 移除默认的logger处理器
        logger.remove()
        
        # 添加GUI日志处理器
        logger.add(self.log_to_gui, format="{time:HH:mm:ss} | {level} | {message}")
        
        # 同时输出到控制台（可选）
        logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
        
    def log_to_gui(self, message):
        """
        将日志消息输出到GUI
        
        :param message: 日志消息
        """
        def append_log():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, message + "\n")
            
            # 限制日志行数为20行
            lines = self.log_text.get("1.0", tk.END).split("\n")
            if len(lines) > 21:  # 21是因为最后有一个空行
                # 删除最旧的行
                excess_lines = len(lines) - 21
                for _ in range(excess_lines):
                    self.log_text.delete("1.0", "2.0")
            
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
            
        # 确保在主线程中更新GUI
        self.root.after(0, append_log)
        
    def clear_log(self):
        """
        清除日志显示
        """
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
        
    def get_adb_devices(self):
        """
        获取当前可用的ADB设备列表
        
        :return: 设备列表，格式为[(设备ID, 设备状态), ...]
        """
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                logger.error("ADB命令执行失败，请确保ADB已正确安装并添加到环境变量")
                return []
            
            lines = result.stdout.strip().split('\n')
            devices = []
            
            for line in lines[1:]:  # 跳过第一行标题
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        device_id = parts[0].strip()
                        status = parts[1].strip()
                        if status == 'device':  # 只返回正常连接的设备
                            devices.append((device_id, status))
            
            return devices
        except FileNotFoundError:
            logger.error("未找到ADB命令，请确保ADB已正确安装并添加到环境变量")
            return []
        except Exception as e:
            logger.error(f"获取ADB设备列表失败: {e}")
            return []
    
    def show_device_selection_dialog(self):
        """
        显示设备选择对话框
        
        :return: 选择的设备ID，如果取消选择则返回None
        """
        # 获取可用设备
        devices = self.get_adb_devices()
        
        if not devices:
            messagebox.showerror("错误", 
                               "未找到可用的ADB设备，请确保：\n"
                               "1. 设备已连接并开启USB调试\n"
                               "2. ADB驱动已正确安装\n"
                               "3. 已授权ADB调试权限")
            return None
        
        # 检查是否有保存的设备配置
        device_manager = DeviceManager()
        last_device = device_manager.config.get('last_device')
        
        # 创建设备选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("选择设备")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        selected_device = None
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 如果有上次使用的设备，显示提示
        if last_device:
            device_ids = [device[0] for device in devices]
            if last_device in device_ids:
                last_frame = ttk.LabelFrame(main_frame, text="上次使用的设备", padding="5")
                last_frame.pack(fill=tk.X, pady=(0, 10))
                
                ttk.Label(last_frame, text=f"设备: {last_device}").pack(anchor=tk.W)
                
                def use_last_device():
                    nonlocal selected_device
                    selected_device = last_device
                    dialog.destroy()
                
                ttk.Button(last_frame, text="使用此设备", command=use_last_device).pack(pady=(5, 0))
        
        # 设备列表
        list_frame = ttk.LabelFrame(main_frame, text="可用设备列表", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建列表框
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        listbox = tk.Listbox(listbox_frame, height=6)
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充设备列表
        for device_id, status in devices:
            listbox.insert(tk.END, f"{device_id} ({status})")
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def on_select():
            nonlocal selected_device
            selection = listbox.curselection()
            if selection:
                selected_device = devices[selection[0]][0]
                dialog.destroy()
            else:
                messagebox.showwarning("警告", "请选择一个设备")
        
        def on_cancel():
            nonlocal selected_device
            selected_device = None
            dialog.destroy()
        
        ttk.Button(button_frame, text="选择", command=on_select).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT)
        
        # 双击选择
        def on_double_click(event):
            on_select()
        
        listbox.bind('<Double-Button-1>', on_double_click)
        
        # 等待对话框关闭
        dialog.wait_window()
        
        return selected_device
    
    def connect_device(self):
        """
        连接设备
        """
        def connect_thread():
            try:
                # 显示设备选择对话框
                selected_device = self.show_device_selection_dialog()
                
                if not selected_device:
                    logger.info("用户取消了设备选择")
                    return
                
                # 创建设备管理器并保存选择的设备
                self.device_manager = DeviceManager()
                self.device_manager.config['last_device'] = selected_device
                self.device_manager.save_config()
                
                # 连接设备
                if 'emulator' in selected_device:
                    connect_string = f"Android:///{selected_device}"
                else:
                    connect_string = f"Android:///{selected_device}"
                
                logger.info(f"正在连接设备: {connect_string}")
                
                # 导入airtest连接函数
                from airtest.core.api import connect_device
                connect_device(connect_string)
                
                # 创建游戏实例
                self.mccaa_instance = MCCAA()
                self.is_device_connected = True
                
                # 更新UI状态
                self.root.after(0, lambda: (
                    self.device_status_label.config(text=f"设备已连接: {selected_device}", foreground="green"),
                    self.connect_btn.config(text="重新连接")
                ))
                
                logger.info(f"设备连接成功: {selected_device}")
                
            except Exception as e:
                logger.error(f"连接设备时发生错误: {e}")
                # 更新UI状态显示错误
                self.root.after(0, lambda: (
                    self.device_status_label.config(text="设备连接失败", foreground="red"),
                    self.connect_btn.config(text="连接设备")
                ))
                
        # 在后台线程中执行连接
        threading.Thread(target=connect_thread, daemon=True).start()
        
    def execute_single_task(self, task_key):
        """
        执行单个任务
        
        :param task_key: 任务键名
        """
        if not self.is_device_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        def task_thread():
            try:
                logger.info(f"开始执行任务: {self.task_definitions[task_key]}")
                self.mccaa_instance.main([task_key])
                logger.info(f"任务 {self.task_definitions[task_key]} 执行完成")
            except Exception as e:
                logger.error(f"执行任务 {self.task_definitions[task_key]} 时发生错误: {e}")
                
        threading.Thread(target=task_thread, daemon=True).start()
        
    def execute_all_tasks(self):
        """
        执行所有任务
        """
        if not self.is_device_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        def all_tasks_thread():
            try:
                all_tasks = list(self.task_definitions.keys())
                logger.info("开始执行所有任务")
                self.mccaa_instance.main(all_tasks)
                logger.info("所有任务执行完成")
            except Exception as e:
                logger.error(f"执行所有任务时发生错误: {e}")
                
        threading.Thread(target=all_tasks_thread, daemon=True).start()
        
    def start_timer(self):
        """
        开始定时任务
        """
        if not self.is_device_connected:
            messagebox.showwarning("警告", "请先连接设备")
            return
            
        # 获取选中的任务
        selected_tasks = [task_key for task_key, var in self.task_vars.items() if var.get()]
        
        if not selected_tasks:
            messagebox.showwarning("警告", "请至少选择一个任务")
            return
            
        try:
            interval = int(self.interval_var.get())
            if interval <= 0:
                raise ValueError("间隔时间必须大于0")
        except ValueError as e:
            messagebox.showerror("错误", f"无效的时间间隔: {e}")
            return
            
        self.selected_tasks = selected_tasks
        self.timer_interval = interval
        self.is_scheduler_running = True
        
        # 更新UI状态
        self.start_timer_btn.config(state="disabled")
        self.stop_timer_btn.config(state="normal")
        
        # 启动定时器线程
        self.scheduler_thread = threading.Thread(target=self.scheduler_worker, daemon=True)
        self.scheduler_thread.start()
        
        task_names = [self.task_definitions[task] for task in selected_tasks]
        status_text = f"定时任务已启动 - 任务: {', '.join(task_names)} - 间隔: {interval}分钟"
        self.timer_status_label.config(text=status_text)
        
        logger.info(f"定时任务已启动，将每{interval}分钟执行: {', '.join(task_names)}")
        
    def stop_timer(self):
        """
        停止定时任务
        """
        self.is_scheduler_running = False
        
        # 更新UI状态
        self.start_timer_btn.config(state="normal")
        self.stop_timer_btn.config(state="disabled")
        self.timer_status_label.config(text="定时任务已停止")
        
        logger.info("定时任务已停止")
        
    def scheduler_worker(self):
        """
        定时任务工作线程
        """
        next_run_time = time.time() + (self.timer_interval * 60)
        
        while self.is_scheduler_running:
            current_time = time.time()
            
            if current_time >= next_run_time:
                try:
                    task_names = [self.task_definitions[task] for task in self.selected_tasks]
                    logger.info(f"定时执行任务: {', '.join(task_names)}")
                    
                    self.mccaa_instance.main(self.selected_tasks)
                    
                    logger.info("定时任务执行完成")
                    
                    # 计算下次执行时间
                    next_run_time = current_time + (self.timer_interval * 60)
                    
                except Exception as e:
                    logger.error(f"定时任务执行失败: {e}")
                    # 即使出错也要更新下次执行时间
                    next_run_time = current_time + (self.timer_interval * 60)
            
            # 更新状态显示
            if self.is_scheduler_running:
                remaining_time = max(0, int(next_run_time - current_time))
                remaining_minutes = remaining_time // 60
                remaining_seconds = remaining_time % 60
                
                task_names = [self.task_definitions[task] for task in self.selected_tasks]
                status_text = f"定时任务运行中 - 任务: {', '.join(task_names)} - 下次执行: {remaining_minutes:02d}:{remaining_seconds:02d}"
                
                self.root.after(0, lambda: self.timer_status_label.config(text=status_text))
            
            time.sleep(1)  # 每秒检查一次
            
    def on_closing(self):
        """
        窗口关闭事件处理
        """
        if self.is_scheduler_running:
            if messagebox.askokcancel("确认", "定时任务正在运行，确定要退出吗？"):
                self.is_scheduler_running = False
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    """
    主函数，启动GUI应用
    """
    root = tk.Tk()
    app = MCCAAGUIApp(root)
    
    # 设置窗口关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 启动GUI主循环
    root.mainloop()


if __name__ == "__main__":
    main()