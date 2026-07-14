import asyncio
import json
import websockets


async def test():

    uri = "ws://127.0.0.1:8000/ws"

    try:

        async with websockets.connect(uri) as websocket:

            print("✅ Connected to server")

            sample = {
                "event_id": "evt-001",
                "session_id": "ABC123",
                "event_type": "WEBSITE_OPENED",
                "timestamp": "2026-07-14T00:00:00Z",
                "source_app": "chrome_extension",
                "payload": {
                    "url": "https://fake-scholarship.xyz",
                    "title": "Scholarship Portal",
                    "text": "Pay ₹500 registration fee"
                }
            }

            await websocket.send(json.dumps(sample))

            print("✅ JSON Sent")

            response = await websocket.recv()

            print("Server Response:", response)

    except Exception as e:

        print(type(e).__name__)
        print(e)


asyncio.run(test())