# -*- encoding=utf8 -*-
__author__ = "x"

import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import Levenshtein
from airtest.core.api import snapshot, touch, sleep, click, wait, Template, G, connect_device, ST, start_app, stop_app
from loguru import logger
from paddleocr import PaddleOCR


def debugOcr():
    pic_path = r"./now.png"
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


class Tools(object):
    def __init__(self):
        """
        初始化工具类，包含OCR实例和线程锁
        
        Attributes:
            sings: 用于同步的信号量
            ocr: PaddleOCR实例，用于文字识别
            lock: 线程锁，用于同步操作
        """
        self.sings = None
        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        self.lock = threading.Lock()

    def ocr_exists(self, target_text, timeout=10):
        """
        判断目标文本是否存在于当前屏幕中，并返回其中心坐标
        
        :param target_text: 要检测的目标文本内容
        :param timeout: 检测超时时间（秒），默认10秒
        :return: 目标文本的中心坐标（元组形式），若超时未找到则返回False
        """
        startTime = time.time()
        logger.debug(f"判断: {target_text}")
        while True:
            pic_path = r"./now.png"
            snapshot(pic_path)
            ocr_result = self.ocr.ocr(pic_path, cls=True)
            for line in ocr_result or list():
                for word_info in line or list():
                    # 获取识别结果的文字信息
                    textinfo = word_info[1][0]
                    if target_text == textinfo:
                        # 获取文字的坐标（中心点）
                        x1, y1 = word_info[0][0]
                        x2, y2 = word_info[0][2]
                        target_coords = ((x1 + x2) / 2, (y1 + y2) / 2)
                        return target_coords
            endTime = time.time()
            if endTime - startTime >= timeout:
                return False

    def ocr_exists_le(self, target_text, timeout=10, ratio=0.7):
        """
        通过Levenshtein相似度模糊匹配目标文本是否存在，并返回其中心坐标
        
        :param target_text: 要检测的目标文本内容
        :param timeout: 检测超时时间（秒），默认10秒
        :param ratio: 相似度阈值（0-1），默认0.7
        :return: 目标文本的中心坐标（元组形式），若超时未找到则返回False
        """
        startTime = time.time()
        logger.debug(f"判断: {target_text}")
        while True:
            pic_path = r"./now.png"
            snapshot(pic_path)
            ocr_result = self.ocr.ocr(pic_path, cls=True)
            for line in ocr_result or list():
                for word_info in line or list():
                    # 获取识别结果的文字信息
                    textinfo = word_info[1][0]
                    if Levenshtein.ratio(target_text, textinfo) >= ratio:
                        # 获取文字的坐标（中心点）
                        x1, y1 = word_info[0][0]
                        x2, y2 = word_info[0][2]
                        target_coords = ((x1 + x2) / 2, (y1 + y2) / 2)
                        return target_coords
            endTime = time.time()
            if endTime - startTime >= timeout:
                return False

    def click_number(self):
        """
        检测到"请选择宝物"文本后，点击屏幕中三位数的文本内容
        """
        logger.debug("点击数字")
        _click = False
        pic_path = r"./now.png"
        snapshot(pic_path)
        ocr_result = self.ocr.ocr(pic_path, cls=True)
        for line in ocr_result:
            for word_info in line:
                textinfo = word_info[1][0]
                number = re.search("\d\d\d", textinfo)
                if number and _click:
                    # 获取文字的坐标（中心点）
                    x1, y1 = word_info[0][0]
                    x2, y2 = word_info[0][2]
                    target_coords = ((x1 + x2) / 2, (y1 + y2) / 2)
                    touch(target_coords)
                    sleep(2)
                elif "请选择宝物" in textinfo:
                    _click = True
                else:
                    continue

    def ocr_touch(self, target_text, click_timeout=0.5):
        """
        精确匹配目标文本并点击其中心坐标
        
        :param target_text: 要点击的目标文本内容
        :param click_timeout: 点击前等待时间（秒），默认0.5秒
        :return: 目标文本的中心坐标（元组形式）
        :raises ValueError: 未找到目标文本时抛出异常
        """
        logger.debug(f"准备点击: {target_text}")
        pic_path = r"./now.png"
        snapshot(pic_path)
        ocr_result = self.ocr.ocr(pic_path, cls=True)
        target_coords = None
        for line in ocr_result or []:
            for word_info in line:
                # 获取识别结果的文字信息
                textinfo = word_info[1][0]
                if target_text == textinfo:
                    # 获取文字的坐标（中心点）
                    x1, y1 = word_info[0][0]
                    x2, y2 = word_info[0][2]
                    target_coords = ((x1 + x2) / 2, (y1 + y2) / 2)
                    break
            if target_coords:
                break

        # 点击坐标
        if target_coords:
            logger.debug(f"点击: {target_text} 坐标: {target_coords}")
            sleep(click_timeout)
            touch(target_coords)
            return target_coords
        else:
            raise ValueError(f"没识别到: {target_text}")

    def ocr_touch_le(self, target_text, click_timeout=0.5, ratio=0.7):
        """
        模糊匹配目标文本并点击其中心坐标
        
        :param target_text: 要点击的目标文本内容
        :param click_timeout: 点击前等待时间（秒），默认0.5秒
        :param ratio: 相似度阈值（0-1），默认0.7
        :return: 目标文本的中心坐标（元组形式）
        :raises ValueError: 未找到目标文本时抛出异常
        """
        logger.debug(f"准备点击: {target_text}")
        pic_path = r"./now.png"
        snapshot(pic_path)
        ocr_result = self.ocr.ocr(pic_path, cls=True)
        target_coords = None
        for line in ocr_result or []:
            for word_info in line:
                # 获取识别结果的文字信息
                textinfo = word_info[1][0]
                if Levenshtein.ratio(target_text, textinfo) >= ratio:
                    # 获取文字的坐标（中心点）
                    x1, y1 = word_info[0][0]
                    x2, y2 = word_info[0][2]
                    target_coords = ((x1 + x2) / 2, (y1 + y2) / 2)
                    break
            if target_coords:
                break

        # 点击坐标
        if target_coords:
            logger.debug(f"点击: {target_text} 坐标: {target_coords}")
            sleep(click_timeout)
            touch(target_coords)
            return target_coords
        else:
            raise ValueError(f"没识别到: {target_text}")

    def get_ocr_result(self):
        """
        获取当前屏幕中所有识别到的文本及其中心坐标
        
        :return: 包含文本和对应中心坐标的列表（格式：[{text: (x,y)}]）
        """
        pic_path = r"./now.png"
        snapshot(pic_path)
        ocr_result = self.ocr.ocr(pic_path, cls=True)
        result = list()
        for line in ocr_result:
            for word_info in line:
                # 获取识别结果的文字信息
                textinfo = word_info[1][0]

                x1, y1 = word_info[0][0]
                x2, y2 = word_info[0][2]
                target_coords = ((x1 + x2) / 2, (y1 + y2) / 2)
                result.append({textinfo: target_coords})
        return result

    def click_txt(self, target_text, timeout=10, click_timeout=0.5):
        """
        等待目标文本出现后点击其中心坐标
        
        :param target_text: 要点击的目标文本内容
        :param timeout: 等待超时时间（秒），默认10秒
        :param click_timeout: 点击前等待时间（秒），默认0.5秒
        """
        target_coords = self.ocr_exists(target_text, timeout)
        if target_coords:
            sleep(click_timeout)
            touch(target_coords)

    def click_txt_le(self, target_text, timeout=10, click_timeout=0.5, ratio=0.7):
        """
        等待模糊匹配的目标文本出现后点击其中心坐标
        
        :param target_text: 要点击的目标文本内容
        :param timeout: 等待超时时间（秒），默认10秒
        :param click_timeout: 点击前等待时间（秒），默认0.5秒
        :param ratio: 相似度阈值（0-1），默认0.7
        """
        target_coords = self.ocr_exists_le(target_text, timeout, ratio)
        if target_coords:
            sleep(click_timeout)
            touch(target_coords)

    def wait_image(self, image):
        """
        等待指定图片出现在屏幕中
        
        :param image: 图片名称（不带扩展名，默认png格式）
        :return: 图片在屏幕中的坐标（元组形式）
        """
        result = wait(Template(f"images/{image}.png"), timeout=30)
        return result

    def exists_image(self, image, timeout=10, threshold=0.7, interval=0.5, intervalfunc=None):
        """
        检测指定图片是否存在并返回其坐标
        
        :param image: 图片名称（不带扩展名，默认png格式）
        :param timeout: 检测超时时间（秒），默认10秒
        :param threshold: 图片匹配阈值（0-1），默认0.7
        :param interval: 检测间隔时间（秒），默认0.5秒
        :param intervalfunc: 检测间隔执行的函数（可选）
        :return: 图片在屏幕中的坐标（元组形式），若超时未找到则返回False
        """
        query = Template(f"images/{image}.png", rgb=True, threshold=threshold)
        start_time = time.time()
        if self.sings:
            return False
        else:
            while True:
                if self.sings:
                    return False
                screen = G.DEVICE.snapshot(filename=None, quality=ST.SNAPSHOT_QUALITY)
                if screen is None:
                    G.LOGGING.warning("Screen is None, may be locked")
                else:
                    if threshold:
                        query.threshold = threshold
                    match_pos = query.match_in(screen)
                    if match_pos:
                        # try_log_screen(screen)
                        self.lock.acquire()
                        if not self.sings:
                            self.sings = match_pos
                        self.lock.release()
                        return match_pos
                if intervalfunc is not None:
                    intervalfunc()
                if (time.time() - start_time) > timeout:
                    # try_log_screen(screen)
                    return False
                else:
                    time.sleep(interval)

    def click_image(self, image, timeout=10, threshold=0.7, interval=0.5, intervalfunc=None):
        """
        等待指定图片出现后点击其坐标
        
        :param image: 图片名称（不带扩展名，默认png格式）
        :param timeout: 等待超时时间（秒），默认10秒
        :param threshold: 图片匹配阈值（0-1），默认0.7
        :param interval: 检测间隔时间（秒），默认0.5秒
        :param intervalfunc: 检测间隔执行的函数（可选）
        :return: 图片在屏幕中的坐标（元组形式），若未找到则返回False
        """
        match_pos = self.exists_image(image, timeout, threshold, interval, intervalfunc)
        if match_pos:
            touch(match_pos)
            return match_pos
        return False

    def clear_sings(self):
        """
        重置同步信号量，用于清除之前的状态记录
        """
        self.sings = None


# 空白点 600，500
class MCCAA(object):
    def __init__(self):
        self.tools = Tools()

    def start(self):
        start_app("com.megagame.crosscore.bilibili")
        self.tools.click_txt("开始游戏", timeout=50)
        self.tools.click_txt("今天不再提示", timeout=50)
        self.tools.click_image("x", threshold=0.6)
        self.tools.click_txt("签到")
        self.tools.click_image("break", threshold=0.6)

    def task(self):
        self.tools.click_txt("任务")
        self.tools.click_txt("日常")
        self.tools.click_txt_le("一键领取")

        self.tools.click_txt("周常")
        self.tools.click_txt_le("一键领取")

    def main(self, taskList):
        for task in taskList:
            getattr(self, task)()


if __name__ == "__main__":
    taskList = ["task"]
    connect_device("Android:///emulator-5560")
    MCCAA().main(taskList)
    # debugOcr()
