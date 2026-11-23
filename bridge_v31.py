"""Ponte de alertas exclusivamente de DEMONSTRAÇÃO Streamlit -> Supabase REST.

NUNCA publica cotações, decisões reais ou ordens. Sem credenciais, falha fechado.
A chave SECRET fica no servidor Streamlit; Android usa apenas publishable (read-only).
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib import request, error

CHANNEL = "trader-demo-v31"
TABLE = "trader_demo_alert_v31"
STATUSES = ("COMPRA", "VENDA", "AGUARDAR", "NAO_OPERAR")
AUTO_CYCLE = ("COMPRA", "AGUARDAR", "VENDA", "NAO_OPERAR")
DESCRIPTIONS = {
    "COMPRA": "SIMULAÇÃO AUTOMÁTICA: compra fictícia. NÃO USE PARA OPERAR.",
    "VENDA": "SIMULAÇÃO AUTOMÁTICA: venda fictícia. NÃO USE PARA OPERAR.",
    "AGUARDAR": "SIMULAÇÃO AUTOMÁTICA: sem condições de entrada.",
    "NAO_OPERAR": "DEMONSTRAÇÃO: sem feed autorizado de mercado.",
}


@dataclass(frozen=True)
class BridgeConfig:
    url: str
    secret_key: str


def project_url(raw: str) -> str:
    """Recusa URLs não HTTPS e domínios que não sejam projetos Supabase."""
    url = str(raw).strip().rstrip("/").lower()
    if not re.fullmatch(r"https://[a-z0-9-]{8,64}\.supabase\.co", url):
        raise ValueError("Use somente https://SEU-PROJETO.supabase.co")
    return url


def valid_config(config: BridgeConfig) -> BridgeConfig:
    project_url(config.url)
    if not config.secret_key.startswith('sb_secret_') or len(config.secret_key) < 24:
        raise ValueError("Chave secret de servidor não configurada.")
    return config


def make_event(status: str, now: datetime | None = None) -> dict:
    if status not in STATUSES:
        raise ValueError("Estado de demonstração inválido.")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Horário sem fuso.")
    now = now.astimezone(timezone.utc)
    return {
        "channel_id": CHANNEL,
        "event_id": str(uuid.uuid4()),
        "status": status,
        "issued_at": now.isoformat(timespec="seconds").replace('+00:00', 'Z'),
        "expires_at": (now + timedelta(seconds=45)).isoformat(timespec="seconds").replace('+00:00', 'Z'),
        "mode": "DEMONSTRACAO",
        "contract": "WINZ26",
    }


def publish_demo(config: BridgeConfig, status: str, *, opener=None, now=None) -> dict:
    """Publica UM estado fictício no canal; só é chamado com controle autenticado."""
    cfg = valid_config(config)
    event = make_event(status, now)
    endpoint = project_url(cfg.url) + '/rest/v1/' + TABLE + '?on_conflict=channel_id'
    payload = json.dumps(event, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    req = request.Request(endpoint, data=payload, method='POST', headers={
        'apikey': cfg.secret_key,
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates,return=minimal',
        'Cache-Control': 'no-store',
    })
    send = opener or request.urlopen
    try:
        with send(req, timeout=5) as response:
            if response.status not in (200, 201, 204):
                raise RuntimeError('Publicação recusada pelo servidor.')
    except (error.HTTPError, error.URLError, TimeoutError) as exc:
        # NÃO imprimir corpo de resposta ou URL com segredos.
        raise RuntimeError('Ponte indisponível; nenhuma mensagem publicada.') from exc
    return event
