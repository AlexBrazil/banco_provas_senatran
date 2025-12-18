# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from banco_questoes.models import Curso, CursoModulo


class Command(BaseCommand):
    help = "Cria o curso 'Primeira Habilitação' e os módulos do SENATRAN 2025."

    def handle(self, *args, **options):
        curso_nome = "Primeira Habilitação"
        curso_slug = slugify(curso_nome)

        curso, _ = Curso.objects.get_or_create(
            slug=curso_slug,
            defaults={"nome": curso_nome},
        )

        modulos = [
            # Conteúdo
            (1, "Placas, Cores e Caminhos", "CONTEUDO", 1, 77),
            (2, "Escolhas e Consequências", "CONTEUDO", 78, 111),
            (3, "Na Direção da Segurança", "CONTEUDO", 112, 228),
            (4, "Cuidar, Agir e Preservar", "CONTEUDO", 229, 275),

            # Simulado
            (5, "Placas, Cores e Caminhos (Teste)", "SIMULADO", 277, 285),
            (6, "Escolhas e Consequências (Teste)", "SIMULADO", 286, 293),
            (7, "Na Direção da Segurança (Teste)", "SIMULADO", 294, 304),
            (8, "Cuidar, Agir e Preservar (Teste)", "SIMULADO", 305, 313),
        ]

        for ordem, nome, categoria, p_ini, p_fim in modulos:
            CursoModulo.objects.update_or_create(
                curso=curso,
                nome=nome,
                defaults={
                    "ordem": ordem,
                    "categoria": categoria,
                    "pagina_inicio": p_ini,
                    "pagina_fim": p_fim,
                    "ativo": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Curso e módulos criados/atualizados com sucesso."))
