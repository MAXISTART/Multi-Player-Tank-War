# bullet.py
"""
子弹类模块：定义游戏中的子弹对象及其行为
"""

import pygame
import math
from common.constants import *
from common.utils import vector_from_angle
from common.deterministic_engine import DeterministicPhysics


class Bullet:
    """
    子弹类：表示游戏中的子弹对象

    主要功能：
    - 初始化子弹（位置、方向等）
    - 子弹移动
    - 碰撞检测
    - 绘制子弹
    """

    def __init__(self, position, direction, owner_id=None):
        """初始化子弹对象"""
        self.x, self.y = position
        self.direction = direction  # 方向角度，0表示向右，90表示向下，以此类推
        self.owner_id = owner_id  # 发射子弹的坦克ID

        # 子弹属性
        self.speed = BULLET_SPEED
        self.damage = BULLET_DAMAGE
        self.radius = BULLET_RADIUS
        self.lifetime = BULLET_LIFETIME * 1000  # 转换为毫秒
        self.color = COLOR_WHITE
        self.active = True  # 子弹是否活跃

        # 计算子弹速度向量
        angle_rad = math.radians(self.direction)
        self.velocity = vector_from_angle(angle_rad, self.speed)

        # 子弹碰撞盒（圆形）
        self.rect = (self.x - self.radius, self.y - self.radius,
                     self.radius * 2, self.radius * 2)

        # 记录创建时间
        self.creation_time = pygame.time.get_ticks()

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

        # 更新位置，使用 delta_time 使移动更平滑
        self.x += self.velocity[0] * delta_time * 60  # 乘以60使速度在60FPS下保持一致
        self.y += self.velocity[1] * delta_time * 60

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
            if getattr(obstacle, 'destroyed', False):
                continue
            if DeterministicPhysics.check_collision(self.rect, obstacle.rect):
                self.active = False
                obstacle.take_damage(self.damage)
                return "obstacle", obstacle

        # 检查与坦克的碰撞(排除自己的坦克)
        for tank in tanks:
            if tank and tank.tank_id != self.owner_id and not getattr(tank, 'is_destroyed', False):  # 不检查与发射者或已销毁坦克的碰撞
                if DeterministicPhysics.check_collision(self.rect, tank.rect):
                    self.active = False
                    tank.take_damage(self.damage)  # 这会触发视觉效果
                    return "tank", tank

        return None, None

    def draw(self, surface):
        """绘制子弹"""
        if not self.active:
            return

        # 绘制子弹（圆形）
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)

    def serialize(self):
        """将子弹状态序列化为字典"""
        return {
            'position': (self.x, self.y),
            'direction': self.direction,
            'owner_id': self.owner_id,
            'velocity': self.velocity,
            'active': self.active,
            'creation_time': self.creation_time
        }

    @classmethod
    def deserialize(cls, data):
        """从序列化数据创建子弹"""
        bullet = cls(data['position'], data['direction'], data['owner_id'])
        bullet.velocity = data['velocity']
        bullet.active = data['active']
        bullet.creation_time = data['creation_time']
        return bullet