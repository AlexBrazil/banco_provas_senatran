# Simulado Digital - Banco de Questoes

Projeto Django 6 para gerenciar cursos, modulos, documentos e questoes do material SENATRAN.

## Variaveis de ambiente
Crie um arquivo `.env` a partir do exemplo e preencha os segredos antes de rodar o projeto:

```
cp .env.example .env
```

Chaves suportadas (todas obrigatorias):
- `DJANGO_SECRET_KEY`: chave secreta do Django.
- `DJANGO_DEBUG`: `1` para modo debug, `0` para producao.
- `DB_NAME`: nome do banco PostgreSQL.
- `DB_USER`: usuario do banco.
- `DB_PASSWORD`: senha do banco.
- `DB_HOST`: host do banco, ex. `127.0.0.1`.
- `DB_PORT`: porta do banco, ex. `5432`.

## Rodando localmente
1. Crie/ative seu virtualenv e instale dependencias (`pip install -r requirements.txt`, se existir).
2. Configure o banco PostgreSQL conforme as variaveis acima.
3. Execute migracoes: `python manage.py migrate`.
4. (Opcional) Popule os modulos SENATRAN 2025: `python manage.py seed_modulos_senatran2025`.
5. Suba o servidor: `python manage.py runserver`.
