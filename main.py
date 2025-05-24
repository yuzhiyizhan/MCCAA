# -*- encoding=utf8 -*-
__author__ = "x"

import re
import threading
import time
import json
import os
import subprocess

from concurrent.futures import ThreadPoolExecutor
import traceback
import Levenshtein
from airtest.core.api import snapshot, touch, wait, Template, G, connect_device, ST, start_app, stop_app
from loguru import logger
from paddleocr import PaddleOCR
from PIL import Image
from my_tools import Tools


def debugOcr():
    pic_path = r"images/now.png"
    snapshot(pic_path)
    ocr = PaddleOCR(use_angle_cls=True, lang="ch")
    ocr_result = ocr.ocr(pic_path, cls=True)
    for line in ocr_result:
        for word_info in line:
            # 获取识别结果的文字信息
            textinfo = word_info[1][0]
            x1, y1 = word_info[0][0]
            x2, y2 = word_info[0][2]
            target_coords = ((x1 + x2) / 2, (y1 + y2) / 2)
            logger.debug(f"{textinfo}: {target_coords}")


def cropped_image(x1, y1, x2, y2):
    pic_path = r"images/now.png"
    snapshot(pic_path)

    # 新增：图片裁剪逻辑（需根据实际需求调整裁剪坐标）

    # 读取原始图片
    img = Image.open(pic_path)
    # 定义裁剪区域（左上角x, 左上角y, 宽度, 高度），需根据实际屏幕区域调整
    # 示例：裁剪屏幕中间 500x500 的区域（左上角坐标(290,710)，宽度500，高度500）

    cropped_img = img.crop((x1, y1, x1 + x2, y1 + y2))
    # 保存裁剪后的图片
    cropped_path = r"./cropped_now.png"
    cropped_img.save(cropped_path)


class DeviceManager:
    """
    设备管理类，用于处理ADB设备的选择和配置保存
    """
    def __init__(self, config_file="device_config.json"):
        """
        初始化设备管理器
        
        :param config_file: 配置文件路径，默认为device_config.json
        """
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """
        加载设备配置文件
        
        :return: 配置字典，如果文件不存在则返回空字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                return {}
        return {}
    
    def save_config(self):
        """
        保存设备配置到文件
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已保存到 {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
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
    
    def select_device(self):
        """
        让用户选择要连接的设备
        
        :return: 选择的设备ID，如果取消选择则返回None
        """
        # 检查是否有保存的设备配置
        if 'last_device' in self.config:
            last_device = self.config['last_device']
            print(f"\n上次使用的设备: {last_device}")

            # 验证设备是否仍然可用
            devices = self.get_adb_devices()
            device_ids = [device[0] for device in devices]
            if last_device in device_ids:
                logger.info(f"使用上次保存的设备: {last_device}")
                return last_device
            else:
                print(f"上次的设备 {last_device} 当前不可用，请重新选择")
        
        # 获取当前可用设备
        devices = self.get_adb_devices()
        
        if not devices:
            print("\n未找到可用的ADB设备，请确保：")
            print("1. 设备已连接并开启USB调试")
            print("2. ADB驱动已正确安装")
            print("3. 已授权ADB调试权限")
            return None
        
        print("\n可用的ADB设备:")
        for i, (device_id, status) in enumerate(devices, 1):
            print(f"{i}. {device_id} ({status})")
        
        while True:
            try:
                choice = input(f"\n请选择设备 (1-{len(devices)}, 输入0取消): ").strip()
                if choice == '0':
                    return None
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(devices):
                    selected_device = devices[choice_num - 1][0]
                    
                    # 保存选择的设备
                    self.config['last_device'] = selected_device
                    self.save_config()
                    
                    logger.info(f"已选择设备: {selected_device}")
                    return selected_device
                else:
                    print(f"请输入1到{len(devices)}之间的数字")
            except ValueError:
                print("请输入有效的数字")
            except KeyboardInterrupt:
                print("\n操作已取消")
                return None
    
    def connect_device(self):
        """
        连接选择的设备
        
        :return: 连接成功返回True，失败返回False
        """
        device_id = self.select_device()
        if not device_id:
            logger.error("未选择设备，程序退出")
            return False
        
        try:
            # 构建连接字符串
            if 'emulator' in device_id:
                connect_string = f"Android:///{device_id}"
            else:
                connect_string = f"Android:///{device_id}"
            
            logger.info(f"正在连接设备: {connect_string}")
            connect_device(connect_string)
            logger.info("设备连接成功")
            return True
        except Exception as e:
            logger.error(f"设备连接失败: {e}")
            return False


# 空白点 600，500
class MCCAA(object):
    def __init__(self):
        self.tools = Tools()
        self.COMMON_COORDINATES = {
            'blank_point': (600, 500),  # 空白点
            'purchase_count_point': (220, 50)  # home点的位置
        }

    def start(self):
        """
        启动游戏并完成初始引导流程
        
        流程说明：
        1. 启动游戏应用（包名：com.megagame.crosscore.bilibili）
        2. 等待"开始游戏"按钮出现（最长等待180秒）
        3. 关闭"今天不再提示"弹窗（2次）
        4. 点击"签到"按钮完成每日签到
        5. 关闭流程结束提示（break图片）
        """
        start_app("com.megagame.crosscore.bilibili")
        self.tools.click_txt("开始游戏", timeout=180)
        self.tools.click_txt_le("今天不再提示", timeout=50)
        self.tools.click_image("x", threshold=0.6)
        self.tools.click_txt_le("今天不再提示", timeout=10)
        self.tools.click_image("x", threshold=0.6)
        self.tools.click_txt("签到")
        self.tools.click_image("break", threshold=0.6)

    def task(self):
        """
        领取日常任务
        :return:
        """
        self.tools.click_txt("任务")
        self.tools.click_txt("日常")
        self.tools.click_txt_le("一键领取")
        # s
        touch(self.COMMON_COORDINATES['blank_point'])
        self.tools.click_txt("周常")
        self.tools.click_txt_le("一键领取")
        # s
        touch(self.COMMON_COORDINATES['blank_point'])
        self.tools.click_image("home")
        self.tools.click_txt("勘探指南")
        self.tools.click_txt("任务")
        self.tools.click_txt("每日任务")
        self.tools.click_txt("领取奖励")
        self.tools.click_txt("获得物品")
        self.tools.click_txt("每周任务")
        self.tools.click_txt("领取奖励")
        self.tools.click_txt("获得物品")
        self.tools.click_txt("本期任务")
        self.tools.click_txt("领取奖励")
        self.tools.click_txt("获得物品")
        touch(self.COMMON_COORDINATES['purchase_count_point'])
        data = self.tools.exists_txt("全部领取")
        if data:
            self.tools.click_txt("全部领取")
            self.tools.click_txt("获得物品")
        self.tools.click_image("home")



    def exercise(self):
        """
        演习
        :return:
        """
        self.tools.click_txt("出击")
        self.tools.click_txt("模拟军演")
        self.tools.click_txt("镜像竞技")

        # for i in range(10):
        while True:
            self.tools.exists_ocr("战力")
            data = self.tools.get_ocr_cropped_result(cropped=[1022, 150, 82, 23])[0]
            power, coordinate = data.popitem()
            if int(power) > 30000:
                self.tools.click_image("refresh", threshold=0.6)
                continue
            else:
                touch(coordinate)
                if self.tools.exists_ocr("今日可购买的模拟次数", timeout=3):
                    touch(self.COMMON_COORDINATES['purchase_count_point'])
                    self.tools.click_image("home")
                    return
                self.tools.click_txt("挑战")
                self.tools.click_txt("战斗胜利", timeout=120, click_timeout=2)
                self.tools.click_txt("获得物品")

    def trade(self):
        """
        换票
        :return:
        """
        self.tools.click_txt("基地")

        self.tools.exists_image("trade", threshold=0.9)
        self.tools.click_image("trade", threshold=0.9)

        def touch_money():
            data = self.tools.exists_ocr("构建订单", timeout=3)
            if data:
                tempList = list(data)
                tempList[1] += 200
                data = tuple(tempList)
                touch(data)
                if self.tools.exists_ocr("订单兑换所需素材不足", timeout=3):
                    return False
                self.tools.click_txt("确定", timeout=3)
                self.tools.click_txt("获得物品", timeout=3)

        touch_money()
        # if not sings:
        #     self.tools.click_txt("取消")
        #     self.tools.click_image("home")
        #     return
        self.tools.click_txt("选择好友")
        self.tools.click_txt("拜访")

        while True:
            sings = touch_money()
            if not sings:
                self.tools.click_txt("取消")
                self.tools.click_image("home")
                return
            data = self.tools.exists_image("next", timeout=3, threshold=0.9)
            if data:
                touch(data)
            else:
                break
        self.tools.click_image("home")

    def change(self):
        """
        合成黑匣
        :return:
        """
        self.tools.click_txt("基地")
        data = self.tools.exists_image("mine", timeout=3, threshold=0.9)
        if not data:
            self.tools.click_image("home")
            return
        self.tools.click_image("mine", threshold=0.9)
        self.tools.click_txt("获得物品")
        self.tools.click_txt("合成工厂")
        self.tools.click_image("factory")
        self.tools.click_txt("基地素材")
        self.tools.click_txt("稀有黑匣")
        self.tools.click_image("next_fast", threshold=0.8)
        self.tools.click_txt("确定")
        self.tools.click_txt("获得物品")
        self.tools.click_txt("合成成功")
        self.tools.click_image("home")

    def main(self, taskList):
        for task in taskList:
            try:
                getattr(self, task)()
            except Exception as e:
                logger.error(f"执行任务 {task} 时发生错误: {str(e)}")
                traceback.print_exc()
                # 执行debugOcr进行调试
                debugOcr()
                # 重新抛出异常以便上层处理
                raise


if __name__ == "__main__":
    # taskList = ["start", "exercise", "change", "trade", "task"]
    taskList = ["task"]
    
    # 使用设备管理器连接设备
    device_manager = DeviceManager()
    if not device_manager.connect_device():
        logger.error("设备连接失败，程序退出")
        exit(1)
    
    # 执行游戏任务
    try:
        MCCAA().main(taskList)
    except Exception as e:
        logger.error(f"执行任务时发生错误: {e}")
        debugOcr()
        traceback.print_exc()

    # debugOcr()
    # data = Tools().get_ocr_cropped_result(cropped=[1022, 150, 82, 23])[0]
    # logger.debug(data)
    # tools = Tools().exists_image("factory", timeout=3, threshold=0.9)
    # tempList = list(tools)
    # tempList[1]+=200
    # tools = tuple(tempList)
    # touch(tools)
    # logger.debug(tools)
    # cropped_image(1022,150,82,23)
