# particle_system.py
"""
粒子系统模块：用于创建和管理粒子效果
"""

import pygame
import math
import random
from common.constants import *
from common.utils import current_time_ms


class Particle:
    """单个粒子类"""

    def __init__(self, x, y, dx, dy, size, color, life_duration, gravity=0):
        """初始化粒子"""
        self.x = x
        self.y = y
        self.dx = dx  # x方向速度
        self.dy = dy  # y方向速度
        self.size = size  # 初始大小
        self.original_size = size  # 保存初始大小用于计算缩放
        self.color = color  # (r, g, b) 颜色元组
        self.creation_time = current_time_ms()
        self.life_duration = life_duration  # 生命周期(毫秒)
        self.gravity = gravity  # 重力影响
        self.alpha = 255  # 透明度
        self.active = True  # 粒子是否活跃

    def update(self, delta_time):
        """更新粒子状态"""
        if not self.active:
            return

        # 计算已过去时间
        current_time = current_time_ms()
        elapsed = current_time - self.creation_time

        # 检查是否超过生命周期
        if elapsed >= self.life_duration:
            self.active = False
            return

        # 计算生命周期比例(0-1之间)
        life_ratio = elapsed / self.life_duration

        # 更新位置
        seconds = delta_time  # 转换为秒
        self.x += self.dx * seconds * 60  # 速度标准化为60FPS
        self.y += self.dy * seconds * 60

        # 应用重力
        self.dy += self.gravity * seconds

        # 随着生命周期更新大小
        size_factor = 1.0 - life_ratio  # 线性缩小
        self.size = max(0.1, self.original_size * size_factor)

        # 随着生命周期更新透明度
        self.alpha = int(255 * (1.0 - life_ratio))

    def draw(self, surface):
        """绘制粒子"""
        if not self.active or self.size <= 0:
            return

        # 对于非常小的粒子，确保至少绘制1像素
        size = max(1, int(self.size))

        # 创建带有透明度的颜色
        color_with_alpha = (*self.color, self.alpha)

        # 创建表面并绘制粒子
        if size <= 1:
            # 单像素直接绘制
            surface.set_at((int(self.x), int(self.y)), color_with_alpha)
        else:
            # 创建带透明度的圆形粒子
            particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surface, color_with_alpha, (size, size), size)
            surface.blit(particle_surface, (int(self.x - size), int(self.y - size)))


class ParticleSystem:
    """粒子系统类"""

    def __init__(self):
        """初始化粒子系统"""
        self.particle_groups = {}  # 存储多个粒子组，键为组ID
        self.next_group_id = 0  # 下一个可用的组ID

    def create_explosion(self, x, y, color_palette, count=30, min_speed=1, max_speed=5,
                         min_size=2, max_size=6, duration=1000, gravity=0):
        """
        创建爆炸效果

        Args:
            x, y: 爆炸中心坐标
            color_palette: 颜色列表，粒子将随机选择其中的颜色
            count: 粒子数量
            min_speed, max_speed: 粒子速度范围
            min_size, max_size: 粒子大小范围
            duration: 爆炸持续时间(毫秒)
            gravity: 重力系数，正值使粒子下落，负值使粒子上升

        Returns:
            粒子组ID，可用于检查效果是否完成
        """
        particles = []

        for _ in range(count):
            # 随机角度、速度和大小
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(min_speed, max_speed)
            size = random.randint(min_size, max_size)

            # 随机选择颜色
            color = random.choice(color_palette)

            # 计算速度向量
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed

            # 创建粒子，生命周期随机化以增加多样性
            life = random.uniform(0.7, 1.0) * duration
            particle = Particle(x, y, dx, dy, size, color, life, gravity)
            particles.append(particle)

        # 将粒子组添加到系统中
        group_id = self.next_group_id
        self.particle_groups[group_id] = particles
        self.next_group_id += 1

        return group_id

    def create_debris(self, x, y, color_palette, count=15, min_speed=0.5, max_speed=3,
                      min_size=1, max_size=4, duration=800, gravity=0.1):
        """
        创建碎片效果，类似爆炸但带有重力

        参数同create_explosion，但默认值针对碎片效果进行了优化
        """
        return self.create_explosion(x, y, color_palette, count, min_speed, max_speed,
                                     min_size, max_size, duration, gravity)

    def create_spark(self, x, y, direction_angle, spread_angle=30, color_palette=None,
                     count=10, min_speed=3, max_speed=7, min_size=1, max_size=3, duration=500):
        """
        创建火花效果，在指定方向上喷射粒子

        Args:
            x, y: 火花起始坐标
            direction_angle: 火花方向角度(度)
            spread_angle: 扩散角度(度)，粒子将在direction_angle±spread_angle的范围内生成
            color_palette: 颜色列表，默认为红黄色系
            其他参数同create_explosion
        """
        if color_palette is None:
            color_palette = [COLOR_RED, COLOR_YELLOW, COLOR_ORANGE]

        particles = []

        for _ in range(count):
            # 计算随机角度(弧度)，在指定方向上扩散
            angle_offset = random.uniform(-spread_angle, spread_angle)
            angle_rad = math.radians(direction_angle + angle_offset)

            speed = random.uniform(min_speed, max_speed)
            size = random.uniform(min_size, max_size)

            # 随机选择颜色
            color = random.choice(color_palette)

            # 计算速度向量
            dx = math.cos(angle_rad) * speed
            dy = math.sin(angle_rad) * speed

            # 创建粒子，火花通常寿命较短
            life = random.uniform(0.5, 1.0) * duration
            particle = Particle(x, y, dx, dy, size, color, life)
            particles.append(particle)

        # 将粒子组添加到系统中
        group_id = self.next_group_id
        self.particle_groups[group_id] = particles
        self.next_group_id += 1

        return group_id

    def is_group_active(self, group_id):
        """检查粒子组是否仍然活跃"""
        if group_id not in self.particle_groups:
            return False

        # 如果组中有任何活跃粒子，则组是活跃的
        return any(particle.active for particle in self.particle_groups[group_id])

    def remove_group(self, group_id):
        """移除粒子组"""
        if group_id in self.particle_groups:
            del self.particle_groups[group_id]

    def update(self, delta_time):
        """更新所有粒子组"""
        # 记录要移除的不活跃组
        groups_to_remove = []

        for group_id, particles in self.particle_groups.items():
            # 更新每个粒子
            for particle in particles:
                particle.update(delta_time)

            # 过滤掉不活跃的粒子
            self.particle_groups[group_id] = [p for p in particles if p.active]

            # 如果组内没有活跃粒子，标记为移除
            if not self.particle_groups[group_id]:
                groups_to_remove.append(group_id)

        # 移除不活跃的组
        for group_id in groups_to_remove:
            self.remove_group(group_id)

    def draw(self, surface):
        """绘制所有粒子组"""
        for particles in self.particle_groups.values():
            for particle in particles:
                particle.draw(surface)


# 创建全局粒子系统实例
particle_system = ParticleSystem()