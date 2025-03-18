# bullet.py
"""
子弹类模块：定义游戏中子弹对象的属性和行为
"""

import pygame
import math
import os
from common.constants import *
from common.utils import vector_from_angle, distance, rect_from_center
from common.deterministic_engine import DeterministicPhysics


class Bullet:
    """
    子弹类：表示坦克发射的子弹

    主要功能：
    - 初始化子弹（位置、方向、伤害等）
    - 子弹移动
    - 碰撞检测
    - 绘制子弹
    """

    def __init__(self, position, direction, owner_id, damage=BULLET_DAMAGE, speed=BULLET_SPEED):
        """初始化子弹对象"""
        self.x, self.y = position
        self.direction = direction  # 角度，0表示向右，90表示向下
        self.owner_id = owner_id
        self.damage = damage
        self.speed = speed
        self.radius = BULLET_RADIUS
        self.active = True
        self.creation_time = pygame.time.get_ticks()
        self.lifetime = BULLET_LIFETIME * 1000  # 转换为毫秒

        # 加载子弹图像
        self.image = None
        self.load_image()

        # 计算移动向量
        angle_rad = math.radians(self.direction)
        self.velocity = vector_from_angle(angle_rad, self.speed)

        # 碰撞盒
        self.rect = (self.x - self.radius, self.y - self.radius,
                     self.radius * 2, self.radius * 2)

    def load_image(self):
        """加载子弹图像"""
        try:
            # 尝试加载图像
            image_path = os.path.join(IMAGES_DIR, "bullet.png")
            if os.path.exists(image_path):
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image,
                                                    (self.radius * 2, self.radius * 2))
        except pygame.error:
            # 如果加载失败，创建一个默认图像
            self.image = None

    def update(self, delta_time, obstacles, tanks):
        """
        更新子弹位置，检测碰撞
        返回碰撞结果（是否命中，命中的对象）
        """
        if not self.active:
            return None, None

        # 检查子弹是否超过生命周期
        current_time = pygame.time.get_ticks()
        if current_time - self.creation_time > self.lifetime:
            self.active = False
            return None, None

        # 更新位置
        self.x += self.velocity[0]
        self.y += self.velocity[1]

        # 更新碰撞盒
        self.rect = (self.x - self.radius, self.y - self.radius,
                     self.radius * 2, self.radius * 2)

        # 检查是否超出屏幕
        if (self.x < 0 or self.x > SCREEN_WIDTH or
                self.y < 0 or self.y > SCREEN_HEIGHT):
            self.active = False
            return None, None

        # 检查与障碍物的碰撞
        for obstacle in obstacles:
            if DeterministicPhysics.check_collision(self.rect, obstacle.rect):
                self.active = False
                obstacle.take_damage(self.damage)
                return "obstacle", obstacle

        # 检查与坦克的碰撞(排除自己的坦克)
        for tank in tanks:
            if tank.tank_id != self.owner_id:  # 不检查与发射者的碰撞
                if DeterministicPhysics.check_collision(self.rect, tank.rect):
                    self.active = False
                    tank.take_damage(self.damage)
                    return "tank", tank

        return None, None

    def draw(self, surface):
        """在屏幕上绘制子弹"""
        if not self.active:
            return

        if self.image:
            # 如果有图像，使用图像
            surface.blit(self.image, self.rect)
        else:
            # 如果没有图像，绘制一个简单的圆形
            pygame.draw.circle(surface, COLOR_BLACK,
                               (int(self.x), int(self.y)), self.radius)

    def serialize(self):
        """将子弹状态序列化为字典"""
        return {
            'x': self.x,
            'y': self.y,
            'direction': self.direction,
            'owner_id': self.owner_id,
            'damage': self.damage,
            'speed': self.speed,
            'active': self.active,
            'creation_time': self.creation_time
        }

    @classmethod
    def deserialize(cls, data):
        """从序列化数据创建子弹"""
        bullet = cls(
            position=(data['x'], data['y']),
            direction=data['direction'],
            owner_id=data['owner_id'],
            damage=data['damage'],
            speed=data['speed']
        )
        bullet.active = data['active']
        bullet.creation_time = data['creation_time']
        return bullet

    def calculate_checksum(self):
        """计算子弹状态的校验和"""
        state = (
            self.x, self.y, self.direction, self.owner_id,
            self.active, self.damage
        )
        return hash(state)


# 单元测试
def test_bullet():
    """子弹类的单元测试"""
    # 初始化pygame
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # 创建子弹
    bullet = Bullet((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), 0, "tank1")

    # 测试移动
    old_x = bullet.x
    bullet.update(1 / 60, [], [])
    assert bullet.x > old_x  # 子弹应该向右移动

    # 测试序列化和反序列化
    serialized_data = bullet.serialize()
    new_bullet = Bullet.deserialize(serialized_data)
    assert new_bullet.x == bullet.x
    assert new_bullet.y == bullet.y
    assert new_bullet.direction == bullet.direction
    assert new_bullet.owner_id == bullet.owner_id

    # 测试绘制
    bullet.draw(screen)
    pygame.display.flip()

    print("All bullet tests passed!")
    pygame.quit()


if __name__ == "__main__":
    test_bullet()