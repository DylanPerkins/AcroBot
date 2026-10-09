from discord_http import CheckFailed, Context

import discord_http


def is_in_dm(ctx: "Context") -> bool:
    """Checks if the context is in a DM channel."""
    return isinstance(ctx.channel, discord_http.DMChannel)


def is_owner(ctx: Context):
    """Check if the user is the owner of the bot."""
    if str(ctx.user.id) != str(ctx.bot.config.discord_owner_id):
        raise CheckFailed("You are not the owner of the bot.")

    return True


def is_administrator(ctx: Context):
    if not ctx.user.guild_permissions.administrator:
        raise CheckFailed("You do not have administrator permissions.")

    return True


def is_capable(ctx: Context):
    """Check if the user is capable of using this command."""
    output = False

    if isinstance(ctx.channel, discord_http.DMChannel):
        output = False
    if ctx.user.guild_permissions.administrator:
        output = True
    if str(ctx.user.id) == str(ctx.bot.config.discord_owner_id):
        output = True

    if not output:
        raise CheckFailed("You do not have the required permissions to use this command.")

    return output
