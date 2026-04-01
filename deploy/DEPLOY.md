# Deploy na VPS

Este projeto já está preparado para rodar em produção no subdomínio `profsol.moven.cloud`.

## Estrutura sugerida na VPS

- código em `/srv/profsol/current`
- ambiente em `/srv/profsol/current/.venv`
- arquivo de ambiente em `/etc/profsol/profsol.env`
- socket Unix em `/run/profsol/profsol.sock`

## Checklist

1. Clonar o repositório na VPS em `/srv/profsol/current`.
2. Copiar `.env.production.example` para `/etc/profsol/profsol.env` e preencher os segredos.
   Preencha também as variáveis `POSTGRES_*` para apontar para o PostgreSQL da VPS.
3. Instalar `uv`, `python3.12`, `nginx` e dependências de build do sistema.
4. Rodar:

```bash
cd /srv/profsol/current
export UV_CACHE_DIR=/srv/profsol/current/.uv-cache
uv sync
DJANGO_SETTINGS_MODULE=config.settings.production uv run python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.production uv run python manage.py collectstatic --noinput
DJANGO_SETTINGS_MODULE=config.settings.production uv run python manage.py createsuperuser
```

## PostgreSQL

Exemplo para criar banco e usuário locais:

```bash
sudo -u postgres psql
```

Dentro do `psql`:

```sql
CREATE DATABASE profsol;
CREATE USER profsol WITH PASSWORD 'troque-esta-senha';
ALTER ROLE profsol SET client_encoding TO 'utf8';
ALTER ROLE profsol SET default_transaction_isolation TO 'read committed';
ALTER ROLE profsol SET timezone TO 'America/Sao_Paulo';
GRANT ALL PRIVILEGES ON DATABASE profsol TO profsol;
\q
```

5. Copiar `deploy/systemd/profsol.service` para `/etc/systemd/system/profsol.service`.
6. Copiar `deploy/nginx/profsol.moven.cloud.conf` para `/etc/nginx/sites-available/profsol.moven.cloud`.
7. Criar o symlink em `sites-enabled`.
8. Testar `nginx -t`.
9. Ativar e iniciar o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable profsol
sudo systemctl start profsol
sudo systemctl restart nginx
```

10. Emitir SSL com Let's Encrypt ou usar o SSL gerenciado da sua infraestrutura.

## DNS

No painel DNS, aponte `profsol.moven.cloud` para o IP público da sua VPS.

## Arquivos importantes

- `config.settings.production`
- `deploy/systemd/profsol.service`
- `deploy/nginx/profsol.moven.cloud.conf`
- `deploy/scripts/deploy.sh`

## Mercado Pago e webhooks

No Mercado Pago, cadastre o webhook público:

`https://profsol.moven.cloud/checkout/mercado-pago/notificacoes/`

## E-mail

Como a entrega dos PDFs depende de e-mail, valide antes:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production uv run python manage.py shell
```

Depois envie um teste com `send_mail`.
