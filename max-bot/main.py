import asyncio
from telethon_max import TelegramClient, events, Button, _conv_callback
from os import getenv
from fastapi import FastAPI
from uvicorn import Config, Server

client = TelegramClient()
app = FastAPI()

@app.post("/send")
async def send_message(user_id: int, text: str) -> None:
    await client.send_message(user_id, text)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    event = _conv_callback(event)
    user_id = event.query.user_id
    if event.data == b"GETID":
        await client.send_message(user_id, f"ID: {user_id}")
    await event.answer()

@client.on(events.NewMessage)
async def message_handler(event):
    user_id = event.peer_id.user_id
    await client.send_message(user_id, "Меню", buttons=[
        [Button.web_app("Запустить приложение", "id2465373383_1_bot")],
        [Button.inline("Узнать ID", b"GETID")]
    ])

async def main():
    server = Server(Config(app=app, host="0.0.0.0", port=80, loop="asyncio", log_level="info"))
    asyncio.create_task(server.serve())
    await client.start(bot_token=getenv("MAX_BOT_TOKEN"))
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
