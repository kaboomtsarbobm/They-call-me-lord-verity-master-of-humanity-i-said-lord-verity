from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0007_sync_choices_and_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlayerStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discord_id', models.BigIntegerField(unique=True)),
                ('total_catches', models.PositiveIntegerField(default=0)),
                ('catch_streak', models.PositiveIntegerField(default=0)),
                ('best_catch_streak', models.PositiveIntegerField(default=0)),
                ('wrong_guesses', models.PositiveIntegerField(default=0)),
                ('wrong_streak', models.PositiveIntegerField(default=0)),
                ('best_wrong_streak', models.PositiveIntegerField(default=0)),
                ('daily_streak', models.PositiveIntegerField(default=0)),
                ('best_daily_streak', models.PositiveIntegerField(default=0)),
                ('last_catch_day', models.DateField(blank=True, null=True)),
                ('catches_today', models.PositiveIntegerField(default=0)),
                ('best_catches_in_day', models.PositiveIntegerField(default=0)),
                ('fastest_catch', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='achievement',
            name='requirement_type',
            field=models.CharField(choices=[('manual', 'Manual'), ('catch_balls', 'catch balls'), ('specific_balls', 'catch balls but you specify them'), ('unique_balls', 'catch different balls'), ('catch_special', 'own special balls'), ('duplicate_balls', 'own copies of the same ball'), ('dex_percent', 'complete a percent of the dex'), ('attack_bonus', 'own a ball with an attack bonus'), ('health_bonus', 'own a ball with a health bonus'), ('money', 'have currency'), ('servers', 'catch balls in different servers'), ('total_catches', 'catch balls (all time)'), ('catch_streak', 'catch balls in a row without a wrong guess'), ('daily_streak', 'catch a ball every day'), ('catches_today', 'catch balls in one day'), ('fast_catch', 'catch a ball fast'), ('wrong_streak', 'get a name wrong in a row'), ('wrong_total', 'get names wrong in total')], default='manual', max_length=50),
        ),
    ]
