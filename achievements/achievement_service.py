import logging
from dataclasses import dataclass, field

import discord
from asgiref.sync import sync_to_async

from bd_models.models import BallInstance

from . import ui
from .models import Achievement, AchievementCompletion

log = logging.getLogger("ballsdex.packages.achievements")


@dataclass
class PlayerStats:
    total: int = 0
    owned_ball_ids: set = field(default_factory=set)

    @property
    def unique(self):
        return len(self.owned_ball_ids)


async def get_currency_name():
    """Return the currency name configured in BallsDex settings."""
    try:
        from django.apps import apps

        for model in apps.get_models():
            field_names = {f.name for f in model._meta.get_fields()}
            if "currency_name" not in field_names:
                continue
            settings = await sync_to_async(model.objects.first)()
            if settings:
                name = getattr(settings, "currency_name", None)
                if name:
                    return str(name)
    except Exception:
        log.debug("Could not read the currency name, using the default", exc_info=True)
    return "currency"


async def load_stats(discord_id):
    owned = BallInstance.objects.filter(player__discord_id=discord_id)
    total = await owned.acount()
    ball_ids = {
        ball_id
        async for ball_id in owned.order_by().values_list("ball_id", flat=True).distinct()
    }
    return PlayerStats(total=total, owned_ball_ids=ball_ids)


def get_progress(achievement, stats):
    """Return (current, target), or None if the achievement can't be completed automatically."""
    kind = achievement.requirement_type
    target = max(achievement.requirement_amount, 1)

    if kind == Achievement.CATCH_BALLS:
        return min(stats.total, target), target

    if kind == Achievement.UNIQUE_BALLS:
        return min(stats.unique, target), target

    if kind == Achievement.SPECIFIC_BALLS:
        required = {ball.pk for ball in achievement.required_balls.all()}
        if not required:
            return None
        return len(required & stats.owned_ball_ids), len(required)

    return None


async def grant_rewards(player, achievement, currency_name):
    """Give every reward of the achievement. Returns (text lines, whether balls were given)."""
    lines = []
    gave_ball = False

    for reward in achievement.rewards.all():
        try:
            if reward.gives_currency():
                await player.add_money(reward.currency_amount)

            if reward.gives_ball():
                for _ in range(reward.ball_amount):
                    await BallInstance.objects.acreate(
                        ball=reward.ball,
                        player=player,
                        attack_bonus=0,
                        health_bonus=0,
                    )
                gave_ball = True
        except Exception:
            log.exception(
                "Could not give reward %s of achievement %s to %s",
                reward.pk,
                achievement.pk,
                player.discord_id,
            )
            continue

        text = reward.describe(currency_name)
        if text:
            lines.append(text)

    return lines, gave_ball


async def notify(achievement, reward_lines, interaction, channel):
    if interaction is None and channel is None:
        return

    embed, file = ui.completion_embed(achievement, reward_lines)
    kwargs = {"embed": embed}
    if file:
        kwargs["file"] = file

    try:
        if interaction is not None:
            await interaction.followup.send(ephemeral=True, **kwargs)
        else:
            await channel.send(**kwargs)
    except discord.HTTPException:
        log.warning("Could not send the completion message for achievement %s", achievement.pk)


async def check_achievements(
    player,
    interaction=None,
    bot=None,
    channel=None,
):
    achievements = await sync_to_async(list)(
        Achievement.objects.filter(enabled=True)
        .exclude(requirement_type=Achievement.MANUAL)
        .prefetch_related("required_balls", "rewards__ball")
    )
    if not achievements:
        return

    done_ids = {
        achievement_id
        async for achievement_id in AchievementCompletion.objects.filter(
            discord_id=player.discord_id
        ).values_list("achievement_id", flat=True)
    }
    pending = [a for a in achievements if a.pk not in done_ids]
    if not pending:
        return

    stats = await load_stats(player.discord_id)
    currency_name = None

    for achievement in pending:
        progress = get_progress(achievement, stats)
        if progress is None or progress[0] < progress[1]:
            continue

        # Create the completion first: if two catches race, only one of them
        # gets "created" and hands out the rewards.
        _, created = await AchievementCompletion.objects.aget_or_create(
            achievement=achievement,
            discord_id=player.discord_id,
        )
        if not created:
            continue

        if currency_name is None:
            currency_name = await get_currency_name()

        reward_lines, gave_ball = await grant_rewards(player, achievement, currency_name)
        if gave_ball:
            stats = await load_stats(player.discord_id)

        await notify(achievement, reward_lines, interaction, channel)
