import discord_http
import os

from utilities.config import Config
from utilities.acronymStorage import AcronymStore


class CustomClient(discord_http.Client):
    def __init__(self, config: Config, *args, **kwargs):
        # Keep app config on the subclass and pass client settings to the base class.
        self.config = config
        self.acronyms = AcronymStore()

        kwargs.setdefault("token", config.discord_token)
        kwargs.setdefault("sync", config.discord_sync.lower() == "true")

        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        for file in os.listdir("cogs"):
            if not file.endswith(".py"):
                continue  # Skip non-python files

            await self.load_extension(f"cogs.{file[:-3]}")
