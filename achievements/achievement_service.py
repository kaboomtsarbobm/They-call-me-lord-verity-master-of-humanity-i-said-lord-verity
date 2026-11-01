import logging
from dataclasses import dataclass, field

import discord
from asgiref.sync import sync_to_async
from django.db.models import Count

from bd_models.models import BallInstance

from . import ui
from .models import Achievement, AchievementCompletion

log = logging.getLogger("ballsdex.packages.achievements")


@dataclass
class PlayerStats:
    total: int = 0
    ball_counts: dict = field(default_factory=dict)  # ball id -> how many copies the player owns

    @property
    def unique(self):
        return len(self.ball_counts)


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
    rows = owned.order_by().values("ball_id").annotate(copies=Count("id"))
    ball_counts = {row["ball_id"]: row["copies"] async for row in rows}
    return PlayerStats(total=sum(ball_counts.values()), ball_counts=ball_counts)


def get_progress(achievement, stats):
    """Return (current, target), or None if the achievement can't be completed automatically."""
    kind = achievement.requirement_type
    target = max(achievement.requirement_amount, 1)

    if kind == Achievement.CATCH_BALLS:
        return min(stats.total, target), target

    if kind == Achievement.UNIQUE_BALLS:
        return min(stats.unique, target), target

    if kind == Achievement.SPECIFIC_BALLS:
        # The amount is how many copies of EACH selected ball the player needs.
        required = {ball.pk for ball in achievement.required_balls.all()}
        if not required:
            return None
        have = sum(min(stats.ball_counts.get(pk, 0), target) for pk in required)
        return have, target * len(required)

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
