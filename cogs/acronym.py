from discord_http import (
    commands, Context, View, ActionRow, Button, ButtonStyles,
    Modal, TextInputComponent, TextStyles,
)

from textwrap import dedent

from utilities.data import CustomClient


def _reveal_content(data: dict) -> str:
    return dedent(f"""\
    **✍🏼 Acronym**: {data["suggested_acronym"]}
    **📔 Series Name**: {data["title"]}
    **🔗 Series Amazon Link**: {data["url"]}
    **🔢 Book Count**: {data["book_count"]}
    **☑️ Completed?**: {data["completed_status"]}
    """)


def _decided_view(key: str) -> View:
    """Same buttons as the original suggestion message, disabled after a decision."""
    return View(ActionRow(
        Button(label="Approve", style=ButtonStyles.success,
               custom_id=f"sugg:appr:{key}", disabled=True),
        Button(label="Deny", style=ButtonStyles.danger,
               custom_id=f"sugg:deny:{key}", disabled=True),
    ))


class RevealAcronym(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot: CustomClient = bot

    @commands.command(name="reveal", description="Reveal an acronym by typing it here.")
    async def reveal_acronym(self, ctx: Context, acronym: str):
        """Finds and displays what a series acronym is for a user."""
        async def call_after():
            data = self.bot.acronyms.get(acronym)

            if data is None:
                await ctx.edit_original_response(content=f"No acronym data found for `{acronym}`")
                return

            await ctx.edit_original_response(content=_reveal_content(data))

        return ctx.response.defer(thinking=True, call_after=call_after, ephemeral=True)

    @commands.command(name="suggest", description="Suggest a new acronym")
    async def suggest_acronym(self, ctx: Context, acronym: str, series_title: str, amazon_series_page: str):
        async def call_after():
            if not amazon_series_page.startswith("https://"):
                await ctx.edit_original_response(content="Please provide a valid `https://` link for the series.")
                return

            status = self.bot.acronyms.add_suggestion(
                acronym=acronym,
                title=series_title,
                url=amazon_series_page,
                suggested_by=ctx.user.id,
            )

            if status == "duplicate_acronym":
                await ctx.edit_original_response(content=f"`{acronym}` already exists.")
                return
            if status == "duplicate_suggestion":
                await ctx.edit_original_response(content=f"`{acronym}` has already been suggested and is pending review.")
                return

            await ctx.edit_original_response(content="Your suggestion has been successfully sent to the developer!")

            key = acronym.strip().lower()
            view = View(ActionRow(
                Button(label="Approve", style=ButtonStyles.success,
                       custom_id=f"sugg:appr:{key}"),
                Button(label="Deny", style=ButtonStyles.danger,
                       custom_id=f"sugg:deny:{key}"),
            ))

            # Suggestions are approved/denied manually via buttons
            owner = await self.bot.fetch_user(int(self.bot.config.discord_owner_id))
            await owner.send(
                content=dedent(f"""\
                ## A new suggestion from {ctx.user.mention} (`{ctx.user.id}`)
                **✍🏼 Acronym**: {acronym}
                **📔 Series Name**: {series_title}
                **🔗 Series Amazon Link**: {amazon_series_page}
                """),
                view=view,
            )

        return ctx.response.defer(thinking=True, call_after=call_after, ephemeral=True)

    @commands.interaction("sugg:appr:", regex=True)
    async def on_approve_button(self, ctx: Context):
        """Opens a pre-filled modal to finalize the acronym data before approving."""
        key = (ctx.custom_id or "").removeprefix("sugg:appr:")
        suggestion = self.bot.acronyms.get_suggestion(key)

        if suggestion is None:
            return ctx.response.send_message("This suggestion no longer exists.", ephemeral=True)

        modal = Modal(title=f"Approve '{key}'",
                      custom_id=f"sugg:apprmodal:{key}")
        modal.add_item(TextInputComponent(
            custom_id="acronym", default=key.upper(), max_length=20
        ), label="Acronym")
        modal.add_item(TextInputComponent(
            custom_id="title", default=suggestion["title"], max_length=200
        ), label="Series Title")
        modal.add_item(TextInputComponent(
            custom_id="url", default=suggestion["url"], max_length=300
        ), label="Amazon Link")
        modal.add_item(TextInputComponent(
            custom_id="book_count", default="", max_length=5
        ), label="Book Count")
        modal.add_item(TextInputComponent(
            custom_id="completed_status", default="No", max_length=10
        ), label="Completed? (Yes/No)")

        return ctx.response.send_modal(modal)

    @commands.interaction("sugg:deny:", regex=True)
    async def on_deny_button(self, ctx: Context):
        """Opens a modal to collect a denial reason before rejecting."""
        key = (ctx.custom_id or "").removeprefix("sugg:deny:")
        suggestion = self.bot.acronyms.get_suggestion(key)

        if suggestion is None:
            return ctx.response.send_message("This suggestion no longer exists.", ephemeral=True)

        modal = Modal(title=f"Deny '{key}'", custom_id=f"sugg:denymodal:{key}")
        modal.add_item(TextInputComponent(
            custom_id="reason", style=TextStyles.paragraph, required=False, max_length=500
        ), label="Reason (optional, sent to the user)")

        return ctx.response.send_modal(modal)

    @commands.interaction("sugg:apprmodal:", regex=True)
    async def on_approve_modal_submit(self, ctx: Context):
        """Finalizes the suggestion into acronyms.json and notifies the suggester."""
        key = (ctx.custom_id or "").removeprefix("sugg:apprmodal:")
        suggestion = self.bot.acronyms.get_suggestion(key)

        if suggestion is None:
            return ctx.response.edit_message(content="This suggestion no longer exists.", view=None)

        book_count_raw = str(ctx.modal_values.get("book_count", ""))
        entry = {
            "suggested_acronym": str(ctx.modal_values.get("acronym", key.upper())),
            "title": str(ctx.modal_values.get("title", suggestion["title"])),
            "url": str(ctx.modal_values.get("url", suggestion["url"])),
            "book_count": int(book_count_raw) if book_count_raw.isdigit() else 0,
            "completed_status": str(ctx.modal_values.get("completed_status", "No")),
        }

        self.bot.acronyms.upsert_acronym(key, entry)
        self.bot.acronyms.remove_suggestion(key)

        async def notify_suggester():
            suggester = await self.bot.fetch_user(int(suggestion["suggested_by"]))
            await suggester.send(
                content=f"✅ Your suggestion for `{key}` was approved! Thank you so much! See the full entry below:\n\n{_reveal_content(entry)}"
            )

        original_content = ctx.message.content if ctx.message else ""
        return ctx.response.edit_message(
            content=f"{original_content}\n\n✅ Suggestion Approved",
            view=_decided_view(key),
            call_after=notify_suggester,
        )

    @commands.interaction("sugg:denymodal:", regex=True)
    async def on_deny_modal_submit(self, ctx: Context):
        """Removes the suggestion and notifies the suggester with the denial reason."""
        key = (ctx.custom_id or "").removeprefix("sugg:denymodal:")
        suggestion = self.bot.acronyms.get_suggestion(key)

        if suggestion is None:
            return ctx.response.edit_message(content="This suggestion no longer exists.", view=None)

        reason = str(ctx.modal_values.get("reason") or "No reason provided.")
        self.bot.acronyms.remove_suggestion(key)

        async def notify_suggester():
            suggester = await self.bot.fetch_user(int(suggestion["suggested_by"]))
            await suggester.send(
                content=f"❌ Your suggestion for `{key}` was denied.\n**Reason**: {reason}"
            )

        original_content = ctx.message.content if ctx.message else ""
        return ctx.response.edit_message(
            content=f"{original_content}\n\n❌ Suggestion Denied",
            view=_decided_view(key),
            call_after=notify_suggester,
        )


async def setup(bot: CustomClient):
    await bot.add_cog(RevealAcronym(bot))
    print("Loaded cog: acronym")
