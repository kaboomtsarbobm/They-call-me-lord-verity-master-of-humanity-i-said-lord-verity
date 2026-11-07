import logging
from dataclasses import dataclass, field

import discord
from asgiref.sync import sync_to_async
from django.db.models import Count, F, Max, Min, Q

from bd_models.models import Ball, BallInstance, Player

from . import ui
from .models import Achievement, AchievementCompletion, PlayerStat

log = logging.getLogger("ballsdex.packages.achievements")


@dataclass
class PlayerStats:
    tracked: object
    total: int = 0
    ball_counts: dict = field(default_factory=dict)
    specials: int = 0
    max_attack: int = 0
    max_health: int = 0
    servers: int = 0
    special_variety: int = 0
    combined_bonus: int = 0
    min_bonus: int = 0
    traded: int = 0
    regimes: int = 0
    economies: int = 0
    dex_total: int = 0
    money: int = 0

    @property
    def unique(self):
        return len(self.ball_counts)


async def get_currency_name():
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


async def read_money(discord_id):
    try:
        money = await Player.objects.filter(discord_id=discord_id).values_list("money", flat=True).afirst()
    except Exception:
        log.debug("Could not read the player's money", exc_info=True)
        return 0
    return money or 0


async def count_distinct_ball_field(discord_id, lookup):
    try:
        owned = BallInstance.objects.filter(player__discord_id=discord_id).exclude(**{f"{lookup}__isnull": True})
        return await owned.order_by().values(lookup).distinct().acount()
    except Exception:
        log.debug("Could not count distinct %s", lookup, exc_info=True)
        return 0


async def load_stats(discord_id, kinds=None):
    owned = BallInstance.objects.filter(player__discord_id=discord_id)
    rows = owned.order_by().values("ball_id").annotate(copies=Count("id"))
    ball_counts = {row["ball_id"]: row["copies"] async for row in rows}

    extra = await owned.order_by().aaggregate(
        specials=Count("id", filter=Q(special__isnull=False)),
        max_attack=Max("attack_bonus"),
        max_health=Max("health_bonus"),
        servers=Count("server_id", distinct=True),
        special_variety=Count("special_id", distinct=True),
        combined_bonus=Max(F("attack_bonus") + F("health_bonus")),
        min_attack=Min("attack_bonus"),
        min_health=Min("health_bonus"),
        traded=Count("id", filter=Q(trade_player__isnull=False)),
    )

    tracked = await PlayerStat.objects.filter(discord_id=discord_id).afirst()
    if tracked is None:
        tracked = PlayerStat(discord_id=discord_id)

    stats = PlayerStats(
        tracked=tracked,
        total=sum(ball_counts.values()),
        ball_counts=ball_counts,
        specials=extra["specials"] or 0,
        max_attack=extra["max_attack"] or 0,
        max_health=extra["max_health"] or 0,
        servers=extra["servers"] or 0,
        special_variety=extra["special_variety"] or 0,
        combined_bonus=extra["combined_bonus"] or 0,
        min_bonus=min(extra["min_attack"] or 0, extra["min_health"] or 0),
        traded=extra["traded"] or 0,
    )

    if kinds is None or Achievement.REGIMES in kinds:
        stats.regimes = await count_distinct_ball_field(discord_id, "ball__regime")
    if kinds is None or Achievement.ECONOMIES in kinds:
        stats.economies = await count_distinct_ball_field(discord_id, "ball__economy")
    if kinds is None or Achievement.DEX_PERCENT in kinds:
        stats.dex_total = await Ball.objects.filter(enabled=True).acount()
    if kinds is None or Achievement.MONEY in kinds:
        stats.money = await read_money(discord_id)
    return stats


def get_progress(achievement, stats):
    kind = achievement.requirement_type
    target = max(achievement.requirement_amount, 1)
    tracked = stats.tracked

    if kind == Achievement.SPECIFIC_BALLS:
        required = {ball.pk for ball in achievement.required_balls.all()}
        if not required:
            return None
        have = sum(min(stats.ball_counts.get(pk, 0), target) for pk in required)
        return have, target * len(required)

    if kind == Achievement.FAST_CATCH:
        done = tracked.fastest_catch is not None and tracked.fastest_catch <= target
        return (1 if done else 0), 1

    if kind == Achievement.SLOW_CATCH:
        done = tracked.slowest_catch is not None and tracked.slowest_catch >= target
        return (1 if done else 0), 1

    if kind == Achievement.DEX_PERCENT:
        target = min(target, 100)
        percent = stats.unique * 100 // stats.dex_total if stats.dex_total else 0
        return min(percent, target), target

    current = {
        Achievement.CATCH_BALLS: stats.total,
        Achievement.UNIQUE_BALLS: stats.unique,
        Achievement.SPECIAL_BALLS: stats.specials,
        Achievement.DUPLICATE_BALLS: max(stats.ball_counts.values(), default=0),
        Achievement.ATTACK_BONUS: stats.max_attack,
        Achievement.HEALTH_BONUS: stats.max_health,
        Achievement.MONEY: stats.money,
        Achievement.SERVERS: stats.servers,
        Achievement.TOTAL_CATCHES: tracked.total_catches,
        Achievement.CATCH_STREAK: tracked.best_catch_streak,
        Achievement.DAILY_STREAK: tracked.best_daily_streak,
        Achievement.CATCHES_TODAY: tracked.best_catches_in_day,
        Achievement.WRONG_STREAK: tracked.best_wrong_streak,
        Achievement.WRONG_TOTAL: tracked.wrong_guesses,
        Achievement.SPECIAL_VARIETY: stats.special_variety,
        Achievement.REGIMES: stats.regimes,
        Achievement.ECONOMIES: stats.economies,
        Achievement.COMBINED_BONUS: stats.combined_bonus,
        Achievement.BAD_BONUS: -stats.min_bonus,
        Achievement.REDEMPTION: tracked.best_redemption,
        Achievement.TOO_SLOW: tracked.late_attempts,
        Achievement.ACTIVE_DAYS: tracked.active_days,
        Achievement.WEEKEND_CATCHES: tracked.weekend_catches,
        Achievement.TRADED_BALLS: stats.traded,
    }.get(kind)

    if current is None:
        return None
    return min(max(current, 0), target), target


async def grant_rewards(player, achievement, currency_name):
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


async def load_achievement(achievement_id):
    found = await sync_to_async(list)(
        Achievement.objects.filter(pk=achievement_id).prefetch_related("rewards__ball")
    )
    return found[0] if found else None


async def give_rewards(discord_id, achievement):
    player, _ = await Player.objects.aget_or_create(discord_id=discord_id)
    currency_name = await get_currency_name()
    return await grant_rewards(player, achievement, currency_name)


async def award_achievement(discord_id, achievement, recipient=None):
    _, created = await AchievementCompletion.objects.aget_or_create(
        achievement=achievement,
        discord_id=discord_id,
    )
    if not created:
        return False

    reward_lines, _ = await give_rewards(discord_id, achievement)
    await notify(achievement, reward_lines, None, recipient)
    return True


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

    kinds = {a.requirement_type for a in pending}
    stats = await load_stats(player.discord_id, kinds)
    currency_name = None

    for achievement in pending:
        progress = get_progress(achievement, stats)
        if progress is None or progress[0] < progress[1]:
            continue

        _, created = await AchievementCompletion.objects.aget_or_create(
            achievement=achievement,
            discord_id=player.discord_id,
        )
        if not created:
            continue

        if currency_name is None:
            currency_name = await get_currency_name()

        reward_lines, _ = await grant_rewards(player, achievement, currency_name)
        if reward_lines:
            stats = await load_stats(player.discord_id, kinds)

        await notify(achievement, reward_lines, interaction, channel)
