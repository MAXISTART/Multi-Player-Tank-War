import asyncio
import websockets
import json
import sys

# 定义一个统一的端口
PORT = 8766


async def test_server():
    print("Testing WebSocket server...")
    try:
        uri = f"ws://localhost:{PORT}"
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("Connected to server!")

            # 等待服务器的welcome消息
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            print(f"Received from server: {data}")

            # 发送一个测试消息
            test_msg = {"type": "test", "message": "Hello Server!"}
            await websocket.send(json.dumps(test_msg))
            print(f"Sent test message: {test_msg}")

            # 等待1秒后退出
            await asyncio.sleep(1)
            print("Test completed successfully!")
            return True
    except Exception as e:
        print(f"Test failed: {e}")
        return False


async def test_client():
    print("Testing as WebSocket server...")
    try:
        # 创建一个简单的echo服务器
        async def echo(websocket, path):
            print("Client connected!")
            await websocket.send(json.dumps({"type": "welcome", "message": "Hello Client!"}))
            async for message in websocket:
                print(f"Received: {message}")
                await websocket.send(message)

        # 启动服务器
        server = await websockets.serve(echo, "localhost", PORT)
        print(f"Echo server running on port {PORT}")

        # 等待10秒后退出
        await asyncio.sleep(10)
        server.close()
        await server.wait_closed()
        print("Echo server stopped")
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        return False


async def main():
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        await test_client()
    else:
        await test_server()


if __name__ == "__main__":
    asyncio.run(main())