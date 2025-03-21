# obstacle.py
"""
障碍物类模块：定义游戏中各种障碍物对象
"""

import pygame
import math
import os
from common.constants import *
from common.utils import current_time_ms
from client.game_engine.particle_system import particle_system


class Obstacle:
    """障碍物基类"""

    def __init__(self, x, y, width, height, health=None):
        """初始化障碍物"""
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.health = health if health is not None else float('inf')
        self.max_health = self.health
        self.rect = (x, y, width, height)
        self.image = None
        self.destroyed = False

        # 受伤状态
        self.hit_time = 0
        self.hit_flash_duration = 500  # 受伤闪烁持续0.5秒
        self.is_hit = False
        self.alpha = 255  # 完全不透明
        self.flash_interval = 100  # 闪烁间隔(毫秒)
        self.last_flash_time = 0
        self.flash_state = False

        # 爆炸效果
        self.is_exploding = False
        self.explosion_start_time = 0
        self.explosion_duration = 800  # 爆炸动画持续0.8秒
        self.explosion_particle_group_id = None  # 存储粒子组ID

    def take_damage(self, damage):
        """受到伤害，返回是否销毁"""
        if self.destroyed or self.is_exploding:
            return True

        if self.health != float('inf'):
            self.health -= damage

            # 设置受伤状态
            self.is_hit = True
            self.hit_time = current_time_ms()

            if self.health <= 0:
                self.health = 0
                self.start_explosion()
                return True

        return False

    def start_explosion(self):
        """开始爆炸效果"""
        self.is_exploding = True
        self.explosion_start_time = current_time_ms()

        # 根据障碍物类型选择颜色
        debris_colors = []
        if isinstance(self, BrickObstacle):
            debris_colors = [COLOR_BROWN, (139, 69, 19), (160, 82, 45)]  # 棕色系
        else:
            debris_colors = [COLOR_GRAY, (100, 100, 100), (70, 70, 70)]  # 灰色系

        # 创建碎片粒子效果
        self.explosion_particle_group_id = particle_system.create_debris(
            x=self.x + self.width / 2,
            y=self.y + self.height / 2,
            color_palette=debris_colors,
            count=20,
            min_speed=0.5,
            max_speed=3,
            min_size=1,
            max_size=4,
            duration=self.explosion_duration,
            gravity=0.1
        )

    def update(self, delta_time):
        """更新障碍物状态"""
        current_time = current_time_ms()

        # 处理爆炸效果
        if self.is_exploding:
            elapsed = current_time - self.explosion_start_time
            if elapsed > self.explosion_duration:
                self.is_exploding = False
                self.destroyed = True
                self.explosion_particle_group_id = None
            # 粒子由粒子系统更新，不需要在这里更新

        # 处理受伤闪烁效果
        if self.is_hit and not self.destroyed and not self.is_exploding:
            elapsed = current_time - self.hit_time

            # 受伤闪烁效果结束
            if elapsed > self.hit_flash_duration:
                self.is_hit = False
                self.alpha = 255  # 恢复完全不透明
            else:
                # 控制闪烁频率
                if current_time - self.last_flash_time > self.flash_interval:
                    self.last_flash_time = current_time
                    self.flash_state = not self.flash_state

                # 设置透明度
                self.alpha = 150 if self.flash_state else 255

        # 低生命值持续闪烁
        if self.health != float(
                'inf') and self.health <= self.max_health * 0.3 and not self.is_hit and not self.is_exploding and not self.destroyed:
            if current_time - self.last_flash_time > self.flash_interval * 1.5:  # 低生命闪烁更慢
                self.last_flash_time = current_time
                self.flash_state = not self.flash_state

            # 设置较轻的闪烁效果
            self.alpha = 200 if self.flash_state else 255

    def draw(self, surface):
        """绘制障碍物"""
        if self.destroyed:
            return  # 已销毁，不绘制

        if self.is_exploding:
            # 爆炸粒子由粒子系统绘制，这里仅绘制淡出的障碍物
            elapsed_ratio = (current_time_ms() - self.explosion_start_time) / self.explosion_duration
            fade_alpha = int(255 * (1 - elapsed_ratio))
            if fade_alpha > 0 and self.image:
                image_copy = self.image.copy()
                image_copy.set_alpha(fade_alpha)
                surface.blit(image_copy, self.rect)
        else:
            # 绘制带透明度的障碍物
            if self.image:
                # 创建带透明度的图像副本
                image_copy = self.image.copy()
                image_copy.set_alpha(self.alpha)
                # 绘制
                surface.blit(image_copy, self.rect)
            else:
                # 如果没有图像，绘制一个简单的矩形
                rect_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                rect_surface.fill((*pygame.Color(self.get_color())[:3], self.alpha))
                surface.blit(rect_surface, self.rect)

    def get_color(self):
        """获取障碍物颜色（子类覆盖）"""
        return COLOR_GRAY

    def get_position(self):
        """获取障碍物位置"""
        return (self.x, self.y)

    def get_size(self):
        """获取障碍物尺寸"""
        return (self.width, self.height)

    def get_center(self):
        """获取障碍物中心点"""
        return (self.x + self.width / 2, self.y + self.height / 2)

    def serialize(self):
        """将障碍物状态序列化为字典"""
        return {
            'type': self.__class__.__name__,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'health': self.health,
            'destroyed': self.destroyed
        }


class WallObstacle(Obstacle):
    """不可破坏的墙"""

    def __init__(self, x, y, width=OBSTACLE_SIZE, height=OBSTACLE_SIZE):
        super().__init__(x, y, width, height, health=WALL_HEALTH)
        self.load_image()

    def load_image(self):
        """加载墙的图像"""
        try:
            image_path = os.path.join(IMAGES_DIR, "wall.png")
            if os.path.exists(image_path):
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, (self.width, self.height))
            else:
                # 如果图像文件不存在，创建一个简单的表面
                self.image = pygame.Surface((self.width, self.height))
                self.image.fill(COLOR_GRAY)
        except pygame.error as e:
            print(f"Error loading wall image: {e}")
            # 如果加载失败，创建一个默认图像
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill(COLOR_GRAY)

    def get_color(self):
        return COLOR_GRAY


class BrickObstacle(Obstacle):
    """可破坏的砖墙"""

    def __init__(self, x, y, width=OBSTACLE_SIZE, height=OBSTACLE_SIZE):
        super().__init__(x, y, width, height, health=BRICK_HEALTH)
        self.load_image()

    def load_image(self):
        """加载砖墙的图像"""
        try:
            image_path = os.path.join(IMAGES_DIR, "brick.png")
            if os.path.exists(image_path):
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, (self.width, self.height))
            else:
                # 如果图像文件不存在，创建一个简单的表面
                self.image = pygame.Surface((self.width, self.height))
                self.image.fill(COLOR_BROWN)
        except pygame.error as e:
            print(f"Error loading brick image: {e}")
            # 如果加载失败，创建一个默认图像
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill(COLOR_BROWN)

    def get_color(self):
        return COLOR_BROWN