# tank.py
"""
坦克类模块：定义游戏中坦克对象的属性和行为
"""

import pygame
import math
import os
from common.constants import *
from common.utils import vector_from_angle, current_time_ms, rect_from_center
from common.deterministic_engine import DeterministicPhysics


class Tank:
    """
    坦克类：表示游戏中的坦克对象

    主要功能：
    - 初始化坦克（位置、朝向、颜色等）
    - 坦克移动控制
    - 坦克射击
    - 处理伤害和碰撞
    - 绘制坦克
    """

    def __init__(self, x, y, color, tank_id=None, is_player=False):
        """初始化坦克对象"""
        self.x = x
        self.y = y
        self.color = color
        self.tank_id = tank_id or f"tank_{id(self)}"
        self.is_player = is_player

        # 坦克属性
        self.width = TANK_WIDTH
        self.height = TANK_HEIGHT
        self.speed = TANK_SPEED
        self.rotation_speed = TANK_ROTATION_SPEED
        self.health = TANK_HEALTH
        self.ammo = TANK_AMMO
        self.last_shot_time = 0
        self.reload_time = TANK_RELOAD_TIME

        # 方向和运动
        self.direction = 0  # 角度，0表示向右，90表示向下
        self.moving = False
        self.rotating = 0  # -1 左转, 0 不转, 1 右转

        # 加载坦克图像
        self.original_image = None
        self.image = None
        self.load_image()

        # 碰撞盒
        self.rect = (x - self.width / 2, y - self.height / 2, self.width, self.height)

    def load_image(self):
        """加载坦克图像"""
        try:
            # 尝试加载图像，如果图像文件不存在，则创建一个简单的表面
            image_path = os.path.join(IMAGES_DIR, f"tank_{self.color}.png")
            if os.path.exists(image_path):
                self.original_image = pygame.image.load(image_path).convert_alpha()
                self.original_image = pygame.transform.scale(self.original_image, (self.width, self.height))
            else:
                # 创建简单的矩形表面
                self.original_image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

                # 绘制坦克主体
                if self.color == 'red':
                    tank_color = COLOR_RED
                elif self.color == 'blue':
                    tank_color = COLOR_BLUE
                elif self.color == 'green':
                    tank_color = COLOR_GREEN
                else:
                    tank_color = COLOR_YELLOW

                pygame.draw.rect(self.original_image, tank_color, (0, 0, self.width, self.height))

                # 绘制坦克炮塔
                pygame.draw.circle(self.original_image, COLOR_DARK_GREEN,
                                   (self.width // 2, self.height // 2), self.width // 3)

                # 绘制坦克炮管
                pygame.draw.rect(self.original_image, COLOR_DARK_GREEN,
                                 (self.width // 2 - 2, 0, 4, self.height // 2))

            # 初始旋转
            self.update_image()
        except pygame.error as e:
            print(f"Error loading tank image: {e}")
            # 如果加载失败，创建一个默认图像
            self.original_image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.rect(self.original_image, self.color, (0, 0, self.width, self.height))
            self.update_image()

    def update_image(self):
        """更新坦克图像的旋转"""
        self.image = pygame.transform.rotate(self.original_image, -self.direction)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def move(self, direction=None, obstacles=None):
        """移动坦克，处理碰撞"""
        if not self.moving:
            return False

        # 计算移动向量
        angle_rad = math.radians(self.direction)
        dx, dy = vector_from_angle(angle_rad, self.speed)

        # 更新位置前保存旧位置
        old_x, old_y = self.x, self.y

        # 先尝试更新位置
        new_x = self.x + dx
        new_y = self.y + dy

        # 边界检查
        new_x = max(self.width / 2, min(SCREEN_WIDTH - self.width / 2, new_x))
        new_y = max(self.height / 2, min(SCREEN_HEIGHT - self.height / 2, new_y))

        # 碰撞检测
        if obstacles:
            # 计算新的矩形
            new_rect = rect_from_center((new_x, new_y), self.width, self.height)

            # 检查与所有障碍物的碰撞
            for obstacle in obstacles:
                if DeterministicPhysics.check_collision(new_rect, obstacle.rect):
                    # 发生碰撞，不更新位置
                    return False

        # 如果没有碰撞，更新位置
        self.x, self.y = new_x, new_y
        self.rect = rect_from_center((self.x, self.y), self.width, self.height)
        return True

    def can_shoot(self, current_time):
        """检查是否可以射击"""
        return (self.ammo > 0 and
                (current_time - self.last_shot_time) >= self.reload_time)

    def shoot(self, current_time):
        """射击，返回子弹的初始位置和方向"""
        if not self.can_shoot(current_time):
            return None

        # 减少弹药
        self.ammo -= 1
        self.last_shot_time = current_time

        # 计算子弹的初始位置（坦克炮管前端）
        angle_rad = math.radians(self.direction)
        bullet_offset = vector_from_angle(angle_rad, self.width / 2)
        bullet_x = self.x + bullet_offset[0]
        bullet_y = self.y + bullet_offset[1]

        return (bullet_x, bullet_y, self.direction)

    def take_damage(self, damage):
        """受到伤害，返回是否死亡"""
        self.health -= damage
        return self.health <= 0

    def draw(self, surface):
        """在屏幕上绘制坦克"""
        if self.image:
            surface.blit(self.image, self.rect)
        else:
            # 如果没有图像，绘制一个简单的矩形
            pygame.draw.rect(surface, self.color, self.rect)

    def serialize(self):
        """将坦克状态序列化为字典"""
        return {
            'tank_id': self.tank_id,
            'x': self.x,
            'y': self.y,
            'direction': self.direction,
            'health': self.health,
            'ammo': self.ammo,
            'color': self.color,
            'is_player': self.is_player,
            'last_shot_time': self.last_shot_time
        }

    @classmethod
    def deserialize(cls, data, color):
        """从序列化数据创建坦克"""
        tank = cls(
            x=data['x'],
            y=data['y'],
            color=data['color'] if 'color' in data else color,
            tank_id=data['tank_id'],
            is_player=data['is_player']
        )
        tank.direction = data['direction']
        tank.health = data['health']
        tank.ammo = data['ammo']
        tank.last_shot_time = data['last_shot_time']
        tank.update_image()  # 更新图像以反映新方向
        return tank

    def apply_input(self, input_data):
        """应用输入数据更新坦克状态"""
        if not input_data:
            return

        # 处理移动输入
        if 'movement' in input_data:
            movement = input_data['movement']

            if movement == 'up':
                self.direction = 0
                self.moving = True
            elif movement == 'right':
                self.direction = 90
                self.moving = True
            elif movement == 'down':
                self.direction = 180
                self.moving = True
            elif movement == 'left':
                self.direction = 270
                self.moving = True
            elif movement == 'stop':
                self.moving = False

        # 处理旋转输入
        if 'rotation' in input_data:
            rotation = input_data['rotation']

            if rotation == 'left':
                self.direction = (self.direction - self.rotation_speed) % 360
            elif rotation == 'right':
                self.direction = (self.direction + self.rotation_speed) % 360

        # 更新图像以反映新方向
        self.update_image()

    def calculate_checksum(self):
        """计算坦克状态的校验和"""
        state = (
            self.x, self.y, self.direction, self.health,
            self.ammo, self.tank_id, self.moving
        )
        return hash(state)


# 单元测试
def test_tank():
    """坦克类的单元测试"""
    # 初始化pygame
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # 创建坦克
    tank = Tank(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 'red', is_player=True)

    # 测试移动
    tank.moving = True
    tank.direction = 0  # 向右
    old_x = tank.x
    tank.move()
    assert tank.x > old_x  # 坦克应该向右移动

    # 测试射击
    current_time = current_time_ms()
    assert tank.can_shoot(current_time)  # 初始应该可以射击
    bullet_info = tank.shoot(current_time)
    assert bullet_info is not None  # 应该返回子弹信息
    assert not tank.can_shoot(current_time)  # 射击后应该进入冷却

    # 测试受伤
    initial_health = tank.health
    tank.take_damage(10)
    assert tank.health == initial_health - 10

    # 测试序列化和反序列化
    serialized_data = tank.serialize()
    new_tank = Tank.deserialize(serialized_data, 'red')
    assert new_tank.x == tank.x
    assert new_tank.y == tank.y
    assert new_tank.direction == tank.direction
    assert new_tank.health == tank.health

    # 测试绘制
    tank.draw(screen)
    pygame.display.flip()

    print("All tank tests passed!")
    pygame.quit()


if __name__ == "__main__":
    test_tank()