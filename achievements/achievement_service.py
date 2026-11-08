import logging
from dataclasses import dataclass, field

import discord
from asgiref.sync import sync_to_async
from django.db.models import Count, F, Max, Min, Q
from django.db.models.functions import Length, Lower, Substr

from bd_models.models import Ball, BallInstance, Player

from . import ui
from .models import Achievement, AchievementCompletion, PlayerStat

log = logging.getLogger("ballsdex.packages.achievements")

GUESS_KINDS = (
    Achievement.GUESS_NAME,
    Achievement.GUESS_CONTAINS,
    Achievement.GUESS_LENGTH,
    Achievement.GUESS_SHOUT,
)


@dataclass
class PlayerStats:
    tracked: object
    total: int = 0
    ball_counts: dict = field(default_factory=dict)
    special_counts: dict = field(default_factory=dict)
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
    same_server: int = 0
    same_regime: int = 0
    same_economy: int = 0
    same_special: int = 0
    average_balls: int = 0
    longest_name: int = 0
    shortest_name: object = None
    letters: int = 0
    rarity_order: list = field(default_factory=list)
    completed: int = 0
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


async def largest_group(discord_id, lookup):
    try:
        owned = BallInstance.objects.filter(player__discord_id=discord_id).exclude(**{f"{lookup}__isnull": True})
        rows = owned.order_by().values(lookup).annotate(copies=Count("id"))
        return max([row["copies"] async for row in rows], default=0)
    except Exception:
        log.debug("Could not group balls by %s", lookup, exc_info=True)
        return 0


async def name_lengths(discord_id):
    try:
        owned = BallInstance.objects.filter(player__discord_id=discord_id)
        result = await owned.order_by().annotate(name_length=Length("ball__country")).aaggregate(
            longest=Max("name_length"),
            shortest=Min("name_length"),
        )
        return result["longest"] or 0, result["shortest"]
    except Exception:
        log.debug("Could not read ball name lengths", exc_info=True)
        return 0, None


async def count_first_letters(discord_id):
    try:
        owned = BallInstance.objects.filter(player__discord_id=discord_id)
        rows = owned.order_by().annotate(first=Lower(Substr("ball__country", 1, 1))).values("first").distinct()
        return len([row["first"] async for row in rows if row["first"] and row["first"].isalpha()])
    except Exception:
        log.debug("Could not count first letters", exc_info=True)
        return 0


async def load_stats(discord_id, kinds=None):
    def wants(*names):
        return kinds is None or any(name in kinds for name in names)

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
        average_balls=Count("id", filter=Q(attack_bonus=0, health_bonus=0)),
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
        average_balls=extra["average_balls"] or 0,
    )

    if wants(Achievement.SPECIAL_BALLS):
        special_rows = owned.exclude(special__isnull=True).order_by().values("special_id").annotate(copies=Count("id"))
        stats.special_counts = {row["special_id"]: row["copies"] async for row in special_rows}
    if wants(Achievement.REGIMES):
        stats.regimes = await count_distinct_ball_field(discord_id, "ball__regime")
    if wants(Achievement.ECONOMIES):
        stats.economies = await count_distinct_ball_field(discord_id, "ball__economy")
    if wants(Achievement.SERVER_BALLS):
        stats.same_server = await largest_group(discord_id, "server_id")
    if wants(Achievement.SAME_REGIME):
        stats.same_regime = await largest_group(discord_id, "ball__regime")
    if wants(Achievement.SAME_ECONOMY):
        stats.same_economy = await largest_group(discord_id, "ball__economy")
    if wants(Achievement.SAME_SPECIAL):
        stats.same_special = await largest_group(discord_id, "special_id")
    if wants(Achievement.LONG_NAME, Achievement.SHORT_NAME):
        stats.longest_name, stats.shortest_name = await name_lengths(discord_id)
    if wants(Achievement.ALPHABET):
        stats.letters = await count_first_letters(discord_id)
    if wants(Achievement.RARE_BALLS, Achievement.RAREST_SET, Achievement.COMMON_SET):
        stats.rarity_order = [
            pk async for pk in Ball.objects.filter(enabled=True).order_by("rarity").values_list("pk", flat=True)
        ]
    if wants(Achievement.ACHIEVEMENTS_DONE):
        stats.completed = await AchievementCompletion.objects.filter(discord_id=discord_id).acount()
    if wants(Achievement.DEX_PERCENT):
        stats.dex_total = await Ball.objects.filter(enabled=True).acount()
    if wants(Achievement.MONEY):
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

    if kind == Achievement.DOUBLE_CATCH:
        done = tracked.smallest_gap is not None and tracked.smallest_gap <= target
        return (1 if done else 0), 1

    if kind == Achievement.SHORT_NAME:
        done = stats.shortest_name is not None and stats.shortest_name <= target
        return (1 if done else 0), 1

    if kind == Achievement.RARE_BALLS:
        rarest = set(stats.rarity_order[:target])
        return (1 if rarest & set(stats.ball_counts) else 0), 1

    if kind in (Achievement.RAREST_SET, Achievement.COMMON_SET):
        order = stats.rarity_order if kind == Achievement.RAREST_SET else stats.rarity_order[::-1]
        pool = set(order[:target])
        if not pool:
            return None
        return len(pool & set(stats.ball_counts)), len(pool)

    if kind == Achievement.DEX_PERCENT:
        target = min(target, 100)
        percent = stats.unique * 100 // stats.dex_total if stats.dex_total else 0
        return min(percent, target), target

    if kind == Achievement.SPECIAL_BALLS and achievement.required_special_id:
        return min(stats.special_counts.get(achievement.required_special_id, 0), target), target

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
        Achievement.WRONG_STREAK: tracked.best_wrong_streak,
        Achievement.WRONG_TOTAL: tracked.wrong_guesses,
        Achievement.SPECIAL_VARIETY: stats.special_variety,
        Achievement.REGIMES: stats.regimes,
        Achievement.ECONOMIES: stats.economies,
        Achievement.COMBINED_BONUS: stats.combined_bonus,
        Achievement.BAD_BONUS: -stats.min_bonus,
        Achievement.REDEMPTION: tracked.best_redemption,
        Achievement.TOO_SLOW: tracked.late_attempts,
        Achievement.TRADED_BALLS: stats.traded,
        Achievement.SPECIAL_CATCHES: tracked.special_catches,
        Achievement.SERVER_BALLS: stats.same_server,
        Achievement.QUICK_CATCHES: tracked.quick_catches,
        Achievement.FIRST_TRY_CATCHES: tracked.first_try_catches,
        Achievement.ACHIEVEMENTS_DONE: stats.completed,
        Achievement.SAME_REGIME: stats.same_regime,
        Achievement.SAME_ECONOMY: stats.same_economy,
        Achievement.AVERAGE_BALL: stats.average_balls,
        Achievement.SAME_SPECIAL: stats.same_special,
        Achievement.LONG_NAME: stats.longest_name,
        Achievement.ALPHABET: stats.letters,
    }.get(kind)

    if current is None:
        return None
    return min(max(current, 0), target), target


def guess_matches(achievement, guess):
    kind = achievement.requirement_type
    text = guess.strip()
    amount = max(achievement.requirement_amount, 1)

    if kind == Achievement.GUESS_LENGTH:
        return len(text) >= amount

    if kind == Achievement.GUESS_SHOUT:
        letters = [char for char in text if char.isalpha()]
        return len(letters) >= amount and all(char.isupper() for char in letters)

    wanted = [part.strip().lower() for part in achievement.guess_text.split(";") if part.strip()]
    if not wanted:
        return False
    lowered = text.lower()
    if kind == Achievement.GUESS_NAME:
        return lowered in wanted
    if kind == Achievement.GUESS_CONTAINS:
        return any(part in lowered for part in wanted)
    return False


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
                        special=reward.special,
                        attack_bonus=reward.attack_bonus,
                        health_bonus=reward.health_bonus,
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
    if not achievement.announce:
        return
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
        Achievement.objects.filter(pk=achievement_id).prefetch_related("rewards__ball", "rewards__special")
    )
    return found[0] if found else None


async def give_rewards(discord_id, achievement):
    player, _ = await Player.objects.aget_or_create(discord_id=discord_id)
    currency_name = await get_currency_name()
    return await grant_rewards(player, achievement, currency_name)


async def claim_completion(achievement, discord_id):
    if achievement.max_winners:
        taken = await AchievementCompletion.objects.filter(achievement=achievement).acount()
        if taken >= achievement.max_winners:
            return False

    completion, created = await AchievementCompletion.objects.aget_or_create(
        achievement=achievement,
        discord_id=discord_id,
    )
    if not created:
        return False

    if achievement.max_winners:
        rank = await AchievementCompletion.objects.filter(
            achievement=achievement,
            pk__lte=completion.pk,
        ).acount()
        if rank > achievement.max_winners:
            await completion.adelete()
            return False
    return True


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
    guess=None,
):
    achievements = await sync_to_async(list)(
        Achievement.objects.filter(enabled=True)
        .exclude(requirement_type=Achievement.MANUAL)
        .prefetch_related("required_balls", "rewards__ball", "rewards__special")
    )
    if not achievements:
        return

    done_ids = {
        achievement_id
        async for achievement_id in AchievementCompletion.objects.filter(
            discord_id=player.discord_id
        ).values_list("achievement_id", flat=True)
    }
    remaining = [a for a in achievements if a.pk not in done_ids]
    if guess is None:
        remaining = [a for a in remaining if a.requirement_type not in GUESS_KINDS]
    if not remaining:
        return

    kinds = {a.requirement_type for a in remaining}
    stats = await load_stats(player.discord_id, kinds)
    currency_name = None

    progressed = True
    while progressed:
        progressed = False
        for achievement in list(remaining):
            if achievement.requires_id is not None and achievement.requires_id not in done_ids:
                continue

            if achievement.requirement_type in GUESS_KINDS:
                if not guess_matches(achievement, guess):
                    continue
            else:
                progress = get_progress(achievement, stats)
                if progress is None or progress[0] < progress[1]:
                    continue

            remaining.remove(achievement)
            if not await claim_completion(achievement, player.discord_id):
                continue

            done_ids.add(achievement.pk)
            stats.completed += 1
            progressed = True

            if currency_name is None:
                currency_name = await get_currency_name()

            reward_lines, _ = await grant_rewards(player, achievement, currency_name)
            if reward_lines:
                stats = await load_stats(player.discord_id, kinds)

            await notify(achievement, reward_lines, interaction, channel)
