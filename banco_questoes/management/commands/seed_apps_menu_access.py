from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from banco_questoes.models import AppModulo, Plano, PlanoPermissaoApp


FREE_PLAN_NAME = "Free"
PAID_PLAN_NAME = "Aprova DETRAN"
FREE_ALLOWED_SLUG = "simulado-digital"
LEGACY_SIMULADO_SLUG = "simulado-provas"

APP_MODULES = [
    {
        "slug": "simulado-digital",
        "nome": "Simulado de Provas",
        "ordem_menu": 1,
        "icone_path": "menu_app/icons/icon_app_1.png",
        "rota_nome": "simulado:inicio",
        "em_construcao": False,
    },
    {
        "slug": "perguntas-respostas",
        "nome": "Perguntas e Respostas para Estudos",
        "ordem_menu": 2,
        "icone_path": "menu_app/icons/icon_app_2.png",
        "rota_nome": "perguntas_respostas:index",
        "em_construcao": True,
    },
    {
        "slug": "apostila-cnh",
        "nome": "Apostila da CNH do Brasil",
        "ordem_menu": 3,
        "icone_path": "menu_app/icons/icon_app_3.png",
        "rota_nome": "apostila_cnh:index",
        "em_construcao": True,
    },
    {
        "slug": "simulacao-prova-detran",
        "nome": "Simulacao do Ambiente de Provas do DETRAN",
        "ordem_menu": 4,
        "icone_path": "menu_app/icons/icon_app_4.png",
        "rota_nome": "simulacao_prova:index",
        "em_construcao": True,
    },
    {
        "slug": "manual-aulas-praticas",
        "nome": "Manual de Aulas Praticas",
        "ordem_menu": 5,
        "icone_path": "menu_app/icons/icon_app_5.png",
        "rota_nome": "manual_pratico:index",
        "em_construcao": True,
    },
    {
        "slug": "aprenda-jogando",
        "nome": "Aprenda Jogando",
        "ordem_menu": 6,
        "icone_path": "menu_app/icons/icon_app_6.png",
        "rota_nome": "aprenda_jogando:index",
        "em_construcao": True,
    },
    {
        "slug": "oraculo",
        "nome": "Oraculo",
        "ordem_menu": 7,
        "icone_path": "menu_app/icons/icon_app_7.png",
        "rota_nome": "oraculo:index",
        "em_construcao": True,
    },
    {
        "slug": "aprova-plus",
        "nome": "Aprova+",
        "ordem_menu": 8,
        "icone_path": "menu_app/icons/icon_app_8.png",
        "rota_nome": "aprova_plus:index",
        "em_construcao": True,
    },
]


class Command(BaseCommand):
    help = "Seed idempotente de AppModulo e PlanoPermissaoApp para Free e Aprova DETRAN."

    def _migrate_legacy_simulado_slug(self) -> None:
        canonical = AppModulo.objects.filter(slug=FREE_ALLOWED_SLUG).first()
        legacy = AppModulo.objects.filter(slug=LEGACY_SIMULADO_SLUG).first()
        if not legacy:
            return

        if canonical:
            # Se ambos existem, desativa o legado para nao duplicar no menu/status.
            if legacy.ativo:
                legacy.ativo = False
                legacy.save(update_fields=["ativo", "atualizado_em"])
            return

        legacy.slug = FREE_ALLOWED_SLUG
        legacy.save(update_fields=["slug", "atualizado_em"])

    @transaction.atomic
    def handle(self, *args, **options):
        self._migrate_legacy_simulado_slug()

        free_plan = Plano.objects.filter(nome__iexact=FREE_PLAN_NAME).first()
        if not free_plan:
            raise CommandError("Plano 'Free' nao encontrado. Crie o plano e rode novamente.")

        paid_plan = Plano.objects.filter(nome__iexact=PAID_PLAN_NAME).first()
        if not paid_plan:
            raise CommandError("Plano 'Aprova DETRAN' nao encontrado. Crie o plano e rode novamente.")

        app_created = 0
        app_updated = 0
        perm_created = 0
        perm_updated = 0

        app_by_slug: dict[str, AppModulo] = {}
        for data in APP_MODULES:
            obj, created = AppModulo.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "nome": data["nome"],
                    "ativo": True,
                    "ordem_menu": data["ordem_menu"],
                    "icone_path": data["icone_path"],
                    "rota_nome": data["rota_nome"],
                    "em_construcao": data["em_construcao"],
                },
            )
            app_by_slug[obj.slug] = obj
            if created:
                app_created += 1
            else:
                app_updated += 1

        for slug, app_modulo in app_by_slug.items():
            free_allowed = slug == FREE_ALLOWED_SLUG
            free_defaults = {
                "permitido": free_allowed,
                "limite_qtd": free_plan.limite_qtd if free_allowed else None,
                "limite_periodo": free_plan.limite_periodo if free_allowed else None,
            }
            _, created = PlanoPermissaoApp.objects.update_or_create(
                plano=free_plan,
                app_modulo=app_modulo,
                defaults=free_defaults,
            )
            if created:
                perm_created += 1
            else:
                perm_updated += 1

            paid_defaults = {
                "permitido": True,
                "limite_qtd": None,
                "limite_periodo": None,
            }
            _, created = PlanoPermissaoApp.objects.update_or_create(
                plano=paid_plan,
                app_modulo=app_modulo,
                defaults=paid_defaults,
            )
            if created:
                perm_created += 1
            else:
                perm_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seed concluido com sucesso. "
                f"AppModulo: {app_created} criados, {app_updated} atualizados. "
                f"PlanoPermissaoApp: {perm_created} criados, {perm_updated} atualizados."
            )
        )
