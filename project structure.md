project/
├── client/
│   ├── main.py                    # 客户端入口
│   ├── game_engine/               # 游戏引擎组件
│   │   ├── tank.py               # 坦克类
│   │   ├── bullet.py             # 子弹类
│   │   ├── obstacle.py           # 障碍物类
│   │   ├── map.py                # 地图类
│   │   └── collision.py          # 碰撞系统
│   ├── network/
│   │   ├── client.py             # 网络客户端
│   │   └── protocol.py           # 通信协议
│   ├── frame_sync/               # 帧同步相关组件
│   │   ├── input_manager.py      # 输入管理
│   │   ├── frame_executor.py     # 帧执行
│   │   └── state_synchronizer.py # 状态同步
│   ├── ui/                       # 用户界面
│   │   ├── menu.py               # 游戏菜单
│   │   └── hud.py                # 游戏UI
│   └── resources/                # 资源文件
│
├── server/
│   ├── main.py                    # 服务器入口
│   ├── room.py                    # 房间管理
│   ├── session.py                 # 会话管理
│   ├── frame_sync/                # 服务器帧同步组件
│   │   ├── frame_manager.py      # 帧管理
│   │   └── validator.py          # 验证器
│   ├── network/
│   │   ├── server.py             # 网络服务器
│   │   └── protocol.py           # 通信协议
│   └── ai/                       # AI组件
│       ├── tank_ai.py            # 坦克AI
│       └── pathfinding.py        # 寻路算法
│
└── common/
    ├── constants.py               # 常量定义
    ├── utils.py                   # 工具函数
    ├── events.py                  # 事件定义
    ├── serialization.py           # 数据序列化
    ├── frame_data.py              # 帧数据结构
    └── deterministic_engine.py    # 确定性引擎