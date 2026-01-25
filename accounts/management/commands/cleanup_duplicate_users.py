from collections import defaultdict
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Find and delete duplicate users (same email), keeping the earliest by ID"

    def handle(self, *args, **options):
        # Group users by email (case-insensitive)
        email_groups = defaultdict(list)
        for user in User.objects.all():
            email_groups[user.email.lower()].append(user)

        deleted_count = 0
        kept_count = 0

        for email, users in email_groups.items():
            if len(users) > 1:
                users_sorted = sorted(users, key=lambda u: u.id)
                keep_user = users_sorted[0]
                delete_users = users_sorted[1:]
                
                self.stdout.write(f"\nEmail: {email}")
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Keeping: User(id={keep_user.id}, username={keep_user.username})"
                    )
                )
                
                for u in delete_users:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Deleting: User(id={u.id}, username={u.username})"
                        )
                    )
                    u.delete()
                    deleted_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Cleanup complete. Deleted {deleted_count} duplicate users.")
        )
