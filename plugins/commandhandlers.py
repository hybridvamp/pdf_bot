from tools.general import _task_checker  # pylint:disable=import-error
from pyrogram import filters
from pdfbot import Pdfbot  # pylint:disable=import-error
from PIL import Image
from tools import (
    MakePdf,
    Merge,
    Encrypter,
    Decypter,
    Extractor,
)  # pylint:disable=import-error
from pyrogram.types import (
    Message,
    CallbackQuery,
    KeyboardButton,
    InputMediaPhoto,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from plugins.logger import LOG_  # pylint:disable=import-error
import asyncio


async def rotate_image(file_path: str, degree: int) -> str:
    """rotate images from input file_path and degree"""
    origin: Image = Image.open(file_path)
    rotated_image = origin.rotate(degree, expand=True)
    await asyncio.sleep(0.001)
    rotated_image.save(file_path)
    LOG_.debug(f"Image rotated and saved to --> {file_path}")
    return file_path


@Pdfbot.on_message(filters.command(["extract"]) & filters.create(_task_checker))
async def extract_handler(client: Pdfbot, message: Message) -> None:
    new_task = Extractor(
        client, message.chat.id, message.message_id, " ".join(message.command[1:])
    )
    client.task_pool.add_task(message.chat.id, new_task)
    if not await new_task.parse_input():
        return
    status = await message.reply_text("**downloading...**")
    await new_task.allocate_and_download(message.reply_to_message)
    await status.edit(
        "**processing...**",
    )
    client.process_pool.new_task(new_task)
    while new_task.status == 0:
        await asyncio.sleep(1.2)
    else:
        if new_task.status == 2:
            await message.reply_text(f"**Task failed: `{new_task.error_code}`**")
        elif new_task.status == 1:
            await message.reply_document(new_task.output)
            new_task.__del__()
    client.task_pool.remove_task(message.chat.id)


@Pdfbot.on_message(
    filters.command(["encrypt", "decrypt"]) & filters.create(_task_checker)
)
async def encrypt_handler(client: Pdfbot, message: Message) -> None:
    if message.reply_to_message is None or (
        message.document and message.document.mime_type != "document/pdf"
    ):
        await message.reply("Please reply to a PDF file")
        return
    if len(message.command) < 1:
        await message.reply(
            f"**usage:** {'/encrypt' if message.command[0] == 'encrypt' else '/decrypt'} password`"
        )
        return
    new_task = (Encrypter if message.command[0] == "encrypt" else Decypter)(
        message.chat.id, message.message_id, " ".join(message.command[1:])
    )
    client.task_pool.add_task(message.chat.id, new_task)
    status = await message.reply_text("**downloading...**")
    await new_task.allocate_and_download(message.reply_to_message)
    await status.edit(
        "**processing...**",
    )
    client.process_pool.new_task(new_task)
    while new_task.status == 0:
        await asyncio.sleep(1.2)
    else:
        if new_task.status == 2:
            await message.reply_text(f"**Task failed: `{new_task.error_code}`**")
        elif new_task.status == 1:
            await message.reply_document(new_task.output)
            new_task.__del__()
    client.task_pool.remove_task(message.chat.id)


@Pdfbot.on_message(filters.command(["merge", "make"]) & filters.create(_task_checker))
async def merge(client: Pdfbot, message: Message):
    is_merge = "merge" in message.command[0]
    await message.reply_text(
        f"Now send me the {'pdf files' if is_merge else 'photos'}",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton("Done"), KeyboardButton("Cancel")]],
            resize_keyboard=True,
        ),
    )
    new_task = (Merge if is_merge else MakePdf)(message.chat.id, message.message_id)
    client.task_pool.add_task(message.chat.id, new_task)
    await asyncio.gather(
        new_task.file_allocator(),
        new_task.add_handlers(client),
    )
    if len(message.command) > 1:
        for commands in message.command[1:]:
            if commands.startswith("-"):
                if commands == "-q" or commands == "-quiet":
                    new_task.quiet = True
                elif commands == "-d" or commands == "-direct":
                    new_task.direct = True
            else:
                filename = commands
                if len(filename) > 64:
                    await message.reply_text(
                        "**WARNING:** file name too long, reducing..."
                    )
                    filename = filename[:64]
                if filename.endswith(".PDF") or filename.endswith(".pdf"):
                    filename = filename.replace(".PDF", "")
                    filename = filename.replace(".pdf", "")
                new_task.output = filename


@Pdfbot.on_callback_query()
async def callback_handler(client: Pdfbot, callback: CallbackQuery):
    message: Message = callback.message
    current_task = client.task_pool.get_task(message.chat.id)
    if callback.data == "help_button":
        await message.edit("")
    elif current_task is None:
        await asyncio.gather(
            callback.answer("cancelled/timed-out"),
            message.delete(),
        )
    elif (
        "rotate" in callback.data
        or "insert" in callback.data
        or "remove" in callback.data
    ):
        file_id = int(callback.data.split(":", 1)[0])
        file_path = current_task.temp_files.get(file_id)
        if file_path is None:
            await asyncio.gather(
                callback.answer("cancelled/timed-out"),
                message.delete(),
            )
        elif "rotate" in callback.data:
            await callback.answer("rotating please wait")
            degree = int(callback.data.split(":", 2)[2])
            temporary_image = await rotate_image(file_path, degree)
            await message.edit_media(
                InputMediaPhoto(temporary_image), reply_markup=message.reply_markup
            )
        elif "insert" in callback.data:
            if file_path is not None:
                current_task.temp_files.pop(file_id)
                current_task.proposed_files.append(file_path)
                await asyncio.gather(
                    message.delete(),
                    (
                        message.reply_text("photo added successfully")
                        if not current_task.quiet
                        else asyncio.sleep(0)
                    ),
                )
                LOG_.debug("image added to proposal queue")
        elif "remove" in callback.data:
            current_task.temp_files.pop(file_id)
            await message.delete()
            LOG_.debug("image removed from temporary queue")

    elif callback.data == "rm_task":
        client.task_pool.remove_task(message.chat.id)
        await asyncio.gather(
            message.reply_text(
                "**Task** cancelled", reply_markup=ReplyKeyboardRemove()
            ),
            message.delete(),
        )

    elif callback.data == "del":
        await message.delete()
