# utils.py
"""
工具函数模块：通用工具函数
"""

import math
import time
import uuid
import logging
import os


def ensure_dir(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def generate_unique_id():
    """生成唯一标识符"""
    return str(uuid.uuid4())


def distance(pos1, pos2):
    """计算两点间的距离"""
    return math.sqrt((pos2[0] - pos1[0]) ** 2 + (pos2[1] - pos1[1]) ** 2)


def angle_between(pos1, pos2):
    """计算两点间的角度（弧度）"""
    return math.atan2(pos2[1] - pos1[1], pos2[0] - pos1[0])


def angle_to_direction(angle):
    """将角度（弧度）转换为方向向量"""
    return (math.cos(angle), math.sin(angle))


def direction_to_angle(direction):
    """将方向向量转换为角度（弧度）"""
    return math.atan2(direction[1], direction[0])


def vector_from_angle(angle, length=1.0):
    """从角度创建向量"""
    return (math.cos(angle) * length, math.sin(angle) * length)


def vector_length(vector):
    """计算向量长度"""
    return math.sqrt(vector[0] ** 2 + vector[1] ** 2)


def normalize_vector(vector):
    """标准化向量"""
    length = vector_length(vector)
    if length == 0:
        return (0, 0)
    return (vector[0] / length, vector[1] / length)


def clamp(value, min_value, max_value):
    """将值限制在指定范围内"""
    return max(min_value, min(max_value, value))


def is_point_in_rect(point, rect):
    """
    检查点是否在矩形内
    rect 格式为 (x, y, width, height)
    """
    return (rect[0] <= point[0] <= rect[0] + rect[2] and
            rect[1] <= point[1] <= rect[1] + rect[3])


def rect_from_center(center, width, height):
    """从中心点创建矩形"""
    return (center[0] - width / 2, center[1] - height / 2, width, height)


def current_time_ms():
    """获取当前时间的毫秒表示"""
    return int(time.time() * 1000)


def setup_logger(name, log_file, level=logging.INFO):
    """设置日志记录器"""
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def log_message(message, level='INFO', logger=None):
    """记录日志消息"""
    if logger:
        if level == 'DEBUG':
            logger.debug(message)
        elif level == 'INFO':
            logger.info(message)
        elif level == 'WARNING':
            logger.warning(message)
        elif level == 'ERROR':
            logger.error(message)
        elif level == 'CRITICAL':
            logger.critical(message)
    else:
        print(f"[{level}] {message}")


def degrees_to_radians(degrees):
    """将角度转换为弧度"""
    return degrees * math.pi / 180


def radians_to_degrees(radians):
    """将弧度转换为角度"""
    return radians * 180 / math.pi


def collide_rect(rect1, rect2):
    """
    检测两个矩形是否碰撞
    rect 格式为 (x, y, width, height)
    """
    return (rect1[0] < rect2[0] + rect2[2] and
            rect1[0] + rect1[2] > rect2[0] and
            rect1[1] < rect2[1] + rect2[3] and
            rect1[1] + rect1[3] > rect2[1])


def calculate_checksum(data):
    """计算数据的简单校验和"""
    if isinstance(data, dict):
        # 对字典进行排序以确保一致性
        return hash(tuple(sorted((k, calculate_checksum(v)) for k, v in data.items())))
    elif isinstance(data, list) or isinstance(data, tuple):
        return hash(tuple(calculate_checksum(item) for item in data))
    else:
        return hash(data)


# 单元测试
def test_utils():
    """工具函数模块的单元测试"""
    # 测试距离计算
    assert distance((0, 0), (3, 4)) == 5

    # 测试向量操作
    angle = math.pi / 4  # 45度
    vec = vector_from_angle(angle, 1.0)
    assert abs(vec[0] - 0.7071) < 0.0001
    assert abs(vec[1] - 0.7071) < 0.0001

    # 测试clamp函数
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10

    # 测试矩形函数
    rect = rect_from_center((50, 50), 20, 20)
    assert rect == (40, 40, 20, 20)
    assert is_point_in_rect((45, 45), rect)
    assert not is_point_in_rect((30, 30), rect)

    print("All utils tests passed!")


if __name__ == "__main__":
    test_utils()