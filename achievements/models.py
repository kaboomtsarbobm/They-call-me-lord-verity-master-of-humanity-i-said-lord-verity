from django.db import models


class Achievement(models.Model):
    MANUAL = "manual"
    CATCH_BALLS = "catch_balls"
    SPECIFIC_BALLS = "specific_balls"
    UNIQUE_BALLS = "unique_balls"

    REQUIREMENT_TYPES = (
        (MANUAL, "Manual"),
        (CATCH_BALLS, "catch balls"),
        (SPECIFIC_BALLS, "catch balls but you specify them"),
        (UNIQUE_BALLS, "catch different balls"),
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


class AchievementCompletion(models.Model):
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    discord_id = models.BigIntegerField()

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