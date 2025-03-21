# protocol.py
"""
通信协议模块：定义客户端和服务器之间的通信协议

包含消息类型定义、序列化和反序列化功能。
"""

import json
import time
from common.frame_data import InputFrame, StateFrame, InputCommand

# 消息类型常量
MSG_TYPE_CONNECT = 1  # 连接请求
MSG_TYPE_DISCONNECT = 2  # 断开连接
MSG_TYPE_JOIN_GAME = 3  # 加入游戏
MSG_TYPE_LEAVE_GAME = 4  # 离开游戏
MSG_TYPE_GAME_START = 5  # 游戏开始
MSG_TYPE_GAME_END = 6  # 游戏结束
MSG_TYPE_INPUT = 7  # 输入命令
MSG_TYPE_STATE_UPDATE = 8  # 状态更新
MSG_TYPE_PING = 9  # Ping消息
MSG_TYPE_PONG = 10  # Pong回复
MSG_TYPE_ERROR = 11  # 错误消息
MSG_TYPE_PLAYER_READY = 12  # 玩家准备
MSG_TYPE_ROOM_INFO = 13  # 房间信息


class Message:
    """
    消息类：表示客户端和服务器之间的通信消息

    主要功能：
    - 定义消息结构
    - 序列化和反序列化
    """

    def __init__(self, msg_type, data=None):
        """初始化消息"""
        self.msg_type = msg_type  # 消息类型
        self.data = data or {}  # 消息数据
        self.timestamp = time.time()  # 消息时间戳

    def to_dict(self):
        """将消息转换为字典"""
        return {
            'type': self.msg_type,
            'data': self.data,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建消息"""
        msg = cls(
            msg_type=data.get('type'),
            data=data.get('data', {})
        )
        msg.timestamp = data.get('timestamp', time.time())
        return msg

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
        type_names = {
            MSG_TYPE_CONNECT: "CONNECT",
            MSG_TYPE_DISCONNECT: "DISCONNECT",
            MSG_TYPE_JOIN_GAME: "JOIN_GAME",
            MSG_TYPE_LEAVE_GAME: "LEAVE_GAME",
            MSG_TYPE_GAME_START: "GAME_START",
            MSG_TYPE_GAME_END: "GAME_END",
            MSG_TYPE_INPUT: "INPUT",
            MSG_TYPE_STATE_UPDATE: "STATE_UPDATE",
            MSG_TYPE_PING: "PING",
            MSG_TYPE_PONG: "PONG",
            MSG_TYPE_ERROR: "ERROR",
            MSG_TYPE_PLAYER_READY: "PLAYER_READY",
            MSG_TYPE_ROOM_INFO: "ROOM_INFO"
        }
        type_name = type_names.get(self.msg_type, f"UNKNOWN({self.msg_type})")
        return f"Message({type_name}, data_size={len(str(self.data))})"


# 消息工厂函数
def create_connect_message(client_id, client_info=None):
    """创建连接请求消息"""
    data = {
        'client_id': client_id,
        'client_info': client_info or {}
    }
    return Message(MSG_TYPE_CONNECT, data)


def create_disconnect_message(client_id, reason=None):
    """创建断开连接消息"""
    data = {
        'client_id': client_id,
        'reason': reason
    }
    return Message(MSG_TYPE_DISCONNECT, data)


def create_join_game_message(client_id, room_id=None):
    """创建加入游戏消息"""
    data = {
        'client_id': client_id,
        'room_id': room_id
    }
    return Message(MSG_TYPE_JOIN_GAME, data)


def create_leave_game_message(client_id, room_id):
    """创建离开游戏消息"""
    data = {
        'client_id': client_id,
        'room_id': room_id
    }
    return Message(MSG_TYPE_LEAVE_GAME, data)


def create_game_start_message(room_id, game_info):
    """创建游戏开始消息"""
    data = {
        'room_id': room_id,
        'game_info': game_info
    }
    return Message(MSG_TYPE_GAME_START, data)


def create_game_end_message(room_id, result):
    """创建游戏结束消息"""
    data = {
        'room_id': room_id,
        'result': result
    }
    return Message(MSG_TYPE_GAME_END, data)


def create_input_message(player_id, frame_id, input_command):
    """创建输入命令消息"""
    if isinstance(input_command, InputCommand):
        input_data = input_command.to_dict()
    else:
        input_data = input_command

    data = {
        'player_id': player_id,
        'frame_id': frame_id,
        'input': input_data
    }
    return Message(MSG_TYPE_INPUT, data)


def create_state_update_message(frame_id, state_frame):
    """创建状态更新消息"""
    if isinstance(state_frame, StateFrame):
        state_data = state_frame.to_dict()
    else:
        state_data = state_frame

    data = {
        'frame_id': frame_id,
        'state': state_data
    }
    return Message(MSG_TYPE_STATE_UPDATE, data)


def create_ping_message(client_id):
    """创建Ping消息"""
    data = {
        'client_id': client_id,
        'send_time': time.time()
    }
    return Message(MSG_TYPE_PING, data)


def create_pong_message(ping_data):
    """创建Pong回复消息"""
    data = ping_data.copy()
    data['reply_time'] = time.time()
    return Message(MSG_TYPE_PONG, data)


def create_error_message(error_code, error_message):
    """创建错误消息"""
    data = {
        'code': error_code,
        'message': error_message
    }
    return Message(MSG_TYPE_ERROR, data)


def create_player_ready_message(client_id, room_id, is_ready=True):
    """创建玩家准备消息"""
    data = {
        'client_id': client_id,
        'room_id': room_id,
        'is_ready': is_ready
    }
    return Message(MSG_TYPE_PLAYER_READY, data)


def create_room_info_message(room_id, room_info):
    """创建房间信息消息"""
    data = {
        'room_id': room_id,
        'info': room_info
    }
    return Message(MSG_TYPE_ROOM_INFO, data)


class NetworkLatencyEstimator:
    """
    网络延迟估计器：估计客户端和服务器之间的网络延迟

    主要功能：
    - 记录Ping-Pong往返时间
    - 计算平均延迟和抖动
    """

    def __init__(self, window_size=10):
        """初始化延迟估计器"""
        self.window_size = window_size  # 延迟历史窗口大小
        self.rtt_history = []  # 往返时间历史记录
        self.last_ping_time = 0  # 最后一次Ping的时间

    def send_ping(self):
        """记录发送Ping的时间"""
        self.last_ping_time = time.time()
        return self.last_ping_time

    def receive_pong(self, ping_time=None):
        """
        处理接收到Pong的事件

        Args:
            ping_time: Pong消息中的发送时间，若为None则使用last_ping_time

        Returns:
            当前的往返时间(RTT)
        """
        if ping_time is None:
            ping_time = self.last_ping_time

        if ping_time == 0:
            return 0

        current_time = time.time()
        rtt = (current_time - ping_time) * 1000  # 转换为毫秒

        # 更新RTT历史
        self.rtt_history.append(rtt)
        while len(self.rtt_history) > self.window_size:
            self.rtt_history.pop(0)

        return rtt

    def get_average_rtt(self):
        """获取平均往返时间"""
        if not self.rtt_history:
            return 0
        return sum(self.rtt_history) / len(self.rtt_history)

    def get_rtt_variance(self):
        """获取往返时间的方差（网络抖动）"""
        if not self.rtt_history or len(self.rtt_history) < 2:
            return 0

        avg = self.get_average_rtt()
        variance = sum((x - avg) ** 2 for x in self.rtt_history) / len(self.rtt_history)
        return variance

    def estimate_one_way_delay(self):
        """估计单向延迟（假设上行和下行对称）"""
        return self.get_average_rtt() / 2

    def __str__(self):
        """字符串表示"""
        return (f"LatencyEstimator(avg_rtt={self.get_average_rtt():.2f}ms, "
                f"variance={self.get_rtt_variance():.2f})")