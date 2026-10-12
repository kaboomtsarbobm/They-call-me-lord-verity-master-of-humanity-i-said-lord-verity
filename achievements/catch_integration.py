"""Catch integration for Verity Achievements."""

import logging
from functools import wraps

log = logging.getLogger("ballsdex.packages.achievements")


def install_catch_integration(bot) -> None:
    from ballsdex.packages.countryballs.countryball import BallSpawnView

    current = BallSpawnView.catch_ball
    if getattr(current, "_verity_achievements_wrapped", False):
        return

    original_catch_ball = current

    @wraps(original_catch_ball)
    async def catch_ball_with_achievements(
        self, user, *, player=None, guild=None
    ):
        result = await original_catch_ball(
            self, user, player=player, guild=guild
        )

        try:
            from bd_models.models import Player
            from .achievement_service import check_achievements

            achievement_player = player
            if achievement_player is None:
                achievement_player, _ = await Player.objects.aget_or_create(
                    discord_id=user.id
                )

            message = getattr(self, "message", None)
            await check_achievements(
                achievement_player,
                interaction=None,
                bot=bot,
                channel=getattr(message, "channel", None),
            )
        except Exception:
            log.exception("Failed to check achievements after a catch")

        return result

    catch_ball_with_achievements._verity_achievements_wrapped = True
    BallSpawnView.catch_ball = catch_ball_with_achievements
    log.info("Verity Achievements catch integration installed")
