import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import Team, TeamScoreHistory


class Command(BaseCommand):
    help = 'Generate sample score history data for teams'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of history to generate'
        )
        parser.add_argument(
            '--entries',
            type=int,
            default=5,
            help='Number of entries per day'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing history before generating new data'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Include inactive teams (not marked as in_game)'
        )

    def handle(self, *args, **options):
        days = options['days']
        entries_per_day = options['entries']
        clear_existing = options['clear']
        include_all = options['all']
        
        # Get teams based on options
        if include_all:
            teams = Team.objects.all()
        else:
            teams = Team.objects.filter(is_in_game=True)
            
        if not teams.exists():
            self.stderr.write(self.style.WARNING('No teams found. Try including inactive teams with --all'))
            return
        
        # Clear existing data if requested
        if clear_existing:
            self.stdout.write('Clearing existing score history...')
            TeamScoreHistory.objects.all().delete()
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        self.stdout.write(f'Generating {days} days of score history for {teams.count()} teams...')
        
        # For each team, generate a gradually increasing score
        for team in teams:
            self.stdout.write(f'Generating data for team: {team.name}')
            
            # Set base scores
            blue_points = random.randint(100, 500)
            red_points = random.randint(100, 500)
            total_score = blue_points + red_points
            
            # Generate entries
            for day in range(days):
                # Get evenly distributed timestamps for each day
                for entry in range(entries_per_day):
                    timestamp = start_date + timedelta(
                        days=day, 
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    )
                    
                    # Randomly increase points
                    if random.random() > 0.5:  # 50% chance to increase
                        blue_increase = random.randint(0, 50)
                        blue_points += blue_increase
                        total_score += blue_increase
                        reason = "Blue points gained"
                    else:
                        red_increase = random.randint(0, 50)
                        red_points += red_increase
                        total_score += red_increase
                        reason = "Red points gained"
                    
                    # Create history entry
                    TeamScoreHistory.objects.create(
                        team=team,
                        timestamp=timestamp,
                        score=total_score,
                        blue_points=blue_points,
                        red_points=red_points,
                        change_reason=reason
                    )
        
        total_entries = TeamScoreHistory.objects.count()
        self.stdout.write(self.style.SUCCESS(f'Successfully generated {total_entries} score history entries!')) 