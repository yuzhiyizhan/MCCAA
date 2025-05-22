# -*- encoding=utf8 -*-
__author__ = "x"

import re
import threading
import time

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

        sings = touch_money()
        if not sings:
            self.tools.click_txt("取消")
            self.tools.click_image("home")
            return
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
    # taskList = ["start", "task","exercise","trade"]
    taskList = ["change"]
    connect_device("Android:///emulator-5560")
    MCCAA().main(taskList)



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
