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
        sings 信号
        """
        self.sings = None
        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        self.lock = threading.Lock()

    def ocr_exists(self, target_text, timeout=10):
        """
        判断文字是否存在
        :param target_text:
        :param timeout:
        :return:
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
        模糊匹配文字是否存在，针对ocr结果漏字，错字的情况
        :param target_text:
        :param timeout:
        :return:
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
        检测并点击屏幕中的三位数文本（需先检测到"请选择宝物"提示）

        Note:
            1. 首先检测是否存在"请选择宝物"文本，存在时标记点击状态
            2. 标记后检测三位数文本（正则匹配\d\d\d），找到后点击其中心坐标
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

        Args:
            target_text (str): 需要点击的目标文本内容
            click_timeout (float): 点击前等待时间（单位：秒），默认0.5秒

        Returns:
            tuple: 点击的文本中心坐标元组(x, y)

        Raises:
            ValueError: 超时未找到目标文本时抛出
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
        模糊匹配目标文本并点击其中心坐标（基于Levenshtein距离）

        Args:
            target_text (str): 需要点击的目标文本内容
            click_timeout (float): 点击前等待时间（单位：秒），默认0.5秒
            ratio (float): 相似度阈值（0-1），达到阈值即认为匹配，默认0.7

        Returns:
            tuple: 点击的文本中心坐标元组(x, y)

        Raises:
            ValueError: 超时未找到目标文本时抛出

        Note:
            与ocr_touch的区别：使用模糊匹配算法检测目标文本
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
        获取当前的文字结果
        :return:
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
        精确匹配目标文本并点击（调用ocr_exists获取坐标）

        Args:
            target_text (str): 需要点击的目标文本内容
            timeout (int): 检测超时时间（单位：秒），默认10秒
            click_timeout (float): 点击前等待时间（单位：秒），默认0.5秒
        """
        target_coords = self.ocr_exists(target_text, timeout)
        if target_coords:
            sleep(click_timeout)
            touch(target_coords)

    def click_txt_le(self, target_text, timeout=10, click_timeout=0.5, ratio=0.7):
        """
        模糊匹配目标文本并点击（调用ocr_exists_le获取坐标）

        Args:
            target_text (str): 需要点击的目标文本内容
            timeout (int): 检测超时时间（单位：秒），默认10秒
            click_timeout (float): 点击前等待时间（单位：秒），默认0.5秒
            ratio (float): 相似度阈值（0-1），默认0.7
        """
        target_coords = self.ocr_exists_le(target_text, timeout, ratio)
        if target_coords:
            sleep(click_timeout)
            touch(target_coords)

    def wait_image(self, image):
        """
        等待目标图片出现（阻塞直到找到或超时）

        Args:
            image (str): 图片名称（无需扩展名，默认查找images目录下的png文件）

        Returns:
            tuple: 找到的图片中心坐标元组(x, y)
        """
        result = wait(Template(f"images/{image}.png"), timeout=30)
        return result

    def exists_image(self, image, timeout=10, threshold=0.7, interval=0.5, intervalfunc=None):
        """
        返回图片坐标
        :param image:
        :param timeout:
        :param threshold:
        :param interval:
        :param intervalfunc:
        :return:
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
        检测并点击目标图片（调用exists_image获取坐标）

        Args:
            image (str): 图片名称（无需扩展名，默认查找images目录下的png文件）
            timeout (int): 检测超时时间（单位：秒），默认10秒
            threshold (float): 图像匹配阈值（0-1），默认0.7
            interval (float): 检测间隔时间（单位：秒），默认0.5秒
            intervalfunc (callable|None): 检测间隔期间执行的回调函数

        Returns:
            tuple|False: 找到图片时返回点击的中心坐标元组(x, y)，否则返回False
        """
        match_pos = self.exists_image(image, timeout, threshold, interval, intervalfunc)
        if match_pos:
            touch(match_pos)
            return match_pos
        return False

    def clear_sings(self):
        """
        重置图像匹配位置信号（sings），允许下次重新检测
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
