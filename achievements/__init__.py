import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.achievements")


async def setup(bot: "BallsDexBot"):
    from .cog import AchievementCog
    from .catch_integration import install_catch_integration

    try:
        install_catch_integration(bot)
    except Exception:
        log.exception(
            "Verity Achievements could not hook into catches, achievements will not trigger automatically"
        )
    await bot.add_cog(AchievementCog(bot))
