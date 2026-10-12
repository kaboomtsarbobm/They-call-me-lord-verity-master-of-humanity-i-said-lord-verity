from typing import TYPE_CHECKING

from .cog import AchievementCog
from .catch_integration import install_catch_integration

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


async def setup(bot: "BallsDexBot"):
    # Keep catch tracking inside this package; countryball.py stays unmodified.
    install_catch_integration(bot)
    await bot.add_cog(AchievementCog(bot))
