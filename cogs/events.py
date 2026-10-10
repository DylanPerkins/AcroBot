import re

from discord_http import commands, Message
from discord_http.cooldowns import Cooldown

from cogs.acronym import _reveal_content
from utilities.data import CustomClient

_TEMPLATE_KEY = "template"  # Not a real acronym, just the JSON schema entry
_WORD_RE = re.compile(r"[A-Za-z0-9']+")

_COOLDOWN_RATE = 1      # 1 reply...
_COOLDOWN_PER = 45 * 60    # ...per 45 minutes, per channel


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot: CustomClient = bot
        self._cooldowns: dict[tuple[int, str], Cooldown] = {}

    def _max_acronym_length(self) -> int:
        """Longest known acronym key, recomputed since acronyms.json can change at runtime."""
        return max(
            (len(key) for key in self.bot.acronyms.keys() if key != _TEMPLATE_KEY),
            default=0,
        )

    def _on_cooldown(self, channel_id: int, key: str) -> bool:
        """Caps replies per acronym per channel, so one acronym can't gate others."""
        bucket = self._cooldowns.setdefault(
            (channel_id, key), Cooldown(_COOLDOWN_RATE, _COOLDOWN_PER)
        )
        return bucket.update_rate_limit() is not None

    @commands.listener()
    async def on_message_create(self, message: Message):
        """Parses new messages word by word, looking for known acronyms."""
        if message.author.bot:
            return  # Ignore all bots

        content = message.content
        if not content:
            return

        max_length = self._max_acronym_length()
        matched: dict[str, dict] = {}

        for word in _WORD_RE.findall(content):
            if len(word) > max_length:
                continue  # Too long to be a known acronym, skip early

            key = word.lower()
            if key == _TEMPLATE_KEY or key in matched:
                continue

            data = self.bot.acronyms.get(key)
            if data is not None:
                matched[key] = data

        if not matched:
            return

        ready = {
            key: data for key, data in matched.items()
            if not self._on_cooldown(message.channel_id, key)
        }
        if not ready:
            return

        reply_content = "\n".join(
            _reveal_content(data) for data in ready.values()
        )
        await message.reply(content=reply_content)


async def setup(bot: CustomClient):
    await bot.add_cog(Events(bot))
    print("Loaded cog: events")
