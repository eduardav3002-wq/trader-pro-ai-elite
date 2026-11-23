"""Trader Pro AI Elite v2.7 — Smart Alerts, interface de PESQUISA.

Nao envia push ao Android, nao desenha sobre aplicativos terceiros e nao
recebe cotacoes. Os alertas de COMPRA/VENDA desta versao sao APENAS DEMO.
A funcao de elegibilidade para um futuro feed falha fechada.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BRT = ZoneInfo('America/Sao_Paulo')
VALID_STATUSES = frozenset({'COMPRA', 'VENDA', 'AGUARDAR', 'NAO_OPERAR'})
DEMO_SCENARIOS = {
    'COMPRA': ('COMPRA', 'Filtros alinhados na simulação; nenhuma ordem será enviada.'),
    'VENDA': ('VENDA', 'Filtros alinhados na simulação; nenhuma ordem será enviada.'),
    'AGUARDAR': ('AGUARDAR', 'Condições insuficientes; aguardar o próximo candle.'),
    'NÃO OPERAR · risco': ('NAO_OPERAR', 'Orçamento diário de risco insuficiente.'),
    'NÃO OPERAR · dados antigos': ('NAO_OPERAR', 'Cotação vencida: decisão bloqueada.'),
    'NÃO OPERAR · sessão fechada': ('NAO_OPERAR', 'Fora do pregão autorizado da B3.'),
}


@dataclass(frozen=True)
class SmartAlert:
    status: str
    reason: str
    event_id: str
    occurred_at: datetime
    expires_at: datetime
    mode: str = 'DEMONSTRACAO'
    contract: str = 'WINZ26'

    def __post_init__(self):
        if self.status not in VALID_STATUSES:
            raise ValueError('Status invalido.')
        if not self.event_id or not self.reason:
            raise ValueError('Evento incompleto.')
        if self.occurred_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError('Carimbo de tempo deve conter fuso.')
        if self.expires_at <= self.occurred_at:
            raise ValueError('Prazo de validade invalido.')
        if self.mode not in {'DEMONSTRACAO', 'FEED_AUTORIZADO'}:
            raise ValueError('Modo invalido.')


def now_brt() -> datetime:
    return datetime.now(tz=BRT)


def default_alert(now: datetime | None = None) -> SmartAlert:
    now = now or now_brt()
    return SmartAlert('NAO_OPERAR', 'Sem feed autorizado ao vivo. Nenhuma entrada habilitada.',
                      'sem_feed', now, now + timedelta(days=365), mode='DEMONSTRACAO')


def demo_alert(scenario: str, now: datetime | None = None, ttl_seconds: int = 60) -> SmartAlert:
    if scenario not in DEMO_SCENARIOS:
        raise ValueError('Cenario de demonstracao desconhecido.')
    if not 5 <= ttl_seconds <= 300:
        raise ValueError('Duracao demo fora de limites.')
    now = now or now_brt()
    state, reason = DEMO_SCENARIOS[scenario]
    return SmartAlert(state, reason, f'demo:{scenario}', now,
                      now + timedelta(seconds=ttl_seconds), mode='DEMONSTRACAO')


def effective_alert(alert: SmartAlert, now: datetime | None = None) -> SmartAlert:
    now = now or now_brt()
    if now >= alert.expires_at:
        return SmartAlert('NAO_OPERAR', 'Alerta expirado. Sem feed autorizado ao vivo.',
                          'demo_expirou', now, now + timedelta(days=365),
                          mode='DEMONSTRACAO')
    return alert


def should_notify(last_event_id: str | None, alert: SmartAlert) -> bool:
    """Nao repetir avisos identicos. Somente o estado inicial sem feed e silencioso."""
    if alert.event_id == 'sem_feed':
        return False
    return alert.event_id != last_event_id


def eligible_live_candidate(*, proposed: str, feed_authorized: bool,
                            quote_verified: bool, quote_at: datetime | None,
                            now: datetime, candle_completed: bool,
                            calendar_open: bool, session_open: bool,
                            risk_permitted: bool, max_age_seconds: int = 20) -> tuple[str, str]:
    """Preparacao para futura integracao, SEM feed na v2.7.

    Nunca autorizar sinal de entrada se algum requisito estiver faltando.
    Retorna apenas um ESTADO INFORMATIVO, nao ordem/decisao automatica.
    """
    if proposed not in VALID_STATUSES:
        raise ValueError('Status invalido.')
    if now.tzinfo is None:
        raise ValueError('Horario de referencia sem fuso.')
    if not feed_authorized or not quote_verified:
        return ('NAO_OPERAR', 'Feed ao vivo ausente ou nao autenticado.')
    if quote_at is None or quote_at.tzinfo is None:
        return ('NAO_OPERAR', 'Carimbo da cotacao invalido.')
    age = (now - quote_at).total_seconds()
    if age < 0 or age > max_age_seconds:
        return ('NAO_OPERAR', 'Cotacao desatualizada ou com horario futuro.')
    if not candle_completed:
        return ('NAO_OPERAR', 'Candle ainda nao fechado.')
    if not calendar_open or not session_open:
        return ('NAO_OPERAR', 'Fora da sessao de negociacao validada.')
    if not risk_permitted:
        return ('NAO_OPERAR', 'Orcamento de risco insuficiente.')
    if proposed == 'AGUARDAR':
        return ('AGUARDAR', 'Sem sinal confirmado.')
    if proposed == 'NAO_OPERAR':
        return ('NAO_OPERAR', 'Filtro preventivo da estrategia.')
    return (proposed, 'Candidato informativo; requer confirmacao manual e validacao independente.')
