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
from client.game_engine.particle_system import particle_system


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

    # 定义方向常量，与按键对应
    RIGHT = 0
    DOWN = 90
    LEFT = 180
    UP = 270

    def __init__(self, x, y, color, tank_id=None, is_player=False):
        """初始化坦克对象"""
        self.x = x
        self.y = y
        self.prev_x = x  # 存储前一帧位置
        self.prev_y = y  # 存储前一帧位置
        self.color = color
        self.tank_id = tank_id or f"tank_{id(self)}"
        self.is_player = is_player

        # 坦克属性
        self.width = TANK_WIDTH
        self.height = TANK_HEIGHT
        self.speed = TANK_SPEED
        self.rotation_speed = TANK_ROTATION_SPEED
        self.health = TANK_HEALTH
        self.max_health = TANK_HEALTH  # 添加最大生命值记录
        self.ammo = TANK_AMMO
        self.last_shot_time = 0
        self.reload_time = TANK_RELOAD_TIME

        # 方向和运动
        self.direction = self.RIGHT  # 初始朝右
        self.moving = False
        self.rotating = 0  # -1 左转, 0 不转, 1 右转

        # 加载坦克图像
        self.original_image = None
        self.image = None
        self.load_image()

        # 碰撞盒
        self.collision_margin = 0  # 移除任何额外边距
        self.rect = (
            x - self.width / 2,
            y - self.height / 2,
            self.width,
            self.height
        )
        self.collision_box = (
            x - self.width / 2,
            y - self.height / 2,
            self.width,
            self.height
        )

        # 受伤状态
        self.hit_time = 0
        self.hit_flash_duration = 1000  # 受伤闪烁持续1秒
        self.is_hit = False
        self.alpha = 255  # 完全不透明
        self.flash_interval = 100  # 闪烁间隔(毫秒)
        self.last_flash_time = 0
        self.flash_state = False

        # 爆炸效果
        self.is_exploding = False
        self.explosion_start_time = 0
        self.explosion_duration = 1000  # 爆炸动画持续1秒
        self.explosion_particle_group_id = None  # 存储粒子组ID
        self.is_destroyed = False

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

                # 绘制坦克主体（方形）
                tank_color = COLOR_RED if self.color == 'red' else COLOR_BLUE if self.color == 'blue' else COLOR_GREEN if self.color == 'green' else COLOR_YELLOW
                pygame.draw.rect(self.original_image, tank_color, (0, 0, self.width, self.height))

                # 绘制坦克炮塔（圆形）
                pygame.draw.circle(self.original_image, COLOR_DARK_GREEN,
                                   (self.width // 2, self.height // 2), self.width // 3)

                # 绘制坦克炮管（向右方向的矩形）
                pygame.draw.rect(self.original_image, COLOR_DARK_GREEN,
                                 (self.width // 2, self.height // 2 - 2, self.width // 2, 4))

            # 初始方向设为向右
            self.direction = self.RIGHT
            self.update_image()

        except pygame.error as e:
            print(f"Error loading tank image: {e}")
            # 如果加载失败，创建一个默认图像
            self.original_image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.rect(self.original_image, self.color, (0, 0, self.width, self.height))
            self.update_image()

    def update_image(self):
        """更新坦克图像的旋转"""
        # 将角度转换为旋转值，pygame旋转是逆时针的，我们需要负值
        self.image = pygame.transform.rotate(self.original_image, -self.direction)

        # 获取旋转后的矩形并确保中心点不变
        new_rect = self.image.get_rect(center=(self.x, self.y))

        # 注意：这里只更新图像的绘制矩形，不影响碰撞盒
        self.rect = (new_rect.x, new_rect.y, new_rect.width, new_rect.height)

        # 单独更新碰撞盒，保持碰撞盒为正方形
        self.collision_box = (
            self.x - self.width / 2,
            self.y - self.height / 2,
            self.width,
            self.height
        )

    def set_direction(self, direction):
        """设置坦克方向"""
        self.direction = direction
        self.update_image()

    def move_in_direction(self, direction, obstacles=None):
        """向指定方向移动坦克"""
        self.set_direction(direction)
        self.moving = True
        return self.move(obstacles=obstacles)

    def move(self, direction=None, obstacles=None):
        """移动坦克，处理碰撞"""
        if not self.moving or self.is_exploding or self.is_destroyed:
            return False

        # 保存当前位置，以便在碰撞时回退
        self.prev_x = self.x
        self.prev_y = self.y

        # 计算移动向量
        angle_rad = math.radians(self.direction)
        dx, dy = vector_from_angle(angle_rad, self.speed)

        # 先尝试更新位置
        new_x = self.x + dx
        new_y = self.y + dy

        # 边界检查，留出一点余量避免卡边界
        margin = 2
        new_x = max(self.width / 2 + margin, min(SCREEN_WIDTH - self.width / 2 - margin, new_x))
        new_y = max(self.height / 2 + margin, min(SCREEN_HEIGHT - self.height / 2 - margin, new_y))

        # 分别检查X和Y方向的移动，实现滑墙效果
        can_move_x = True
        can_move_y = True

        if obstacles:
            # 使用稍小的碰撞盒检查，允许坦克通过狭窄空间
            # 缩小的碰撞盒仅用于碰撞检测
            collision_shrink = 2  # 每边缩小的像素数

            # 检查X方向移动
            test_rect_x = (
                new_x - self.width / 2 + collision_shrink,
                self.y - self.height / 2 + collision_shrink,
                self.width - 2 * collision_shrink,
                self.height - 2 * collision_shrink
            )

            for obstacle in obstacles:
                if getattr(obstacle, 'destroyed', False):
                    continue
                if DeterministicPhysics.check_collision(test_rect_x, obstacle.rect):
                    can_move_x = False
                    break

            # 检查Y方向移动
            test_rect_y = (
                self.x - self.width / 2 + collision_shrink,
                new_y - self.height / 2 + collision_shrink,
                self.width - 2 * collision_shrink,
                self.height - 2 * collision_shrink
            )

            for obstacle in obstacles:
                if getattr(obstacle, 'destroyed', False):
                    continue
                if DeterministicPhysics.check_collision(test_rect_y, obstacle.rect):
                    can_move_y = False
                    break

        # 应用移动，考虑滑墙
        if can_move_x:
            self.x = new_x
        if can_move_y:
            self.y = new_y

        # 更新碰撞矩形和绘制矩形
        # 注意视觉表现的矩形和碰撞检测的矩形可能稍有不同
        self.update_image()  # 这会更新self.rect和self.collision_box

        # 确保碰撞盒也被更新
        self.collision_box = (
            self.x - self.width / 2,
            self.y - self.height / 2,
            self.width,
            self.height
        )

        return can_move_x or can_move_y  # 只要有一个方向能移动就返回True

    def can_shoot(self, current_time):
        """检查是否可以射击"""
        return (self.ammo > 0 and
                (current_time - self.last_shot_time) >= self.reload_time and
                not self.is_exploding and not self.is_destroyed)

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
        if self.is_exploding or self.is_destroyed:
            return True  # 已经在爆炸或已销毁

        self.health -= damage

        # 设置受伤状态
        self.is_hit = True
        self.hit_time = current_time_ms()
        self.flash_state = True  # 强制开始闪烁
        self.alpha = 128  # 立即应用透明度

        # 检查是否死亡
        if self.health <= 0:
            self.health = 0
            self.start_explosion()
            return True
        return False

    def show_collision_effect(self):
        """显示坦克碰撞效果"""
        # 轻微闪烁以指示碰撞
        self.is_hit = True
        self.hit_time = current_time_ms()
        self.hit_flash_duration = 300  # 短时间闪烁
        self.alpha = 180  # 稍微降低透明度

    def start_explosion(self):
        """开始爆炸效果"""
        self.is_exploding = True
        self.explosion_start_time = current_time_ms()

        # 创建爆炸粒子效果
        explosion_colors = [COLOR_RED, COLOR_YELLOW, COLOR_ORANGE]
        self.explosion_particle_group_id = particle_system.create_explosion(
            x=self.x,
            y=self.y,
            color_palette=explosion_colors,
            count=30,
            min_speed=1,
            max_speed=5,
            min_size=2,
            max_size=6,
            duration=self.explosion_duration
        )

        # 同时创建一些碎片效果
        debris_colors = []
        if self.color == 'red':
            debris_colors = [(200, 0, 0), (150, 0, 0), (100, 0, 0)]
        elif self.color == 'blue':
            debris_colors = [(0, 0, 200), (0, 0, 150), (0, 0, 100)]
        elif self.color == 'green':
            debris_colors = [(0, 200, 0), (0, 150, 0), (0, 100, 0)]
        elif self.color == 'yellow':
            debris_colors = [(200, 200, 0), (150, 150, 0), (100, 100, 0)]
        else:
            debris_colors = [COLOR_GRAY, COLOR_DARK_GREEN, COLOR_BROWN]

        particle_system.create_debris(
            x=self.x,
            y=self.y,
            color_palette=debris_colors,
            count=15,
            min_speed=0.5,
            max_speed=3,
            min_size=1,
            max_size=4,
            duration=800,
            gravity=0.1
        )

    def update(self, delta_time):
        """更新坦克状态"""
        current_time = current_time_ms()

        # 处理爆炸效果
        if self.is_exploding:
            elapsed = current_time - self.explosion_start_time
            if elapsed > self.explosion_duration:
                self.is_exploding = False
                self.is_destroyed = True
                self.explosion_particle_group_id = None
            # 粒子由粒子系统更新，不需要在这里更新

        # 处理受伤闪烁效果
        if self.is_hit:
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
                self.alpha = 128 if self.flash_state else 255

        # 坦克生命值低时持续闪烁
        if self.health <= self.max_health * 0.3 and not self.is_hit and not self.is_exploding and not self.is_destroyed:
            if current_time - self.last_flash_time > self.flash_interval * 2:  # 低生命闪烁更慢
                self.last_flash_time = current_time
                self.flash_state = not self.flash_state

            # 设置较轻的闪烁效果
            self.alpha = 180 if self.flash_state else 255

    def draw(self, surface):
        """在屏幕上绘制坦克"""
        if self.is_destroyed:
            return  # 坦克已销毁，不绘制

        if self.is_exploding:
            # 爆炸粒子由粒子系统绘制，这里仅绘制淡出的坦克
            if self.image:
                # 计算淡出效果
                elapsed_ratio = min(1.0, (current_time_ms() - self.explosion_start_time) / self.explosion_duration)
                fade_alpha = int(255 * (1 - elapsed_ratio))

                if fade_alpha > 0:
                    # 创建带透明度的图像副本
                    image_copy = self.image.copy()
                    image_copy.set_alpha(fade_alpha)
                    surface.blit(image_copy, self.rect)
        else:
            # 绘制带透明度的坦克
            if self.image:
                # 创建带透明度的图像副本
                image_copy = self.image.copy()
                # 设置透明度
                image_copy.set_alpha(self.alpha)
                # 绘制
                surface.blit(image_copy, self.rect)
            else:
                # 如果没有图像，绘制一个简单的矩形
                rect_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                rect_color = COLOR_RED if self.color == 'red' else COLOR_BLUE if self.color == 'blue' else COLOR_GREEN if self.color == 'green' else COLOR_YELLOW
                rect_surface.fill((*pygame.Color(rect_color)[:3], self.alpha))
                surface.blit(rect_surface, self.rect)

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
            'last_shot_time': self.last_shot_time,
            'is_destroyed': self.is_destroyed
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
        if 'is_destroyed' in data and data['is_destroyed']:
            tank.is_destroyed = True
        tank.update_image()  # 更新图像以反映新方向
        return tank

    def apply_input(self, input_data, obstacles):
        """应用输入数据更新坦克状态"""
        if not input_data:
            return

        # 处理移动输入
        if 'movement' in input_data:
            movement = input_data['movement']

            if movement == 'up':
                self.move_in_direction(self.UP, obstacles)
            elif movement == 'right':
                self.move_in_direction(self.RIGHT, obstacles)
            elif movement == 'down':
                self.move_in_direction(self.DOWN, obstacles)
            elif movement == 'left':
                self.move_in_direction(self.LEFT, obstacles)
            elif movement == 'stop':
                self.moving = False

    def calculate_checksum(self):
        """计算坦克状态的校验和"""
        state = (
            self.x, self.y, self.direction, self.health,
            self.ammo, self.tank_id, self.moving
        )
        return hash(state)