# client/network/protocol.py
"""
通信协议模块：定义客户端和服务器通信协议
"""

import json
import struct
from common.serialization import serialize_object, deserialize_object


class NetworkProtocol:
    """
    网络协议：处理消息的序列化和反序列化
    """

    @staticmethod
    def pack_message(message):
        """
        打包消息为二进制格式

        Args:
            message: 要打包的消息（字典）

        Returns:
            打包后的二进制数据
        """
        # 序列化消息到JSON
        msg_json = json.dumps(message)
        msg_bytes = msg_json.encode('utf-8')

        # 添加长度前缀（4字节网络字节序）
        msg_len = len(msg_bytes)
        prefix = struct.pack('!I', msg_len)

        return prefix + msg_bytes

    @staticmethod
    def unpack_message(data):
        """
        解包二进制数据为消息

        Args:
            data: 二进制数据

        Returns:
            解包后的消息（字典）
        """
        # 解析消息长度
        msg_len = struct.unpack('!I', data[:4])[0]

        # 解析消息内容
        msg_data = data[4:4 + msg_len].decode('utf-8')
        return json.loads(msg_data)

    @staticmethod
    def create_connect_message(client_id):
        """创建连接消息"""
        return {
            'type': 'connect',
            'client_id': client_id
        }

    @staticmethod
    def create_disconnect_message(client_id):
        """创建断开连接消息"""
        return {
            'type': 'disconnect',
            'client_id': client_id
        }

    @staticmethod
    def create_input_frame_message(client_id, frame_number, input_data):
        """创建输入帧消息"""
        return {
            'type': 'input_frame',
            'client_id': client_id,
            'frame': frame_number,
            'input': input_data,
            'timestamp': int(time.time() * 1000)
        }

    @staticmethod
    def create_state_sync_request_message(client_id, frame_number):
        """创建状态同步请求消息"""
        return {
            'type': 'request_state_sync',
            'client_id': client_id,
            'frame': frame_number,
            'timestamp': int(time.time() * 1000)
        }