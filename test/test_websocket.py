# test_both.py
import asyncio
import websockets
import json


async def server_handler(websocket, path):
    print("[Test] Client connected!")
    await websocket.send(json.dumps({"type": "welcome", "message": "Hello!"}))
    async for message in websocket:
        print(f"[Test] Server received: {message}")
        await websocket.send(json.dumps({"type": "echo", "content": json.loads(message)}))


async def client():
    await asyncio.sleep(0.5)  # 确保服务器有时间启动
    try:
        uri = "ws://localhost:8765"
        print(f"[Test] Client connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("[Test] Client connected!")

            # 接收welcome消息
            response = await websocket.recv()
            print(f"[Test] Client received: {response}")

            # 发送测试消息
            test_msg = json.dumps({"type": "test", "message": "Hello Server!"})
            await websocket.send(test_msg)
            print(f"[Test] Client sent: {test_msg}")

            # 接收回应
            response = await websocket.recv()
            print(f"[Test] Client received response: {response}")

            await asyncio.sleep(1)
            print("[Test] Client done")
    except Exception as e:
        print(f"[Test] Client error: {e}")


async def main():
    # 启动服务器
    server = await websockets.serve(server_handler, "localhost", 8765)
    print("[Test] Server started on localhost:8765")

    # 启动客户端
    client_task = asyncio.create_task(client())

    # 等待客户端完成
    await client_task

    # 关闭服务器
    server.close()
    await server.wait_closed()
    print("[Test] Test completed")


if __name__ == "__main__":
    asyncio.run(main())