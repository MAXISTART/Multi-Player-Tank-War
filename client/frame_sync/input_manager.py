# client/frame_sync/input_manager.py
import pygame
from common.constants import *


class InputManager:
    def __init__(self):
        self.current_inputs = {'movement': 'stop', 'shoot': False}
        self.previous_inputs = {'movement': 'stop', 'shoot': False}
        self.has_non_empty_input = False

    def capture_input(self):
        """捕获当前帧的用户输入"""
        keys = pygame.key.get_pressed()

        # 备份上一帧的输入
        self.previous_inputs = self.current_inputs.copy()
        self.current_inputs = {'movement': 'stop', 'shoot': False}  # 默认为空输入

        # 移动输入
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.current_inputs['movement'] = 'up'
            print("[Input] Captured: UP")
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.current_inputs['movement'] = 'right'
            print("[Input] Captured: RIGHT")
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.current_inputs['movement'] = 'down'
            print("[Input] Captured: DOWN")
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.current_inputs['movement'] = 'left'
            print("[Input] Captured: LEFT")
        else:
            self.current_inputs['movement'] = 'stop'

        # 射击输入
        self.current_inputs['shoot'] = keys[pygame.K_SPACE]
        if keys[pygame.K_SPACE]:
            print("[Input] Captured: SHOOT")

        # 检查输入是否为非空
        self.has_non_empty_input = not self.is_input_empty(self.current_inputs)
        if self.has_non_empty_input:
            print(f"[Input] Non-empty input captured: {self.current_inputs}")

        return self.current_inputs

    def is_input_non_empty(self):
        """检查输入是否非空"""
        return self.has_non_empty_input

    def is_input_empty(self, inputs):
        """检查输入是否为空（默认状态）"""
        return inputs['movement'] == 'stop' and not inputs['shoot']

    def serialize_input(self):
        """将输入序列化为可传输格式"""
        return self.current_inputs