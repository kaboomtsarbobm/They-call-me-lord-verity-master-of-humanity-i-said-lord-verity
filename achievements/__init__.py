from typing import TYPE_CHECKING

from .cog import AchievementCog

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


async def setup(bot: "BallsDexBot"):
    from .catch_integration import install_catch_integration

    install_catch_integration(bot)
    await bot.add_cog(AchievementCog(bot))
