from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from banco_questoes.models import EventoAuditoria


class Command(BaseCommand):
    help = "Remove eventos de auditoria mais antigos que 6 meses."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=180,
            help="Quantidade de dias para manter (default: 180).",
        )

    def handle(self, *args, **options):
        dias = options["dias"]
        cutoff = timezone.now() - timedelta(days=dias)
        qs = EventoAuditoria.objects.filter(timestamp__lt=cutoff)
        total = qs.count()
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"{total} eventos removidos (antes de {cutoff})."))
