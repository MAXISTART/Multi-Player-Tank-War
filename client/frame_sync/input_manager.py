# client/frame_sync/input_manager.py
import pygame
from common.constants import *


class InputManager:
    def __init__(self):
        self.current_inputs = {}
        self.previous_inputs = {}
        self.input_changed = False

    # client/frame_sync/input_manager.py
    def capture_input(self):
        """捕获当前帧的用户输入"""
        keys = pygame.key.get_pressed()

        # 清空当前输入
        self.previous_inputs = self.current_inputs.copy()
        self.current_inputs = {}

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

        # 检查输入是否变化
        self.input_changed = self.current_inputs != self.previous_inputs
        if self.input_changed:
            print(f"[Input] Input changed: {self.current_inputs}")

        return self.current_inputs

    def has_input_changed(self):
        """检查输入是否与上一帧相比发生变化"""
        return self.input_changed

    def serialize_input(self):
        """将输入序列化为可传输格式"""
        return self.current_inputs