# -*- encoding=utf8 -*-
"""
启动脚本 - 直接运行MCCAA GUI应用
"""

import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    # 导入并运行GUI应用
    from gui_app import main
    
    if __name__ == "__main__":
        print("启动MCCAA游戏脚本管理器...")
        main()
        
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保已安装所有必需的依赖包")
    print("可以运行以下命令安装依赖:")
    print("pip install -r requirements.txt")
    input("按回车键退出...")
except Exception as e:
    print(f"启动应用时发生错误: {e}")
    input("按回车键退出...")