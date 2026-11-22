"""Triagem técnica de arquivos HISTÓRICOS DECLARADOS — nunca autenticação B3."""
from __future__ import annotations

from datetime import datetime
import hashlib
import io

import pandas as pd

from engine import BRT, HOLIDAYS_2026, contract_expiry, validate_win_candles

MAX_CSV_BYTES = 15_000_000


def missing_trading_days(data: pd.DataFrame) -> list[str]:
    """Verifica buracos de DIAS entre 2 pregões do arquivo, além dos gaps intradiários.

    Restringe ao calendário conhecido de 2026. Fechamento excepcional não
    codificado exige revisão manual do calendário oficial; falha por segurança.
    """
    if data.empty:
        raise ValueError('A amostra histórica está vazia.')
    found = set(data['datetime'].dt.date)
    start, end = min(found), max(found)
    days = pd.bdate_range(start=start, end=end)
    return [d.date().isoformat() for d in days
            if d.date() not in HOLIDAYS_2026 and d.date() not in found]


def inspect_historical_csv(payload: bytes, provider: str, contract: str, filename: str,
                           as_of=None) -> tuple[pd.DataFrame, dict]:
    """Valida integridade estrutural + declaração; não verifica cotações externas.

    Um fornecedor 'declarado' nunca é promovido para fonte 'autenticada'.
    """
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_CSV_BYTES:
        raise ValueError('Envie um CSV não vazio com até 15 MB.')
    if not isinstance(provider, str) or len(provider.strip()) < 3 or len(provider) > 150:
        raise ValueError('Indique o fornecedor do histórico (mínimo 3 caracteres).')
    if not isinstance(contract, str):
        raise ValueError('Informe um contrato WIN específico, como WINZ26.')
    contract = contract.strip().upper()
    expiry = contract_expiry(contract)
    if expiry.year != 2026:
        raise ValueError('Somente contratos de 2026: calendário de outros anos não verificado.')
    try:
        raw = pd.read_csv(io.BytesIO(payload), encoding='utf-8-sig')
    except (UnicodeError, pd.errors.ParserError, ValueError) as err:
        raise ValueError('CSV não pôde ser interpretado. Use UTF-8 com vírgulas e cabeçalho padrão.') from err
    cleaned = validate_win_candles(raw, require_complete_sessions=True, contract=contract)
    now = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp(datetime.now(BRT)).tz_localize(None)
    if now.tzinfo is not None:
        now = now.tz_convert(BRT).tz_localize(None)
    if cleaned['datetime'].max() + pd.Timedelta(minutes=5) > now:
        raise ValueError('O CSV contém candle posterior ao instante atual; não é histórico fechado.')
    missing = missing_trading_days(cleaned)
    if missing:
        shown = ', '.join(missing[:6])
        raise ValueError('Há pregões inteiros ausentes entre o primeiro e último arquivo: '
                         + shown + ('…' if len(missing) > 6 else '') + '. Exporte uma sequência contínua.')
    symbol_cols = [c for c in ('symbol', 'ticker', 'ativo', 'contract', 'contrato') if c in cleaned]
    warnings = [
        'O SHA-256 registra o arquivo recebido, mas não comprova que preços foram negociados na B3.',
        'A identidade do fornecedor foi declarada por quem fez o envio; sem consulta independente à fonte.',
        'Verifique licença, ajustes, rolagem, horários e se houve suspensões excepcionais da B3.',
        'Candles de 5 minutos não revelam a ordem dos toques intrabar, fila, liquidez ou execução real.',
    ]
    if not symbol_cols:
        warnings.append('O CSV não contém coluna de ticker; o contrato foi apenas DECLARADO e não conferido nas linhas.')
    if 'volume' not in cleaned:
        warnings.append('Volume ausente: filtros de volume usam apenas o comportamento previsto pelo motor para ausência de volume.')
    coverage = cleaned.groupby(cleaned.datetime.dt.date).size()
    info = {
        'classificacao': 'CSV_HISTORICO_DECLARADO_NAO_AUTENTICADO',
        'origem_verificada_independentemente': False,
        'nome_arquivo': str(filename)[:180],
        'fonte_declarada': provider.strip(),
        'contrato_declarado': contract,
        'ticker_presente_no_csv': bool(symbol_cols),
        'sha256': hashlib.sha256(payload).hexdigest(),
        'ano_calendario_validado': 2026,
        'fuso_interpretado': 'America/Sao_Paulo',
        'timestamp_representa': 'ABERTURA de candle de 5 minutos',
        'primeiro_candle': str(cleaned.datetime.min()),
        'ultimo_candle': str(cleaned.datetime.max()),
        'candles': int(len(cleaned)),
        'pregoes_completos': int(coverage.size),
        'pregoes_inteiros_ausentes': 0,
        'linhas_por_dia': dict((str(d),int(n)) for d,n in coverage.items()),
        'avisos': warnings,
    }
    return cleaned, info
