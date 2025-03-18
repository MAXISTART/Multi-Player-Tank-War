# deterministic_engine.py
"""
确定性引擎模块：确保跨平台一致性计算
"""

import random
import math
from common.utils import collide_rect


class DeterministicRandom:
    """
    确定性随机数生成器：生成可重现的随机序列

    主要功能：
    - 使用固定种子初始化
    - 生成随机数序列
    - 支持常用随机操作
    """

    def __init__(self, seed=None):
        """使用给定种子初始化随机数生成器"""
        self.random = random.Random(seed)
        self.initial_seed = seed

    def next_int(self, min_value=0, max_value=100):
        """生成随机整数"""
        return self.random.randint(min_value, max_value)

    def next_float(self, min_value=0.0, max_value=1.0):
        """生成随机浮点数"""
        return min_value + self.random.random() * (max_value - min_value)

    def next_bool(self, probability=0.5):
        """生成随机布尔值"""
        return self.random.random() < probability

    def choice(self, items):
        """从列表中随机选择一项"""
        return self.random.choice(items)

    def shuffle(self, items):
        """随机打乱列表"""
        # 注意：这会修改原始列表
        self.random.shuffle(items)
        return items

    def get_state(self):
        """获取当前随机数生成器状态"""
        return self.random.getstate()

    def set_state(self, state):
        """设置随机数生成器状态"""
        self.random.setstate(state)

    def reset(self):
        """重置为初始状态"""
        self.random = random.Random(self.initial_seed)


class DeterministicPhysics:
    """
    确定性物理计算：确保物理计算在所有平台上结果一致

    主要功能：
    - 确定性向量运算
    - 确定性碰撞检测
    - 固定步长物理更新
    """

    @staticmethod
    def vector_add(v1, v2):
        """确定性向量加法"""
        return (v1[0] + v2[0], v1[1] + v2[1])

    @staticmethod
    def vector_subtract(v1, v2):
        """确定性向量减法"""
        return (v1[0] - v2[0], v1[1] - v2[1])

    @staticmethod
    def vector_multiply(v, scalar):
        """确定性向量乘以标量"""
        return (v[0] * scalar, v[1] * scalar)

    @staticmethod
    def vector_length(v):
        """确定性计算向量长度"""
        return math.sqrt(v[0] * v[0] + v[1] * v[1])

    @staticmethod
    def vector_normalize(v):
        """确定性向量归一化"""
        length = DeterministicPhysics.vector_length(v)
        if length < 0.00001:  # 避免除以接近0的值
            return (0, 0)
        return (v[0] / length, v[1] / length)

    @staticmethod
    def vector_rotate(v, angle):
        """确定性向量旋转（角度为弧度）"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return (v[0] * cos_a - v[1] * sin_a, v[0] * sin_a + v[1] * cos_a)

    @staticmethod
    def check_collision(rect1, rect2):
        """确定性矩形碰撞检测"""
        return collide_rect(rect1, rect2)

    @staticmethod
    def move_with_collision(moving_rect, velocity, obstacles):
        """确定性移动和碰撞处理"""
        # 分别处理x和y方向的移动，使物体能够沿着墙壁滑动
        # 先尝试水平移动
        new_rect_x = (
            moving_rect[0] + velocity[0],
            moving_rect[1],
            moving_rect[2],
            moving_rect[3]
        )

        x_collision = False
        for obstacle in obstacles:
            if DeterministicPhysics.check_collision(new_rect_x, obstacle):
                x_collision = True
                break

        # 再尝试垂直移动
        new_rect_y = (
            moving_rect[0] if x_collision else new_rect_x[0],
            moving_rect[1] + velocity[1],
            moving_rect[2],
            moving_rect[3]
        )

        y_collision = False
        for obstacle in obstacles:
            if DeterministicPhysics.check_collision(new_rect_y, obstacle):
                y_collision = True
                break

        # 返回最终位置
        return (
            new_rect_x[0] if not x_collision else moving_rect[0],
            new_rect_y[1] if not y_collision else moving_rect[1],
            moving_rect[2],
            moving_rect[3]
        )


class DeterministicTime:
    """
    确定性时间管理：确保时间步长一致

    主要功能：
    - 固定时间步长
    - 时间累积器
    - 时间插值
    """

    def __init__(self, fixed_delta=1 / 60):
        """初始化时间管理器"""
        self.fixed_delta = fixed_delta
        self.accumulator = 0.0
        self.current_time = 0.0
        self.t = 0.0  # 游戏内部时间

    def update(self, real_delta):
        """更新时间累积器"""
        self.current_time += real_delta
        self.accumulator += real_delta

    def should_update(self):
        """检查是否应该执行物理更新"""
        return self.accumulator >= self.fixed_delta

    def consume_update(self):
        """消费一次更新时间"""
        self.accumulator -= self.fixed_delta
        self.t += self.fixed_delta
        return self.fixed_delta

    def get_interpolation_factor(self):
        """获取渲染插值因子"""
        return self.accumulator / self.fixed_delta

    def get_fixed_delta(self):
        """获取固定时间步长"""
        return self.fixed_delta

    def set_fixed_delta(self, fixed_delta):
        """设置固定时间步长"""
        self.fixed_delta = fixed_delta

    def get_time(self):
        """获取当前游戏内部时间"""
        return self.t


# 单元测试
def test_deterministic_engine():
    """确定性引擎模块的单元测试"""
    # 测试确定性随机数
    rand1 = DeterministicRandom(42)
    rand2 = DeterministicRandom(42)

    # 同样的种子应该产生同样的随机数序列
    for _ in range(10):
        assert rand1.next_int(0, 100) == rand2.next_int(0, 100)

    # 测试物理引擎
    v1 = (3, 4)
    v2 = (1, 2)

    # 向量加法
    result = DeterministicPhysics.vector_add(v1, v2)
    assert result == (4, 6)

    # 向量长度
    length = DeterministicPhysics.vector_length(v1)
    assert abs(length - 5) < 0.0001

    # 碰撞检测
    rect1 = (0, 0, 10, 10)
    rect2 = (5, 5, 10, 10)
    rect3 = (20, 20, 10, 10)

    assert DeterministicPhysics.check_collision(rect1, rect2)
    assert not DeterministicPhysics.check_collision(rect1, rect3)

    # 时间管理
    time_manager = DeterministicTime(fixed_delta=0.01)
    time_manager.update(0.02)  # 更新两帧的时间

    assert time_manager.should_update()
    time_manager.consume_update()
    assert time_manager.should_update()
    time_manager.consume_update()
    assert not time_manager.should_update()

    print("All deterministic engine tests passed!")


if __name__ == "__main__":
    test_deterministic_engine()