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
if __name__ == "__main__":
    connect_device("Android:///emulator-5560")
    debugOcr()