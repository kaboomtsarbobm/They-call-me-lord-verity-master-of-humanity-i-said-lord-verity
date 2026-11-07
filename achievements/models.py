from django.core.exceptions import ValidationError
from django.db import models


def _plural(amount, word):
    return f"{amount} {word}" if amount == 1 else f"{amount} {word}s"


class Achievement(models.Model):
    MANUAL = "manual"
    CATCH_BALLS = "catch_balls"
    SPECIFIC_BALLS = "specific_balls"
    UNIQUE_BALLS = "unique_balls"
    SPECIAL_BALLS = "catch_special"
    DUPLICATE_BALLS = "duplicate_balls"
    DEX_PERCENT = "dex_percent"
    ATTACK_BONUS = "attack_bonus"
    HEALTH_BONUS = "health_bonus"
    MONEY = "money"
    SERVERS = "servers"
    TOTAL_CATCHES = "total_catches"
    CATCH_STREAK = "catch_streak"
    DAILY_STREAK = "daily_streak"
    CATCHES_TODAY = "catches_today"
    FAST_CATCH = "fast_catch"
    WRONG_STREAK = "wrong_streak"
    WRONG_TOTAL = "wrong_total"
    SPECIAL_VARIETY = "special_variety"
    REGIMES = "regimes"
    ECONOMIES = "economies"
    COMBINED_BONUS = "combined_bonus"
    BAD_BONUS = "bad_bonus"
    SLOW_CATCH = "slow_catch"
    REDEMPTION = "redemption"
    TOO_SLOW = "too_slow"
    ACTIVE_DAYS = "active_days"
    WEEKEND_CATCHES = "weekend_catches"
    TRADED_BALLS = "traded_balls"

    REQUIREMENT_TYPES = (
        (MANUAL, "Manual"),
        (CATCH_BALLS, "catch balls"),
        (SPECIFIC_BALLS, "catch balls but you specify them"),
        (UNIQUE_BALLS, "catch different balls"),
        (SPECIAL_BALLS, "own special balls"),
        (DUPLICATE_BALLS, "own copies of the same ball"),
        (DEX_PERCENT, "complete a percent of the dex"),
        (ATTACK_BONUS, "own a ball with an attack bonus"),
        (HEALTH_BONUS, "own a ball with a health bonus"),
        (MONEY, "have currency"),
        (SERVERS, "catch balls in different servers"),
        (TOTAL_CATCHES, "catch balls (all time)"),
        (CATCH_STREAK, "catch balls in a row without a wrong guess"),
        (DAILY_STREAK, "catch a ball every day"),
        (CATCHES_TODAY, "catch balls in one day"),
        (FAST_CATCH, "catch a ball fast"),
        (WRONG_STREAK, "get a name wrong in a row"),
        (WRONG_TOTAL, "get names wrong in total"),
        (SPECIAL_VARIETY, "own balls from different specials"),
        (REGIMES, "own balls from different regimes"),
        (ECONOMIES, "own balls from different economies"),
        (COMBINED_BONUS, "own a ball with a combined bonus"),
        (BAD_BONUS, "own a ball with a bad bonus"),
        (SLOW_CATCH, "catch a ball slowly"),
        (REDEMPTION, "catch a ball after wrong guesses"),
        (TOO_SLOW, "be too slow to catch"),
        (ACTIVE_DAYS, "catch balls on different days"),
        (WEEKEND_CATCHES, "catch balls on weekends"),
        (TRADED_BALLS, "own balls from other players"),
    )

    title = models.CharField(max_length=100)
    caption = models.TextField(blank=True)
    image = models.ImageField(upload_to="achievements/", blank=True, null=True)
    enabled = models.BooleanField(default=True)

    requirement_type = models.CharField(
        max_length=50,
        choices=REQUIREMENT_TYPES,
        default=MANUAL,
    )
    requirement_amount = models.PositiveIntegerField(default=1)

    required_balls = models.ManyToManyField(
        "bd_models.Ball",
        blank=True,
        related_name="required_for_achievements",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title

    def requirement_text(self):
        amount = self.requirement_amount
        kind = self.requirement_type
        if kind == self.CATCH_BALLS:
            return f"Catch {_plural(amount, 'ball')}"
        if kind == self.UNIQUE_BALLS:
            return f"Catch {_plural(amount, 'different ball')}"
        if kind == self.SPECIFIC_BALLS:
            balls = [str(ball) for ball in self.required_balls.all()]
            if not balls:
                return "Catch specific balls (none selected)"
            amount = max(amount, 1)
            if amount == 1:
                return f"Catch: {', '.join(balls)}"
            if len(balls) == 1:
                return f"Catch {amount} {balls[0]}"
            return f"Catch {amount} of each: {', '.join(balls)}"
        if kind == self.SPECIAL_BALLS:
            return f"Own {_plural(amount, 'special ball')}"
        if kind == self.DUPLICATE_BALLS:
            return f"Own {amount} copies of the same ball"
        if kind == self.DEX_PERCENT:
            return f"Complete {amount}% of the dex"
        if kind == self.ATTACK_BONUS:
            return f"Own a ball with at least +{amount}% attack"
        if kind == self.HEALTH_BONUS:
            return f"Own a ball with at least +{amount}% health"
        if kind == self.MONEY:
            return f"Have {amount} currency"
        if kind == self.SERVERS:
            return f"Catch balls in {_plural(amount, 'different server')}"
        if kind == self.TOTAL_CATCHES:
            return f"Catch {_plural(amount, 'ball')} in total"
        if kind == self.CATCH_STREAK:
            return f"Catch {_plural(amount, 'ball')} in a row without a wrong guess"
        if kind == self.DAILY_STREAK:
            return f"Catch a ball {_plural(amount, 'day')} in a row"
        if kind == self.CATCHES_TODAY:
            return f"Catch {_plural(amount, 'ball')} in one day"
        if kind == self.FAST_CATCH:
            return f"Catch a ball within {_plural(amount, 'second')} of it spawning"
        if kind == self.WRONG_STREAK:
            return f"Get a name wrong {_plural(amount, 'time')} in a row"
        if kind == self.WRONG_TOTAL:
            return f"Get a name wrong {_plural(amount, 'time')} in total"
        if kind == self.SPECIAL_VARIETY:
            return f"Own balls from {_plural(amount, 'different special')}"
        if kind == self.REGIMES:
            return f"Own balls from {_plural(amount, 'different regime')}"
        if kind == self.ECONOMIES:
            return f"Own balls from {amount} different {'economy' if amount == 1 else 'economies'}"
        if kind == self.COMBINED_BONUS:
            return f"Own a ball with at least +{amount}% attack and health combined"
        if kind == self.BAD_BONUS:
            return f"Own a ball with an attack or health bonus of -{amount}% or worse"
        if kind == self.SLOW_CATCH:
            return f"Catch a ball at least {_plural(amount, 'second')} after it spawned"
        if kind == self.REDEMPTION:
            return f"Catch a ball right after getting it wrong {_plural(amount, 'time')} in a row"
        if kind == self.TOO_SLOW:
            return f"Be too slow to catch a ball {_plural(amount, 'time')}"
        if kind == self.ACTIVE_DAYS:
            return f"Catch balls on {_plural(amount, 'different day')}"
        if kind == self.WEEKEND_CATCHES:
            return f"Catch {_plural(amount, 'ball')} on weekends"
        if kind == self.TRADED_BALLS:
            return f"Own {_plural(amount, 'ball')} that came from other players"
        return "Awarded manually"


class AchievementReward(models.Model):
    CURRENCY = "currency"
    BALL = "ball"
    BOTH = "both"

    REWARD_TYPES = (
        (CURRENCY, "Money"),
        (BALL, "Ball(s)"),
        (BOTH, "Wowie Zowie!! How About Both!!"),
    )

    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    reward_type = models.CharField(
        max_length=20,
        choices=REWARD_TYPES,
        default=CURRENCY,
    )
    currency_amount = models.PositiveIntegerField(default=0)
    ball = models.ForeignKey(
        "bd_models.Ball",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="achievement_rewards",
    )
    ball_amount = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.achievement.title} reward"

    def clean(self):
        if not self.currency_amount and not self.ball_id:
            raise ValidationError("Set a currency amount, choose a ball, or both.")
        if self.ball_id and self.ball_amount < 1:
            raise ValidationError({"ball_amount": "Ball quantity must be at least 1."})

    def save(self, *args, **kwargs):
        if self.currency_amount and self.ball_id:
            self.reward_type = self.BOTH
        elif self.ball_id:
            self.reward_type = self.BALL
        else:
            self.reward_type = self.CURRENCY
        super().save(*args, **kwargs)

    def gives_currency(self):
        return self.reward_type in (self.CURRENCY, self.BOTH) and self.currency_amount > 0

    def gives_ball(self):
        return self.reward_type in (self.BALL, self.BOTH) and self.ball_id is not None and self.ball_amount > 0

    def describe(self, currency_name="currency"):
        parts = []
        if self.gives_currency():
            parts.append(f"{self.currency_amount} {currency_name}")
        if self.gives_ball():
            parts.append(f"{self.ball} x{self.ball_amount}")
        return " + ".join(parts)


class AchievementCompletion(models.Model):
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    discord_id = models.BigIntegerField(db_index=True)

    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("achievement", "discord_id"),
                name="unique_achievement_completion",
            ),
        )

    def __str__(self):
        return f"{self.discord_id} - {self.achievement.title}"


class PlayerStat(models.Model):
    discord_id = models.BigIntegerField(unique=True)
    total_catches = models.PositiveIntegerField(default=0)
    catch_streak = models.PositiveIntegerField(default=0)
    best_catch_streak = models.PositiveIntegerField(default=0)
    wrong_guesses = models.PositiveIntegerField(default=0)
    wrong_streak = models.PositiveIntegerField(default=0)
    best_wrong_streak = models.PositiveIntegerField(default=0)
    daily_streak = models.PositiveIntegerField(default=0)
    best_daily_streak = models.PositiveIntegerField(default=0)
    last_catch_day = models.DateField(blank=True, null=True)
    catches_today = models.PositiveIntegerField(default=0)
    best_catches_in_day = models.PositiveIntegerField(default=0)
    fastest_catch = models.FloatField(blank=True, null=True)
    slowest_catch = models.FloatField(blank=True, null=True)
    best_redemption = models.PositiveIntegerField(default=0)
    late_attempts = models.PositiveIntegerField(default=0)
    active_days = models.PositiveIntegerField(default=0)
    weekend_catches = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"stats for {self.discord_id}"
