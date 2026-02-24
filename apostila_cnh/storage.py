from __future__ import annotations

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateApostilaStorage(FileSystemStorage):
    """
    Storage privado para PDFs da apostila.
    Nao expoe URL direta do arquivo.
    """

    def __init__(self, location: str | None = None):
        super().__init__(
            location=location or str(settings.APOSTILA_CNH_PDF_ROOT),
            base_url=None,
        )

    def url(self, name):
        raise ValueError("Arquivo privado: use endpoint protegido para acesso.")

    def get_available_name(self, name, max_length=None):
        # Mantem nome deterministico na reimportacao.
        if self.exists(name):
            self.delete(name)
        return name


private_apostila_storage = PrivateApostilaStorage()
