from __future__ import annotations

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apostila_cnh.models import ApostilaDocumento, ApostilaPagina
from apostila_cnh.services.ingestao_pdf import ingerir_documento_pdf


class Command(BaseCommand):
    help = "Importa o PDF da apostila CNH e indexa texto por pagina (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--slug", required=True, type=str)
        parser.add_argument("--pdf-path", type=str)
        parser.add_argument("--titulo", type=str)
        parser.add_argument("--ativar", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        slug = options["slug"].strip()
        pdf_path_opt = (options.get("pdf_path") or "").strip()
        titulo_opt = (options.get("titulo") or "").strip()
        ativar = options.get("ativar", False)

        documento = ApostilaDocumento.objects.filter(slug=slug).first()
        created_documento = False
        if not documento:
            if not pdf_path_opt:
                raise CommandError(
                    "Documento nao encontrado para o slug informado. "
                    "Use --pdf-path no primeiro import."
                )
            documento = ApostilaDocumento(
                slug=slug,
                titulo=titulo_opt or slug.replace("-", " ").title(),
            )
            created_documento = True

        if titulo_opt and documento.titulo != titulo_opt:
            documento.titulo = titulo_opt
            documento.save(update_fields=["titulo", "atualizado_em"])

        if pdf_path_opt:
            pdf_path = Path(pdf_path_opt)
            if not pdf_path.exists() or not pdf_path.is_file():
                raise CommandError(f"Arquivo PDF nao encontrado: {pdf_path}")
            if pdf_path.suffix.lower() != ".pdf":
                raise CommandError(f"Arquivo informado nao e PDF: {pdf_path}")

            old_file_name = documento.arquivo_pdf.name if documento.arquivo_pdf else ""
            arquivo_nome = f"{slug}.pdf"
            with pdf_path.open("rb") as fh:
                documento.arquivo_pdf.save(arquivo_nome, File(fh), save=False)
            documento.save()
            new_file_name = documento.arquivo_pdf.name
            if old_file_name and old_file_name != new_file_name:
                documento.arquivo_pdf.storage.delete(old_file_name)

        if not documento.arquivo_pdf:
            raise CommandError(
                "Documento sem arquivo PDF associado. "
                "Use --pdf-path para anexar o arquivo."
            )
        if not Path(documento.arquivo_pdf.path).exists():
            raise CommandError(
                "Arquivo PDF do documento nao foi encontrado no storage privado. "
                "Reimporte usando --pdf-path."
            )

        if ativar and not documento.ativo:
            ApostilaDocumento.objects.filter(ativo=True).exclude(pk=documento.pk).update(ativo=False)
            documento.ativo = True
            documento.save(update_fields=["ativo", "atualizado_em"])

        resultado = ingerir_documento_pdf(documento)

        self.stdout.write(self.style.SUCCESS("IMPORTACAO FINALIZADA"))
        self.stdout.write(f"Documento: {documento.slug}")
        self.stdout.write(f"Criado agora: {'SIM' if created_documento else 'NAO'}")
        self.stdout.write(f"Total de paginas no PDF: {resultado.total_paginas}")
        self.stdout.write(f"Paginas criadas: {resultado.paginas_criadas}")
        self.stdout.write(f"Paginas atualizadas: {resultado.paginas_atualizadas}")
        self.stdout.write(f"Paginas removidas (sobras): {resultado.paginas_removidas}")
        self.stdout.write(f"Paginas sem texto: {resultado.paginas_sem_texto}")

        total_indexado = ApostilaPagina.objects.filter(documento=documento).count()
        self.stdout.write(f"Total de paginas indexadas no banco: {total_indexado}")
