from django.core.management.base import BaseCommand

from atelier.services.youtube import sync_channel_videos


class Command(BaseCommand):
    help = "Importa vídeos recentes do canal da professora no YouTube."

    def handle(self, *args, **options):
        total = sync_channel_videos()
        self.stdout.write(self.style.SUCCESS(f"{total} vídeos sincronizados com sucesso."))
