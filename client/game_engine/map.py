# map.py
"""
地图类模块：定义游戏地图和障碍物的生成与管理
"""

import pygame
import random
import os
import json
import math
from common.constants import *
from client.game_engine.obstacle import WallObstacle, BrickObstacle
from common.deterministic_engine import DeterministicRandom, DeterministicPhysics


class Map:
    """
    地图类：管理游戏地图和障碍物

    主要功能：
    - 地图生成（随机和预设）
    - 障碍物管理
    - 出生点管理
    - 地图渲染
    """

    def __init__(self, map_name=None):
        """初始化地图对象"""
        self.screen_width = SCREEN_WIDTH
        self.screen_height = SCREEN_HEIGHT
        self.grid_size = GRID_SIZE
        self.map_width = MAP_WIDTH
        self.map_height = MAP_HEIGHT

        # 使用确定性随机生成器
        self.random = DeterministicRandom()

        # 地图网格
        self.grid = [[0 for _ in range(self.map_width)] for _ in range(self.map_height)]

        # 障碍物列表
        self.obstacles = []

        # 出生点列表
        self.spawn_points = []

        # 如果提供了地图名称，则加载，否则生成默认地图
        if map_name:
            self.load_map(map_name)
        else:
            self.generate_default_map()

    def generate_default_map(self):
        """生成默认地图"""
        # 创建边界墙
        self._create_boundaries()

        # 随机生成一些砖块
        self._generate_random_bricks(15)

        # 初始化默认出生点 - 确保它们远离障碍物
        self._initialize_default_spawn_points()

    def generate_random_map(self, seed=None):
        """生成随机地图"""
        if seed is not None:
            self.random.seed(seed)

        # 清空已有障碍物
        self.obstacles = []
        self.spawn_points = []

        # 创建边界墙
        self._create_boundaries()

        # 随机生成砖块
        self._generate_random_bricks(30)  # 生成30个随机砖块

        # 随机生成一些墙
        self._generate_random_walls(10)  # 生成10个随机墙

        # 初始化默认出生点
        self._initialize_default_spawn_points()

    def _initialize_default_spawn_points(self):
        """初始化默认出生点，确保它们远离障碍物"""
        # 清空现有出生点
        self.spawn_points = []

        # 定义基本的四个角落出生点位置，远离墙体
        # 确保离边界墙足够远，防止卡墙
        wall_offset = self.grid_size * 2.5
        potential_points = [
            (wall_offset, wall_offset),  # 左上角
            (self.screen_width - wall_offset, wall_offset),  # 右上角
            (wall_offset, self.screen_height - wall_offset),  # 左下角
            (self.screen_width - wall_offset, self.screen_height - wall_offset)  # 右下角
        ]

        # 检查每个点是否安全（不与障碍物重叠），如果不安全则调整
        for point in potential_points:
            safe_point = self._find_safe_spawn_point(point[0], point[1])
            if safe_point:
                self.spawn_points.append(safe_point)

        # 如果没有找到足够的安全点，添加中心区域的点
        if len(self.spawn_points) < 4:
            center_x = self.screen_width / 2
            center_y = self.screen_height / 2
            for offset in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
                center_point = (center_x + offset[0] * 50, center_y + offset[1] * 50)
                safe_point = self._find_safe_spawn_point(center_point[0], center_point[1])
                if safe_point and safe_point not in self.spawn_points:
                    self.spawn_points.append(safe_point)
                    if len(self.spawn_points) >= 4:
                        break

    def _find_safe_spawn_point(self, base_x, base_y, max_attempts=20):
        """
        在基准点周围找到一个安全的出生点

        Args:
            base_x, base_y: 基准点坐标
            max_attempts: 最大尝试次数

        Returns:
            安全的出生点坐标，如果找不到则返回None
        """
        # 首先检查原始点是否安全
        if self._is_safe_spawn_location(base_x, base_y, TANK_WIDTH, TANK_HEIGHT):
            return (base_x, base_y)

        # 原始点不安全，开始在周围搜索
        search_radius = self.grid_size

        for attempt in range(max_attempts):
            # 增加搜索半径
            search_radius += self.grid_size * 0.5

            # 在当前半径范围内随机选择点
            angle = self.random.uniform(0, 2 * math.pi)
            distance = self.random.uniform(0, search_radius)
            x = base_x + distance * math.cos(angle)
            y = base_y + distance * math.sin(angle)

            # 确保点在地图边界内
            x = max(TANK_WIDTH, min(self.screen_width - TANK_WIDTH, x))
            y = max(TANK_HEIGHT, min(self.screen_height - TANK_HEIGHT, y))

            # 检查这个点是否安全
            if self._is_safe_spawn_location(x, y, TANK_WIDTH, TANK_HEIGHT):
                return (x, y)

        # 如果找不到安全点，返回None
        print(f"Warning: Could not find safe spawn point near ({base_x}, {base_y})")
        return None

    def _is_safe_spawn_location(self, x, y, width, height, margin=5):
        """
        检查给定位置是否适合坦克出生

        Args:
            x, y: 位置坐标（中心点）
            width, height: 实体尺寸
            margin: 额外边距

        Returns:
            如果位置安全返回True
        """
        # 创建稍微小一点的坦克碰撞盒
        # 减小安全检查的边距，确保出生点不会过于受限
        tank_rect = (
            x - width / 2,
            y - height / 2,
            width,
            height
        )

        # 检查是否与任何障碍物重叠
        for obstacle in self.obstacles:
            if DeterministicPhysics.check_collision(tank_rect, obstacle.rect):
                return False

        # 检查是否太靠近地图边缘
        if (x - width / 2 - margin < 0 or
                x + width / 2 + margin > self.screen_width or
                y - height / 2 - margin < 0 or
                y + height / 2 + margin > self.screen_height):
            return False

        # 安全点
        return True

    def _add_additional_spawn_points(self, count):
        """添加额外的出生点"""
        attempts = 0
        max_attempts = 100
        added = 0

        while added < count and attempts < max_attempts:
            attempts += 1

            # 随机选择地图上的一点
            x = self.random.randint(self.grid_size * 2, self.screen_width - self.grid_size * 2)
            y = self.random.randint(self.grid_size * 2, self.screen_height - self.grid_size * 2)

            # 检查是否安全，且距离现有出生点足够远
            if self._is_safe_spawn_location(x, y, TANK_WIDTH, TANK_HEIGHT):
                # 检查与现有出生点的距离
                too_close = False
                for point in self.spawn_points:
                    if DeterministicPhysics.distance((x, y), point) < TANK_WIDTH * 3:
                        too_close = True
                        break

                if not too_close:
                    self.spawn_points.append((x, y))
                    added += 1

    def load_map(self, map_name):
        """从文件加载地图"""
        map_path = os.path.join(MAPS_DIR, f"{map_name}.json")
        try:
            with open(map_path, 'r') as f:
                map_data = json.load(f)

            # 清空已有障碍物
            self.obstacles = []
            self.spawn_points = []

            # 加载障碍物
            for obstacle in map_data.get('obstacles', []):
                obstacle_type = obstacle.get('type')
                x, y = obstacle.get('x'), obstacle.get('y')
                width, height = obstacle.get('width', OBSTACLE_SIZE), obstacle.get('height', OBSTACLE_SIZE)

                if obstacle_type == 'wall':
                    self.obstacles.append(WallObstacle(x, y, width, height))
                elif obstacle_type == 'brick':
                    self.obstacles.append(BrickObstacle(x, y, width, height))

            # 加载出生点
            self.spawn_points = map_data.get('spawn_points', [])

            # 如果没有出生点或出生点不安全，重新生成
            if not self.spawn_points or not self._validate_spawn_points():
                self._initialize_default_spawn_points()

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading map {map_name}: {e}")
            # 如果加载失败，生成默认地图
            self.generate_default_map()

    def _validate_spawn_points(self):
        """验证所有出生点是否安全"""
        safe_points = []
        for point in self.spawn_points:
            x, y = point[0], point[1]
            if self._is_safe_spawn_location(x, y, TANK_WIDTH, TANK_HEIGHT):
                safe_points.append(point)
            else:
                # 尝试找到附近的安全点
                safe_point = self._find_safe_spawn_point(x, y)
                if safe_point:
                    safe_points.append(safe_point)

        # 更新出生点列表
        self.spawn_points = safe_points

        # 如果没有足够的安全点，返回False
        return len(self.spawn_points) >= 4

    def save_map(self, map_name):
        """保存地图到文件"""
        map_data = {
            'obstacles': [],
            'spawn_points': self.spawn_points
        }

        # 保存障碍物数据
        for obstacle in self.obstacles:
            obstacle_type = 'wall' if isinstance(obstacle, WallObstacle) else 'brick'
            map_data['obstacles'].append({
                'type': obstacle_type,
                'x': obstacle.x,
                'y': obstacle.y,
                'width': obstacle.width,
                'height': obstacle.height
            })

        # 确保地图目录存在
        os.makedirs(MAPS_DIR, exist_ok=True)

        # 保存到文件
        map_path = os.path.join(MAPS_DIR, f"{map_name}.json")
        with open(map_path, 'w') as f:
            json.dump(map_data, f, indent=4)

    def _create_boundaries(self):
        """创建地图边界墙"""
        wall_size = OBSTACLE_SIZE

        # 上边界
        for x in range(0, self.screen_width, wall_size):
            self.obstacles.append(WallObstacle(x, 0))

        # 下边界
        for x in range(0, self.screen_width, wall_size):
            self.obstacles.append(WallObstacle(x, self.screen_height - wall_size))

        # 左边界
        for y in range(wall_size, self.screen_height - wall_size, wall_size):
            self.obstacles.append(WallObstacle(0, y))

        # 右边界
        for y in range(wall_size, self.screen_height - wall_size, wall_size):
            self.obstacles.append(WallObstacle(self.screen_width - wall_size, y))

    def _generate_random_bricks(self, count):
        """随机生成砖块"""
        for _ in range(count):
            # 随机选择网格位置
            grid_x = self.random.randint(1, self.map_width - 2)
            grid_y = self.random.randint(1, self.map_height - 2)

            # 转换为像素坐标
            x = grid_x * self.grid_size
            y = grid_y * self.grid_size

            # 创建砖块
            self.obstacles.append(BrickObstacle(x, y))

    def _generate_random_walls(self, count):
        """随机生成墙"""
        for _ in range(count):
            # 随机选择网格位置
            grid_x = self.random.randint(1, self.map_width - 2)
            grid_y = self.random.randint(1, self.map_height - 2)

            # 转换为像素坐标
            x = grid_x * self.grid_size
            y = grid_y * self.grid_size

            # 创建墙
            self.obstacles.append(WallObstacle(x, y))

    def get_spawn_points(self):
        """获取所有可用的出生点位置"""
        if not self.spawn_points:
            self._initialize_default_spawn_points()
        return self.spawn_points

    def get_random_spawn_point(self, used_points=None):
        """
        获取一个随机出生点，避免与已使用的点重叠

        Args:
            used_points: 已经被使用的出生点列表，避免重复

        Returns:
            随机选择的出生点坐标元组 (x, y)
        """
        # 获取所有可用的出生点
        spawn_points = self.get_spawn_points()

        if used_points is None:
            used_points = []

        # 过滤掉已使用的出生点
        available_points = [point for point in spawn_points if point not in used_points]

        # 如果没有可用出生点，尝试创建新点
        if not available_points:
            # 选择一个已使用的点作为基准，寻找附近的安全位置
            base_point = used_points[-1] if used_points else (self.screen_width // 2, self.screen_height // 2)
            new_point = self._find_safe_spawn_point(base_point[0], base_point[1])

            if new_point:
                return new_point
            else:
                # 如果仍然找不到安全点，选择基准点并警告
                print("Warning: Using a potentially unsafe spawn point")
                return base_point

        # 从可用出生点中随机选择一个
        return self.random.choice(available_points)

    def _check_overlap(self, point, rect, margin=0):
        """
        检查点与矩形是否重叠（考虑边距）

        Args:
            point: 要检查的点 (x, y)
            rect: 矩形 (x, y, width, height)
            margin: 额外边距

        Returns:
            如果点与矩形（加上边距）重叠，返回True
        """
        x, y = point
        rx, ry, rw, rh = rect

        # 扩展矩形边界
        rx -= margin
        ry -= margin
        rw += 2 * margin
        rh += 2 * margin

        return (rx <= x <= rx + rw) and (ry <= y <= ry + rh)

    def update(self):
        """更新地图状态"""
        # 移除被销毁的障碍物
        obstacles_to_remove = []
        for obstacle in self.obstacles:
            if getattr(obstacle, 'destroyed', False):
                obstacles_to_remove.append(obstacle)

        for obstacle in obstacles_to_remove:
            try:
                self.obstacles.remove(obstacle)
            except ValueError:
                pass  # 如果障碍物已被移除，忽略错误

    def draw(self, surface):
        """绘制地图"""
        # 绘制背景
        surface.fill(COLOR_BLACK)

        # 绘制障碍物
        for obstacle in self.obstacles:
            obstacle.draw(surface)

    def get_obstacles_at(self, grid_x, grid_y):
        """获取指定网格位置的障碍物"""
        x = grid_x * self.grid_size
        y = grid_y * self.grid_size

        obstacles_at_position = []
        for obstacle in self.obstacles:
            if (obstacle.x == x and obstacle.y == y):
                obstacles_at_position.append(obstacle)

        return obstacles_at_position

    def clear_obstacles(self):
        """清空所有障碍物"""
        self.obstacles = []

    def add_obstacle(self, obstacle):
        """添加障碍物"""
        self.obstacles.append(obstacle)

    def remove_obstacle(self, obstacle):
        """移除障碍物"""
        if obstacle in self.obstacles:
            self.obstacles.remove(obstacle)

    def add_spawn_point(self, x, y):
        """添加出生点"""
        self.spawn_points.append((x, y))

    def get_size(self):
        """获取地图尺寸"""
        return (self.screen_width, self.screen_height)