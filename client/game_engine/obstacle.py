# obstacle.py
"""
障碍物类模块：定义游戏中的各种障碍物
"""

import pygame
import os
from common.constants import *


class Obstacle:
    """
    障碍物基类：游戏中所有障碍物的基类

    主要功能：
    - 初始化障碍物（位置、尺寸等）
    - 碰撞检测
    - 处理伤害
    - 绘制障碍物
    """

    def __init__(self, x, y, width, height, is_destructible=False, health=100):
        """初始化障碍物对象"""
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.is_destructible = is_destructible
        self.health = health if is_destructible else float('inf')
        self.initial_health = health
        self.destroyed = False

        # 碰撞盒
        self.rect = (x, y, width, height)

        # 图像
        self.image = None

    def take_damage(self, damage):
        """
        受到伤害，返回是否被破坏
        不可破坏的障碍物会忽略伤害
        """
        if not self.is_destructible:
            return False

        self.health -= damage
        if self.health <= 0 and not self.destroyed:
            self.destroyed = True
            return True
        return False

    def draw(self, surface):
        """在屏幕上绘制障碍物"""
        if self.destroyed:
            return

        if self.image:
            surface.blit(self.image, self.rect)
        else:
            # 如果没有图像，绘制一个简单的矩形
            color = COLOR_GRAY
            if self.is_destructible:
                # 根据生命值改变颜色
                health_ratio = self.health / self.initial_health
                green = int(255 * health_ratio)
                color = (255 - green, green, 0)

            pygame.draw.rect(surface, color, self.rect)

    def serialize(self):
        """将障碍物状态序列化为字典"""
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'is_destructible': self.is_destructible,
            'health': self.health,
            'destroyed': self.destroyed,
            'type': self.__class__.__name__
        }

    @classmethod
    def deserialize(cls, data):
        """从序列化数据创建障碍物"""
        if data['type'] == 'WallObstacle':
            return WallObstacle(
                data['x'], data['y'], data['width'], data['height']
            )
        elif data['type'] == 'BrickObstacle':
            obstacle = BrickObstacle(
                data['x'], data['y'], data['width'], data['height']
            )
            obstacle.health = data['health']
            obstacle.destroyed = data['destroyed']
            return obstacle
        else:
            obstacle = cls(
                data['x'], data['y'], data['width'], data['height'],
                data['is_destructible']
            )
            obstacle.health = data['health']
            obstacle.destroyed = data['destroyed']
            return obstacle

    def calculate_checksum(self):
        """计算障碍物状态的校验和"""
        state = (
            self.x, self.y, self.width, self.height,
            self.is_destructible, self.health, self.destroyed
        )
        return hash(state)


class WallObstacle(Obstacle):
    """
    墙壁类：不可破坏的障碍物
    """

    def __init__(self, x, y, width=OBSTACLE_SIZE, height=OBSTACLE_SIZE):
        """初始化墙壁对象"""
        super().__init__(x, y, width, height, is_destructible=False)
        self.load_image()

    def load_image(self):
        """加载墙壁图像"""
        try:
            # 尝试加载图像
            image_path = os.path.join(IMAGES_DIR, "wall.png")
            if os.path.exists(image_path):
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, (self.width, self.height))
        except pygame.error:
            # 如果加载失败，将使用基类的绘制方法
            self.image = None


class BrickObstacle(Obstacle):
    """
    砖块类：可破坏的障碍物
    """

    def __init__(self, x, y, width=OBSTACLE_SIZE, height=OBSTACLE_SIZE, health=BRICK_HEALTH):
        """初始化砖块对象"""
        super().__init__(x, y, width, height, is_destructible=True, health=health)
        self.load_image()

    def load_image(self):
        """加载砖块图像"""
        try:
            # 尝试加载图像
            image_path = os.path.join(IMAGES_DIR, "brick.png")
            if os.path.exists(image_path):
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, (self.width, self.height))
        except pygame.error:
            # 如果加载失败，将使用基类的绘制方法
            self.image = None


# 单元测试
def test_obstacles():
    """障碍物类的单元测试"""
    # 初始化pygame
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # 创建墙壁
    wall = WallObstacle(100, 100)
    assert not wall.is_destructible

    # 创建砖块
    brick = BrickObstacle(200, 100)
    assert brick.is_destructible

    # 测试伤害
    assert not wall.take_damage(50)  # 墙壁不应该被破坏
    assert wall.health == float('inf')

    initial_brick_health = brick.health
    brick.take_damage(10)
    assert brick.health == initial_brick_health - 10

    # 破坏砖块
    brick.take_damage(brick.health)
    assert brick.destroyed

    # 测试序列化和反序列化
    wall_data = wall.serialize()
    new_wall = Obstacle.deserialize(wall_data)
    assert new_wall.__class__.__name__ == 'WallObstacle'
    assert not new_wall.is_destructible

    brick_data = brick.serialize()
    new_brick = Obstacle.deserialize(brick_data)
    assert new_brick.__class__.__name__ == 'BrickObstacle'
    assert new_brick.destroyed

    # 测试绘制
    wall.draw(screen)
    brick.draw(screen)  # 已经被破坏，不应该绘制
    pygame.display.flip()

    print("All obstacle tests passed!")
    pygame.quit()


if __name__ == "__main__":
    test_obstacles()