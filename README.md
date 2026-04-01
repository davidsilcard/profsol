# Prof. Sol Tricô & Crochê

Projeto Django para um site com:

- Home institucional em tons pastel
- Vídeos importados do canal do YouTube
- Catálogo de receitas digitais em PDF
- Login e área da cliente
- Checkout preparado para Mercado Pago com Pix e cartão
- Liberação de download e envio por e-mail após pagamento aprovado
- Estrutura pronta para deploy na VPS com subdomínio próprio

## Stack

- Python 3.12
- Django 5.2
- Gunicorn
- SQLite no desenvolvimento local
- PostgreSQL recomendado em produção
- Requests para integrações externas

## Como rodar

1. Sincronize o ambiente com `uv`:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv sync
```

2. Copie `.env.example` para `.env` ou configure as variáveis no ambiente.
3. Rode as migrações:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python manage.py migrate
```

4. Crie um superusuário:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python manage.py createsuperuser
```

5. Suba o servidor:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python manage.py runserver
```

## Ambientes

- desenvolvimento: `config.settings.development`
- produção: `config.settings.production`

Para publicar na VPS, use `DJANGO_SETTINGS_MODULE=config.settings.production`.
Em produção, configure também `DB_ENGINE=postgres` e as variáveis `POSTGRES_*`.

## Fluxo de conteúdo

- `Home`: apresentação da professora e resumo das abas.
- `Vídeos`: importação do canal da professora e agrupamento por tema.
- `Receitas`: catálogo com valor, capa, descrição e checkout.
- `Minha conta`: histórico e downloads liberados.

## Painel admin

Cadastre pelo admin:

- conteúdo institucional do site
- temas de vídeo
- receitas com capa e PDF
- acompanhamento dos pedidos

## Sincronizar vídeos do YouTube

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python manage.py sync_youtube_videos
```

Os vídeos são importados do canal configurado em `YOUTUBE_CHANNEL_URL`. Depois disso, você pode organizar cada vídeo por tema no admin.

## Pagamentos

O checkout está preparado para `Mercado Pago Checkout Pro`, que permite Pix e cartão sem capturar dados do cartão diretamente no site.

Para ativar:

- configure `MERCADO_PAGO_ACCESS_TOKEN`
- configure `SITE_URL` com a URL real do site
- cadastre a rota de webhook publicada em `/checkout/mercado-pago/notificacoes/`

## Entrega das receitas

Quando um pagamento é aprovado:

- a receita é liberada na área logada
- o PDF pode ser baixado
- um e-mail é enviado para a cliente

## Deploy na VPS

Os arquivos de deploy estão em:

- `deploy/nginx/profsol.moven.cloud.conf`
- `deploy/systemd/profsol.service`
- `deploy/scripts/deploy.sh`
- `deploy/DEPLOY.md`

O alvo preparado é o subdomínio:

- `https://profsol.moven.cloud/`
