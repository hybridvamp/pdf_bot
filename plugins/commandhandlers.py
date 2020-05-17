from pyrogram import Client,Filters,InlineKeyboardButton,InlineKeyboardMarkup
from plugins.tools_bundle import pdf_silcer
import asyncio
import os 

@Client.on_message(Filters.command(["start"]))
async def start(client,message):
    await client.send_message(
        chat_id=message.chat.id,
        text=f'{message.chat.id}',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(text='decrypt',callback_data='decrypter')]
        ])
    )



@Client.on_message(Filters.document)
async def downloader(client,message):
    if message.document.mime_type == "application/pdf":
        #Download and storing file
        location = "./FILES" + "/" + str(message.chat.id)
        imgdir =  location + "/" + "input.pdf"
        if not os.path.isdir(location):
            os.mkdir(location)
        dwn = await message.reply_text("Downloading...", quote=True)
        await client.download_media(
            message=message,
            file_name=imgdir
        )
        await dwn.edit(
        text='Choose any options',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(text='Compress',callback_data=f'compress|{imgdir}')],
            [InlineKeyboardButton(text='Split and Merge',callback_data=f's&m|{imgdir}')],
            [InlineKeyboardButton(text='PDF Protections',callback_data=f'pass|{imgdir}')]
            
        ])
    )
    else:
        await message.reply(text='Oops This is not a pdf')


@Client.on_callback_query()
async def cb_(client,callback_query):
    cb_data = callback_query.data.split('|')[0]
    imgdir = callback_query.data.split('|')[1]
    msg = callback_query.message
    if cb_data == 's&m':
        await msg.edit(
            text='Please Choose',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text='Split PDF',callback_data=f'slicer|{imgdir}')],
                [InlineKeyboardButton(text='Merge PDF',callback_data=f'merger|{imgdir}')]
            ])
        )
        
    elif cb_data == 'pass':
        await msg.edit(
            text='Please Choose',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text='encrypt',callback_data=f'encrypter|{imgdir}')],
                [InlineKeyboardButton(text='decrypt',callback_data=f'decrypter|{imgdir}')]
            ])
        )

    elif cb_data == 'compress':
        await msg.edit(
            text='Please Select Compresssion Ratio',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text='low',callback_data=f'low|{imgdir}')],
                [InlineKeyboardButton(text='recommended',callback_data=f'medium|{imgdir}')],
                [InlineKeyboardButton(text='high',callback_data=f'high|{imgdir}')]
            ])
        )
    elif cb_data == 'slicer':
        await msg.edit(
            text='working'
        )
        print(callback_query.message.chat.id)
        #print(callback_query)
        await pdf_silcer(imgdir, int(callback_query.message.chat.id), client)
        await msg.delete()