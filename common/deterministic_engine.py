# deterministic_engine.py
"""
确定性引擎模块：提供可重现的随机数生成和物理计算

这个模块确保在相同的种子和输入条件下，游戏的随机元素和物理计算
始终产生相同的结果，有助于游戏回放和网络同步。
"""

import random
import math


class DeterministicRandom:
    """
    确定性随机数生成器

    使用固定的种子和算法确保在相同种子下产生相同的随机序列。
    用于地图生成、AI决策等需要可重现随机性的场景。
    """

    def __init__(self, seed=None):
        """初始化随机数生成器，可选指定种子"""
        self._random = random.Random()
        self.seed(seed)

    def seed(self, seed=None):
        """设置随机数生成器的种子"""
        self._random.seed(seed)
        return seed

    def random(self):
        """返回 [0.0, 1.0) 范围内的随机浮点数"""
        return self._random.random()

    def uniform(self, a, b):
        """返回 [a, b) 范围内的随机浮点数"""
        return self._random.uniform(a, b)

    def randint(self, a, b):
        """返回 [a, b] 范围内的随机整数"""
        return self._random.randint(a, b)

    def choice(self, seq):
        """从非空序列中随机选择一个元素"""
        return self._random.choice(seq)

    def choices(self, population, weights=None, k=1):
        """从population中随机选择k个元素，可以指定权重"""
        return self._random.choices(population, weights, k=k)

    def shuffle(self, x):
        """将序列x随机打乱"""
        return self._random.shuffle(x)

    def sample(self, population, k):
        """从population中随机抽取k个不重复的元素"""
        return self._random.sample(population, k)

    def randrange(self, start, stop=None, step=1):
        """返回range(start, stop, step)中的随机元素"""
        return self._random.randrange(start, stop, step)

    def normalvariate(self, mu, sigma):
        """返回均值为mu，标准差为sigma的正态分布随机数"""
        return self._random.normalvariate(mu, sigma)


class DeterministicPhysics:
    """
    确定性物理计算

    提供确定性的物理计算函数，确保相同输入产生相同输出。
    用于碰撞检测、移动计算等需要精确可重现的场景。
    """

    @staticmethod
    def check_collision(rect1, rect2):
        """
        检查两个矩形是否碰撞

        Args:
            rect1: 第一个矩形 (x, y, width, height)
            rect2: 第二个矩形 (x, y, width, height)

        Returns:
            如果两个矩形重叠，返回True
        """
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2

        # 检查两个矩形是否不重叠
        if (x1 >= x2 + w2 or  # rect1在rect2右侧
                x1 + w1 <= x2 or  # rect1在rect2左侧
                y1 >= y2 + h2 or  # rect1在rect2下方
                y1 + h1 <= y2):  # rect1在rect2上方
            return False

        return True

    @staticmethod
    def check_circle_collision(circle1, circle2):
        """
        检查两个圆是否碰撞

        Args:
            circle1: 第一个圆 (x, y, radius)
            circle2: 第二个圆 (x, y, radius)

        Returns:
            如果两个圆重叠，返回True
        """
        x1, y1, r1 = circle1
        x2, y2, r2 = circle2

        # 计算两个圆心之间的距离
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # 如果距离小于两个半径之和，则圆重叠
        return distance < (r1 + r2)

    @staticmethod
    def check_circle_rect_collision(circle, rect):
        """
        检查圆与矩形是否碰撞

        Args:
            circle: 圆 (x, y, radius)
            rect: 矩形 (x, y, width, height)

        Returns:
            如果圆与矩形重叠，返回True
        """
        circle_x, circle_y, radius = circle
        rect_x, rect_y, rect_w, rect_h = rect

        # 找到矩形上离圆心最近的点
        closest_x = max(rect_x, min(circle_x, rect_x + rect_w))
        closest_y = max(rect_y, min(circle_y, rect_y + rect_h))

        # 计算圆心到矩形最近点的距离
        distance = math.sqrt((circle_x - closest_x) ** 2 + (circle_y - closest_y) ** 2)

        # 如果距离小于圆的半径，则相交
        return distance < radius

    @staticmethod
    def calculate_reflection(direction, normal):
        """
        计算反射方向

        Args:
            direction: 入射方向向量 (dx, dy)
            normal: 表面法线向量 (nx, ny)，应该是单位向量

        Returns:
            反射方向向量 (reflect_dx, reflect_dy)
        """
        dx, dy = direction
        nx, ny = normal

        # 确保法线是单位向量
        norm = math.sqrt(nx * nx + ny * ny)
        if norm != 0:
            nx /= norm
            ny /= norm

        # 计算入射方向与法线的点积
        dot_product = dx * nx + dy * ny

        # 计算反射方向 (r = d - 2(d·n)n)
        reflect_dx = dx - 2 * dot_product * nx
        reflect_dy = dy - 2 * dot_product * ny

        return (reflect_dx, reflect_dy)

    @staticmethod
    def get_rect_center(rect):
        """
        获取矩形的中心点

        Args:
            rect: 矩形 (x, y, width, height)

        Returns:
            中心点坐标 (center_x, center_y)
        """
        x, y, width, height = rect
        return (x + width / 2, y + height / 2)

    @staticmethod
    def vector_magnitude(vector):
        """
        计算向量的大小

        Args:
            vector: 向量 (x, y)

        Returns:
            向量的大小
        """
        return math.sqrt(vector[0] ** 2 + vector[1] ** 2)

    @staticmethod
    def vector_normalize(vector):
        """
        将向量归一化为单位向量

        Args:
            vector: 向量 (x, y)

        Returns:
            归一化后的向量 (nx, ny)，如果向量为零向量，则返回 (0, 0)
        """
        magnitude = DeterministicPhysics.vector_magnitude(vector)
        if magnitude == 0:
            return (0, 0)
        return (vector[0] / magnitude, vector[1] / magnitude)

    @staticmethod
    def distance(point1, point2):
        """
        计算两点之间的距离

        Args:
            point1: 第一个点 (x, y)
            point2: 第二个点 (x, y)

        Returns:
            两点之间的欧几里得距离
        """
        return math.sqrt((point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2)

    @staticmethod
    def angle_between_points(point1, point2):
        """
        计算从point1到point2的角度（弧度）

        Args:
            point1: 起点 (x, y)
            point2: 终点 (x, y)

        Returns:
            从point1到point2的角度，以弧度计，0表示向右，π/2表示向下
        """
        return math.atan2(point2[1] - point1[1], point2[0] - point1[0])

    @staticmethod
    def angle_to_vector(angle):
        """
        将角度转换为单位向量

        Args:
            angle: 角度，以弧度计

        Returns:
            对应的单位向量 (x, y)
        """
        return (math.cos(angle), math.sin(angle))

    @staticmethod
    def vector_to_angle(vector):
        """
        将向量转换为角度

        Args:
            vector: 向量 (x, y)

        Returns:
            向量的角度，以弧度计，范围在 [-π, π]
        """
        return math.atan2(vector[1], vector[0])

    @staticmethod
    def rotate_point(point, center, angle):
        """
        围绕中心点旋转一个点

        Args:
            point: 要旋转的点 (x, y)
            center: 旋转中心 (x, y)
            angle: 旋转角度，以弧度计，正值表示逆时针旋转

        Returns:
            旋转后的点 (x', y')
        """
        # 将点相对于中心点平移
        x, y = point[0] - center[0], point[1] - center[1]

        # 应用旋转
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        x_new = x * cos_a - y * sin_a
        y_new = x * sin_a + y * cos_a

        # 平移回原来的坐标系
        return (x_new + center[0], y_new + center[1])