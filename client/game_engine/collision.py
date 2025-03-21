# collision.py
"""
碰撞系统模块：处理游戏中的碰撞检测
"""

from common.deterministic_engine import DeterministicPhysics


class CollisionSystem:
    """
    碰撞系统：处理游戏中的碰撞检测

    主要功能：
    - 检测坦克与障碍物的碰撞
    - 检测坦克与坦克的碰撞
    - 检测子弹与物体的碰撞
    """

    @staticmethod
    def check_tank_obstacle_collision(tank, obstacles):
        """
        检查坦克与障碍物的碰撞

        Args:
            tank: 坦克对象
            obstacles: 障碍物列表

        Returns:
            碰撞的障碍物列表
        """
        collided_obstacles = []

        # 使用稍小的碰撞盒，允许坦克通过狭窄空间
        collision_shrink = 2  # 每边缩小的像素数
        tank_collision_box = (
            tank.x - tank.width / 2 + collision_shrink,
            tank.y - tank.height / 2 + collision_shrink,
            tank.width - 2 * collision_shrink,
            tank.height - 2 * collision_shrink
        )

        for obstacle in obstacles:
            if getattr(obstacle, 'destroyed', False):
                continue
            if DeterministicPhysics.check_collision(tank_collision_box, obstacle.rect):
                collided_obstacles.append(obstacle)

        return collided_obstacles

    @staticmethod
    def check_tank_tank_collision(tank, other_tanks):
        """
        检查坦克与其他坦克的碰撞

        Args:
            tank: 待检查的坦克
            other_tanks: 其他坦克列表

        Returns:
            (是否碰撞, 碰撞的坦克)
        """
        # 使用稍小的碰撞盒，允许坦克更容易通过
        collision_shrink = 1  # 每边缩小的像素数
        tank_collision_box = (
            tank.x - tank.width / 2 + collision_shrink,
            tank.y - tank.height / 2 + collision_shrink,
            tank.width - 2 * collision_shrink,
            tank.height - 2 * collision_shrink
        )

        for other_tank in other_tanks:
            if other_tank == tank or getattr(other_tank, 'is_destroyed', False):
                continue

            other_tank_collision_box = (
                other_tank.x - other_tank.width / 2 + collision_shrink,
                other_tank.y - other_tank.height / 2 + collision_shrink,
                other_tank.width - 2 * collision_shrink,
                other_tank.height - 2 * collision_shrink
            )

            if DeterministicPhysics.check_collision(tank_collision_box, other_tank_collision_box):
                return True, other_tank

        return False, None

    @staticmethod
    def check_bullet_obstacle_collision(bullet, obstacles):
        """
        检查子弹与障碍物的碰撞

        Args:
            bullet: 子弹对象
            obstacles: 障碍物列表

        Returns:
            (是否碰撞, 碰撞的障碍物)
        """
        if not bullet.active:
            return False, None

        for obstacle in obstacles:
            if getattr(obstacle, 'destroyed', False):
                continue
            if DeterministicPhysics.check_collision(bullet.rect, obstacle.rect):
                return True, obstacle

        return False, None

    @staticmethod
    def check_bullet_tank_collision(bullet, tanks):
        """
        检查子弹与坦克的碰撞

        Args:
            bullet: 子弹对象
            tanks: 坦克列表

        Returns:
            (是否碰撞, 碰撞的坦克)
        """
        if not bullet.active:
            return False, None

        for tank in tanks:
            # 跳过子弹所有者的坦克和已销毁的坦克
            if tank.tank_id == bullet.owner_id or getattr(tank, 'is_destroyed', False):
                continue

            if DeterministicPhysics.check_collision(bullet.rect, tank.rect):
                return True, tank

        return False, None

    @staticmethod
    def check_screen_bounds(position, size, screen_width, screen_height, margin=0):
        """
        检查对象是否超出屏幕边界

        Args:
            position: 对象位置 (x, y) - 中心点
            size: 对象大小 (width, height)
            screen_width, screen_height: 屏幕尺寸
            margin: 边界余量

        Returns:
            是否在屏幕边界内
        """
        x, y = position
        width, height = size

        half_width = width / 2
        half_height = height / 2

        return (
                x - half_width + margin >= 0 and
                x + half_width - margin <= screen_width and
                y - half_height + margin >= 0 and
                y + half_height - margin <= screen_height
        )

    @staticmethod
    def handle_tank_collision(moving_tank, other_tanks):
        """
        处理坦克与其他坦克的碰撞

        Args:
            moving_tank: 移动中的坦克
            other_tanks: 其他坦克列表

        Returns:
            是否发生碰撞
        """
        collision, collided_tank = CollisionSystem.check_tank_tank_collision(
            moving_tank, other_tanks
        )

        if collision:
            # 撤销移动
            moving_tank.x = moving_tank.prev_x
            moving_tank.y = moving_tank.prev_y

            # 更新碰撞盒
            moving_tank.collision_box = (
                moving_tank.x - moving_tank.width / 2,
                moving_tank.y - moving_tank.height / 2,
                moving_tank.width,
                moving_tank.height
            )

            # 更新视觉矩形
            moving_tank.update_image()

            # 显示碰撞效果
            moving_tank.show_collision_effect()
            collided_tank.show_collision_effect()

            return True

        return False