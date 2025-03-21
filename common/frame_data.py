# frame_data.py
"""
帧数据结构模块：定义帧同步系统的数据结构

包含输入帧和状态帧的定义，以及序列化和反序列化功能。
"""

import time
import json
import hashlib
from common.utils import calculate_checksum


class InputCommand:
    """
    输入命令类：表示玩家在一帧中的输入

    主要功能：
    - 存储键盘/鼠标输入状态
    - 序列化和反序列化
    """

    def __init__(self, player_id=None, movement=None, shooting=False, special=None):
        """初始化输入命令"""
        self.player_id = player_id  # 玩家ID
        self.movement = movement  # 移动方向: 'up', 'down', 'left', 'right', 'stop'
        self.shooting = shooting  # 是否射击
        self.special = special  # 特殊技能（预留）
        self.timestamp = time.time()  # 本地时间戳，用于计算延迟

    def to_dict(self):
        """将输入命令转换为字典"""
        return {
            'player_id': self.player_id,
            'movement': self.movement,
            'shooting': self.shooting,
            'special': self.special,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建输入命令"""
        cmd = cls(
            player_id=data.get('player_id'),
            movement=data.get('movement'),
            shooting=data.get('shooting'),
            special=data.get('special')
        )
        if 'timestamp' in data:
            cmd.timestamp = data['timestamp']
        return cmd

    def serialize(self):
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict())

    @classmethod
    def deserialize(cls, json_str):
        """从JSON字符串反序列化"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError:
            return None

    def __str__(self):
        """字符串表示"""
        return f"InputCommand(player={self.player_id}, move={self.movement}, shoot={self.shooting})"


class InputFrame:
    """
    输入帧类：包含一帧中所有玩家的输入

    主要功能：
    - 存储一帧中的所有输入命令
    - 管理帧ID和时间戳
    - 序列化和反序列化
    """

    def __init__(self, frame_id=0):
        """初始化输入帧"""
        self.frame_id = frame_id  # 帧ID，在游戏进程中唯一
        self.commands = {}  # 玩家ID -> 输入命令的映射
        self.timestamp = time.time()  # 帧创建时间

    def add_command(self, player_id, command):
        """添加玩家的输入命令"""
        if isinstance(command, InputCommand):
            self.commands[player_id] = command
        else:
            # 如果是字典，转换为InputCommand
            self.commands[player_id] = InputCommand.from_dict(command)

    def get_command(self, player_id):
        """获取指定玩家的输入命令"""
        return self.commands.get(player_id)

    def to_dict(self):
        """将输入帧转换为字典"""
        return {
            'frame_id': self.frame_id,
            'timestamp': self.timestamp,
            'commands': {pid: cmd.to_dict() for pid, cmd in self.commands.items()}
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建输入帧"""
        frame = cls(frame_id=data.get('frame_id', 0))
        frame.timestamp = data.get('timestamp', time.time())

        for pid, cmd_data in data.get('commands', {}).items():
            frame.add_command(pid, InputCommand.from_dict(cmd_data))

        return frame

    def serialize(self):
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict())

    @classmethod
    def deserialize(cls, json_str):
        """从JSON字符串反序列化"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError:
            return None

    def get_checksum(self):
        """计算帧校验和，用于验证一致性"""
        # 只使用输入命令计算校验和，忽略时间戳
        data_for_checksum = {
            'frame_id': self.frame_id,
            'commands': {pid: cmd.to_dict() for pid, cmd in self.commands.items()}
        }
        # 使用JSON字符串的哈希作为校验和
        return hashlib.md5(json.dumps(data_for_checksum, sort_keys=True).encode()).hexdigest()

    def __str__(self):
        """字符串表示"""
        return f"InputFrame(id={self.frame_id}, players={len(self.commands)})"


class StateFrame:
    """
    状态帧类：包含一帧中游戏的完整状态

    主要功能：
    - 存储游戏状态（坦克、子弹等）
    - 管理帧ID和检查点
    - 序列化和反序列化
    """

    def __init__(self, frame_id=0, is_keyframe=False):
        """初始化状态帧"""
        self.frame_id = frame_id  # 帧ID
        self.is_keyframe = is_keyframe  # 是否为关键帧（完整状态）
        self.timestamp = time.time()  # 帧创建时间
        self.game_state = {}  # 游戏状态
        self.checksum = ""  # 状态校验和

    def set_game_state(self, state):
        """设置游戏状态"""
        self.game_state = state
        self._update_checksum()

    def _update_checksum(self):
        """更新状态校验和"""
        # 使用游戏状态计算校验和，忽略时间戳
        data_for_checksum = {
            'frame_id': self.frame_id,
            'game_state': self.game_state
        }
        self.checksum = calculate_checksum(data_for_checksum)

    def to_dict(self):
        """将状态帧转换为字典"""
        return {
            'frame_id': self.frame_id,
            'is_keyframe': self.is_keyframe,
            'timestamp': self.timestamp,
            'game_state': self.game_state,
            'checksum': self.checksum
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建状态帧"""
        frame = cls(
            frame_id=data.get('frame_id', 0),
            is_keyframe=data.get('is_keyframe', False)
        )
        frame.timestamp = data.get('timestamp', time.time())
        frame.game_state = data.get('game_state', {})
        frame.checksum = data.get('checksum', "")
        return frame

    def serialize(self):
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict())

    @classmethod
    def deserialize(cls, json_str):
        """从JSON字符串反序列化"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError:
            return None

    def verify_checksum(self):
        """验证校验和是否匹配"""
        current_checksum = self.checksum
        self._update_checksum()
        return current_checksum == self.checksum

    def __str__(self):
        """字符串表示"""
        return f"StateFrame(id={self.frame_id}, keyframe={self.is_keyframe})"


class FrameBuffer:
    """
    帧缓冲区：存储和管理输入帧和状态帧

    主要功能：
    - 维护帧历史记录
    - 帧回滚和重放
    - 缓冲区管理
    """

    def __init__(self, max_size=300):
        """初始化帧缓冲区"""
        self.max_size = max_size  # 最大缓冲区大小
        self.input_frames = {}  # 帧ID -> 输入帧
        self.state_frames = {}  # 帧ID -> 状态帧
        self.last_confirmed_frame_id = -1  # 最后确认的帧ID
        self.last_executed_frame_id = -1  # 最后执行的帧ID

    def add_input_frame(self, frame):
        """添加输入帧"""
        if isinstance(frame, dict):
            frame = InputFrame.from_dict(frame)

        self.input_frames[frame.frame_id] = frame
        self._cleanup_buffer()

    def add_state_frame(self, frame):
        """添加状态帧"""
        if isinstance(frame, dict):
            frame = StateFrame.from_dict(frame)

        self.state_frames[frame.frame_id] = frame
        self._cleanup_buffer()

    def get_input_frame(self, frame_id):
        """获取指定帧ID的输入帧"""
        return self.input_frames.get(frame_id)

    def get_state_frame(self, frame_id):
        """获取指定帧ID的状态帧"""
        return self.state_frames.get(frame_id)

    def get_last_keyframe(self):
        """获取最近的关键帧"""
        keyframes = [f for f in self.state_frames.values() if f.is_keyframe]
        if not keyframes:
            return None
        return max(keyframes, key=lambda f: f.frame_id)

    def _cleanup_buffer(self):
        """清理过旧的帧，保持缓冲区大小在限制内"""
        # 如果缓冲区大小超过限制，移除最旧的帧
        while len(self.input_frames) > self.max_size:
            oldest_frame_id = min(self.input_frames.keys())
            del self.input_frames[oldest_frame_id]

        while len(self.state_frames) > self.max_size:
            oldest_frame_id = min(self.state_frames.keys())
            del self.state_frames[oldest_frame_id]

    def set_confirmed_frame(self, frame_id):
        """设置最后确认的帧ID"""
        self.last_confirmed_frame_id = frame_id

    def set_executed_frame(self, frame_id):
        """设置最后执行的帧ID"""
        self.last_executed_frame_id = frame_id

    def get_input_frames_range(self, start_frame_id, end_frame_id):
        """获取指定范围内的输入帧"""
        return {
            fid: frame for fid, frame in self.input_frames.items()
            if start_frame_id <= fid <= end_frame_id
        }

    def __str__(self):
        """字符串表示"""
        return (f"FrameBuffer(inputs={len(self.input_frames)}, "
                f"states={len(self.state_frames)}, "
                f"confirmed={self.last_confirmed_frame_id}, "
                f"executed={self.last_executed_frame_id})")