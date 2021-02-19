# (c) AlenPaulVarghese
# -*- coding: utf-8 -*-

from tools.scaffold import PdfTask2
from plugins.logger import LOG_  # pylint:disable=import-error
import asyncio


class Encrypter(PdfTask2):
    def __init__(self, chat_id: int, message_id: int, password: str):
        super().__init__(chat_id, message_id)
        self.user_input = password

    async def process(self):
        pdf_check = await asyncio.create_subprocess_shell(
            f"qpdf --is-encrypted {self.input_file}"
        )
        if await pdf_check.wait() == 0:
            raise Exception("The given file is already encrypted")
        self.output = self.cwd + self.output + ".pdf"
        cmd = [
            "qpdf",
            "--encrypt",
            f"'{self.user_input}'",
            f"'{self.user_input}'",
            "128",
            "--",
            f"{self.input_file}",
            f"{self.output}",
        ]
        LOG_.debug("exec: {}".format(" ".join(cmd)))
        proc = await asyncio.create_subprocess_shell(
            " ".join(cmd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if stderr:
            raise Exception(stderr.decode("utf-8"))
