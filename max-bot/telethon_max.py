import aiomax
import aiohttp
import asyncio
import types
from os import getenv

events = types.ModuleType("bot_client.events")
events.CallbackQuery = "on_button_callback"
events.NewMessage = "on_message"

_mime_type_by_extension = {
    "zip": "application/zip",
    "pdf": "application/pdf",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xml": "application/xml",
    "csv": "text/csv",
    "txt": "text/plain",
    "mp4": "video/mp4",
    "mp3": "audio/mpeg"
}

async def _async_none_fn():
    return None

def _conv_document(document):
    if type(document) is aiomax.PhotoAttachment:
        filename, mime_type = "photo.jpg", "image/jpeg"
    elif type(document) is aiomax.VideoAttachment:
        filename, mime_type = "video.mp4", "video/mp4"
    elif type(document) is aiomax.AudioAttachment:
        filename, mime_type = "audio.mp3", "audio/mpeg"
    elif type(document) is aiomax.FileAttachment:
        filename, mime_type = document.filename, _mime_type_by_extension[document.filename.rsplit('.', 1)[-1]]
    else:
        filename, mime_type = None, None
    return types.SimpleNamespace(
        url=getattr(document, "url", None),
        filename=filename,
        mime_type=mime_type
    )

def _conv_message(event):
    def get_phone(vcf):
        idx = vcf.find("TEL;TYPE=cell:")
        if idx == -1: return None
        idx += 14
        return "+" + vcf[idx:vcf.find("\r\n", idx)]

    async def get_reply_message():
        if event.link is None or event.link.type != "reply":
            return None
        return types.SimpleNamespace(
            id = event.link.message.message_id,
            peer_id = types.SimpleNamespace(
                user_id = event.link.sender.user_id
            ),
            text = event.link.message.text,
            sender = event.link.sender,
            contact = types.SimpleNamespace(
                phone_number = get_phone(event.link.message.attachments[0].vcf_info)
            ) if len(event.link.message.attachments) > 0 and type(event.link.message.attachments[0]) is aiomax.ContactAttachment else None,
            document = _conv_document(event.link.message.attachments[0]) if len(event.link.message.attachments) > 0 else None,
            get_reply_message = _async_none_fn
        )
    return types.SimpleNamespace(
        id = event.id,
        peer_id = types.SimpleNamespace(
            user_id = event.sender.user_id
        ),
        text = event.body.text,
        sender = event.sender,
        contact = types.SimpleNamespace(
            phone_number = get_phone(event.body.attachments[0].vcf_info)
        ) if len(event.body.attachments) > 0 and type(event.body.attachments[0]) is aiomax.ContactAttachment else None,
        document = _conv_document(event.body.attachments[0]) if len(event.body.attachments) > 0 else None,
        get_reply_message = get_reply_message
    )

def _conv_callback(event):
    async def answer():
        pass
    return types.SimpleNamespace(
        query = types.SimpleNamespace(
            user_id = event.user.user_id
        ),
        data = event.payload.encode(),
        answer = answer
    )

class Button:
    @staticmethod
    def inline(text: str, payload: str | bytes):
        if type(payload) == bytes:
            payload = payload.decode()
        return aiomax.buttons.CallbackButton(text, payload)

    @staticmethod
    def request_phone(text: str):
        return aiomax.buttons.ContactButton(text)

    @staticmethod
    def url(text: str, url: str):
        return aiomax.buttons.LinkButton(text, url)

    @staticmethod
    def web_app(text: str, bot: str):
        return aiomax.buttons.WebAppButton(text, bot)

    @staticmethod
    def clear():
        return None

class TelegramClient:
    def __init__(self, *args, **kwargs):
        self.bot = aiomax.Bot(getenv("MAX_BOT_TOKEN"), use_certificate=True)

    async def start(self, bot_token):
        await self.bot.start_polling()

    def on(self, decorator):
        if decorator == "on_message":
            def foo(f):
                @self.bot.on_message()
                def on_msg(msg):
                    return f(_conv_message(msg))
                @self.bot.on_bot_start()
                def on_start(event):
                    return f(types.SimpleNamespace(
                        peer_id = types.SimpleNamespace(
                            user_id = event.user.user_id
                        ),
                        text = "/start " + event.payload if event.payload is not None else "/start",
                        sender = event.user,
                        contact = None,
                        document = None,
                        get_reply_message = _async_none_fn
                    ))
                return f
            return foo
        return getattr(self.bot, decorator)()

    async def send_message(self, user_id, message, parse_mode=None, buttons=None):
        return await self.bot.send_message(text=message, user_id=user_id, keyboard=buttons, format=parse_mode)

    async def send_file(self, user_id, file, caption=None, buttons=None, parse_mode=None):
        async def check_attachment(attachment):
            if hasattr(attachment, "_TelegramClient__uploaded_easymark"):
                return attachment
            filename = getattr(attachment, "filename", None)
            if type(attachment) is aiomax.VideoAttachment:
                filename = "video.mp4"
            async with aiohttp.ClientSession() as http:
                async with http.get(attachment.url) as resp:
                    content = await resp.read()
            return await self.upload_file(content, filename)
        if type(file) is list:
            for i in range(len(file)):
                file[i] = await check_attachment(file[i])
        elif file is not None:
            file = await check_attachment(file)
        return await self.bot.send_message(text=caption, user_id=user_id, keyboard=buttons, format=parse_mode, attachments=file)

    async def edit_message(self, user_id, msg_id, text=None, buttons=None, parse_mode=None):
        await self.bot.edit_message(msg_id, text=text, format=parse_mode, notify=False, keyboard=buttons)

    async def _upload_file(self, file, file_name=None):
        if type(file) == str and file.endswith(".mp4"):
            return await self.bot.upload_video(file)
        return await self.bot.upload_file(file, filename=file_name)

    async def upload_file(self, file, file_name=None):
        file = await self._upload_file(file, file_name)
        file.__uploaded_easymark = True
        return file

    async def download_file(self, file):
        async with aiohttp.ClientSession() as http:
            async with http.get(file.url) as resp:
                return await resp.read()

    async def get_messages(self, chat_id, ids):
        return _conv_message(await self.bot.get_message(str(ids)))

    async def run_until_disconnected(self):
        await self.bot.start_polling(aiohttp.ClientSession())