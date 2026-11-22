"""Trader Pro AI Elite v0.8: motor de OHLC do WIN preservado da v0.7, sem ordens reais.

A validação da grade de preço e dos horários é deliberadamente estrita.
Horários-base são os da B3 para 2026-11; feriados de 2026 são conferidos,
mas outros anos, vencimentos e leilões precisam de calendário oficial.
"""
from datetime import datetime, time
import re
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

TICK = 5.0
BRT = ZoneInfo("America/Sao_Paulo")
SESSION_START = time(9, 0)
LAST_OPEN = time(18, 20)  # candle 18:20–18:25; encerramento normal 18:25
ENTRY_CUTOFF = time(17, 55)  # última abertura permitida no backtest
# Calendário específico de 2026, conforme notícia/calendário oficial da B3.
# Outros anos NÃO são verificados quanto aos feriados por este protótipo.
HOLIDAYS_2026 = frozenset(pd.Timestamp(x).date() for x in (
    '2026-01-01', '2026-02-16', '2026-02-17', '2026-04-03',
    '2026-04-21', '2026-05-01', '2026-06-04', '2026-09-07',
    '2026-10-12', '2026-11-02', '2026-11-20',
    '2026-12-24', '2026-12-25', '2026-12-31'))
SPECIAL_OPEN_2026 = {pd.Timestamp('2026-02-18').date(): time(13,0)}
REQUIRED = ("datetime", "open", "high", "low", "close")
CONTRACT_MONTHS = {"G": 2, "J": 4, "M": 6, "Q": 8, "V": 10, "Z": 12}


def contract_expiry(contract):
    """Retorna vencimento nominal; calendário oficial precisa confirmar exceções."""
    name = str(contract or "").strip().upper()
    match = re.fullmatch(r"WIN([GJMQVZ])(\d{2})", name)
    if not match:
        raise ValueError("Informe o contrato real, no formato WINZ26 (não use WIN contínuo).")
    year = 2000 + int(match.group(2))
    month = CONTRACT_MONTHS[match.group(1)]
    day = min((pd.Timestamp(year, month, 15 + d).date()
               for d in range(-3, 4)
               if pd.Timestamp(year, month, 15 + d).weekday() == 2),
              key=lambda d: abs(d.day - 15))
    return day


def session_bounds(day, contract=None):
    """Grade normal 2026; no vencimento do contrato, seu pregão acaba às 17h.

    Esta implementação NÃO conhece todas as exceções/calls. Por segurança,
    somente os dias de 2026 são aceitos pelo validador.
    """
    start = SPECIAL_OPEN_2026.get(day, SESSION_START)
    end = time(16, 55) if contract and day == contract_expiry(contract) else LAST_OPEN
    return start, end



ENTRY_GATE_LABELS = {
    'SEM_SINAL': 'Nenhum sinal de compra ou venda neste candle',
    'FERIADO_B3': 'Bloqueado: B3 sem negociação do WIN nesta data',
    'FIM_DE_SEMANA': 'Bloqueado: não há pregão de WIN aos sábados e domingos',
    'CALENDARIO_NAO_VALIDADO': 'Bloqueado: calendário da B3 ainda não validado para esse ano',
    'FORA_SESSAO': 'Bloqueado: candle fora da sessão regular/especial autorizada',
    'ELEGIVEL_HORARIO': 'Sinal com próxima abertura disponível dentro do horário',
    'HORARIO_TARDIO': 'A próxima abertura ultrapassa o horário-limite de entrada',
    'SEM_CANDLE_SEGUINTE': 'Próximo candle não disponível na mesma sessão',
    'DIA_VENCIMENTO': 'Sinais não podem gerar entradas no dia do vencimento',
}


def market_day_gate(when):
    """Falha fechada: sem calendário confirmado, SEM tentativa de negociação.

    Para 2026 utiliza a tabela publicada pela B3 para derivativos listados.
    Não confundir feriado dos EUA com feriado brasileiro da B3.
    """
    when = pd.Timestamp(when)
    day = when.date()
    if day.year != 2026:
        return 'CALENDARIO_NAO_VALIDADO'
    if day.weekday() >= 5:
        return 'FIM_DE_SEMANA'
    if day in HOLIDAYS_2026:
        return 'FERIADO_B3'
    return None


def signal_entry_gate(signal, signal_dt, next_dt=None, contract=None):
    """Gate único para elegibilidade de calendário, horário e próximo candle.

    NÃO examina gestão de risco nem autoriza ordem real. Repetido no backtest.
    """
    if signal not in ('COMPRA', 'VENDA'):
        return 'SEM_SINAL'
    signal_dt = pd.Timestamp(signal_dt)
    target = signal_dt + pd.Timedelta(minutes=5)
    for when in (signal_dt, target):
        block = market_day_gate(when)
        if block:
            return block
    if contract and signal_dt.date() == contract_expiry(contract):
        return 'DIA_VENCIMENTO'
    open_time, last_time = session_bounds(target.date(),contract)
    if (signal_dt.time() < open_time or signal_dt.time() > last_time
            or target.time() < open_time or target.time() > last_time):
        return 'FORA_SESSAO'
    if target.time() > ENTRY_CUTOFF or target.date() != signal_dt.date():
        return 'HORARIO_TARDIO'
    if next_dt is None or pd.Timestamp(next_dt) != target:
        return 'SEM_CANDLE_SEGUINTE'
    return 'ELEGIVEL_HORARIO'


def _normalize_columns(df):
    aliases = {
        'data': 'datetime', 'datahora': 'datetime', 'data_hora': 'datetime',
        'timestamp': 'datetime', 'date': 'datetime',
        'abertura': 'open', 'maxima': 'high', 'máxima': 'high',
        'minima': 'low', 'mínima': 'low', 'fechamento': 'close',
        'volume_financeiro': 'volume'
    }
    out = df.copy()
    out.columns = [aliases.get(str(c).strip().lower(), str(c).strip().lower()) for c in out.columns]
    if out.columns.duplicated().any():
        raise ValueError('Colunas duplicadas após a normalização.')
    return out


def _parse_brt(value):
    dt = pd.to_datetime(value, errors='raise')
    if pd.isna(dt):
        raise ValueError('Data vazia.')
    # CSV sem fuso: a aplicação exige a convenção declarada de horário de Brasília.
    if dt.tzinfo is None:
        return dt.to_pydatetime()
    return dt.tz_convert(BRT).tz_localize(None).to_pydatetime()


def validate_win_candles(data, min_rows=80, require_complete_sessions=False, contract=None):
    """Valida e devolve OHLC de candles *abertos* a cada 5 min, horário de Brasília.

    Falha se o CSV contiver preços fracionários fora do tick, horário incorreto,
    OHLC inconsistente ou lacunas intradiárias. Nunca ajusta dados inválidos.
    require_complete_sessions=True é obrigatório para backtests comparáveis.
    """
    if not isinstance(data, pd.DataFrame):
        raise ValueError('Dados devem ser fornecidos em tabela CSV.')
    if contract is not None:
        expiry = contract_expiry(contract)
        if expiry.year != 2026:
            raise ValueError('Esta versão valida o calendário somente de 2026; aguarde um calendário oficial para outros anos.')
    else:
        expiry = None
    df = _normalize_columns(data)
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError('CSV de CANDLES obrigatório: datetime,open,high,low,close. Colunas ausentes: ' + ', '.join(sorted(missing)))
    # Se o fornecedor exportar código do ativo, ele precisa coincidir com a
    # declaração do usuário. Sem a coluna, a declaração NÃO é verificada.
    if contract is not None:
        for symbol_col in ('symbol', 'ticker', 'ativo', 'contract', 'contrato'):
            if symbol_col in df:
                symbols = df[symbol_col].astype('string').str.strip().str.upper()
                if (symbols.isna() | symbols.ne(contract.strip().upper())).fillna(True).any():
                    raise ValueError(f'Coluna {symbol_col} não corresponde ao contrato declarado {contract.upper()} em todas as linhas.')
    if len(df) < min_rows:
        raise ValueError(f'São necessários pelo menos {min_rows} candles de 5 minutos; recebidos {len(df)}.')
    try:
        df['datetime'] = pd.to_datetime([_parse_brt(v) for v in df['datetime']])
    except (ValueError, TypeError, OverflowError) as ex:
        raise ValueError(f'Datas inválidas ou fuso inconsistente: {ex}') from ex
    if df['datetime'].isna().any():
        raise ValueError('Existem timestamps vazios.')
    if df['datetime'].duplicated().any():
        raise ValueError('Existem candles com data/hora duplicadas.')
    if not df['datetime'].is_monotonic_increasing:
        raise ValueError('Ordene cronologicamente os candles (do mais antigo ao mais recente).')
    for c in ('open','high','low','close'):
        df[c] = pd.to_numeric(df[c], errors='coerce')
        if df[c].isna().any() or (~np.isfinite(df[c])).any() or (df[c] <= 0).any():
            raise ValueError(f'A coluna {c} contém valores inválidos ou não positivos.')
        off_tick = np.abs(df[c].to_numpy(dtype=float) / TICK - np.round(df[c].to_numpy(dtype=float) / TICK)) > 1e-7
        if off_tick.any():
            row = int(np.where(off_tick)[0][0]) + 2
            raise ValueError(f'Preço fora do tick de 5 pontos em {c}, linha {row}: {df[c].iloc[row-2]:.2f}. Dados rejeitados, sem arredondar.')
    if (df.high < df[['open','close','low']].max(axis=1)).any() or (df.low > df[['open','close']].min(axis=1)).any():
        raise ValueError('Existem candles com máxima/mínima inconsistentes com abertura e fechamento.')
    if (df.datetime.dt.year != 2026).any():
        raise ValueError('Esta versão conhece apenas o calendário B3 de 2026. Outros anos estão bloqueados por segurança.')
    if expiry and (df.datetime.dt.date > expiry).any():
        raise ValueError(f'O contrato {contract.upper()} vence em {expiry}; há candles posteriores ao vencimento.')
    if (df.datetime.dt.dayofweek >= 5).any():
        raise ValueError('CSV tem candles em sábado/domingo. Dados rejeitados.')
    on_holiday = df.datetime.dt.date.map(lambda d: d in HOLIDAYS_2026)
    if on_holiday.any():
        date = df.datetime.loc[on_holiday].iloc[0].date()
        raise ValueError(f'Não houve pregão regular WIN no feriado da B3: {date}. Dados rejeitados.')
    times = df.datetime.dt.time
    invalid_time = ~df.datetime.map(
        lambda dt: (session_bounds(dt.date(), contract)[0] <= dt.time()
                    <= session_bounds(dt.date(), contract)[1]
                    and dt.minute % 5 == 0 and dt.second == 0))
    if invalid_time.any():
        idx = int(np.where(invalid_time.to_numpy())[0][0])
        raise ValueError(f'Horário inválido para candle WIN em Brasília: {df.datetime.iloc[idx]} (linha {idx+2}).')
    delta = df.datetime.diff()
    same_day = df.datetime.dt.normalize().eq(df.datetime.dt.normalize().shift())
    gaps = same_day & delta.ne(pd.Timedelta(minutes=5))
    if gaps.any():
        idx = int(np.where(gaps.to_numpy())[0][0])
        raise ValueError(f'Falha ou salto de candles dentro do pregão, entre {df.datetime.iloc[idx-1]} e {df.datetime.iloc[idx]}.')
    if require_complete_sessions:
        for day, session in df.groupby(df.datetime.dt.date):
            start, last = session_bounds(day, contract)
            if (session.datetime.iloc[0].time() != start
                    or session.datetime.iloc[-1].time() != last):
                raise ValueError(
                    f'Pregão incompleto em {day}: é necessário CSV desde {start:%H:%M} '
                    f'até {last:%H:%M} (candles de abertura). Exporte dias completos '
                    'para evitar saídas artificiais no fim dos dados.')
    return df.reset_index(drop=True)


def demo_data(days=4, seed=27):
    """OHLC *totalmente fictício*, mas conforme a grade técnica de candles WIN."""
    if days < 1 or days > 30:
        raise ValueError('days deve estar entre 1 e 30.')
    rng = np.random.default_rng(seed)
    candidates = pd.bdate_range(end='2026-11-19', periods=days+16)
    dates = [d for d in candidates if d.date() not in HOLIDAYS_2026][-days:]
    rows = []
    previous = 128000.0
    for day in dates:
        previous = round((previous + float(rng.integers(-12,13)) * TICK)/TICK)*TICK
        for slot in range(113):  # 09:00, 09:05 ... 18:20
            when = day + pd.Timedelta(hours=9, minutes=5*slot)
            opening = previous
            delta = float(rng.choice([-7,-5,-3,-2,-1,0,1,2,3,5,7])) * TICK
            closing = opening + delta
            high = max(opening,closing) + float(rng.integers(0,4)) * TICK
            low = min(opening,closing) - float(rng.integers(0,4)) * TICK
            rows.append({'datetime':when, 'open':opening, 'high':high,
                         'low':low, 'close':closing, 'volume':int(rng.integers(20,2000))})
            previous = closing
    return pd.DataFrame(rows)


REASON_LABELS = {
    'AQUECIMENTO': 'Histórico insuficiente para calcular os filtros com segurança',
    'SEM_CONFIRMACAO_15M': 'Tendência de 15 minutos ainda não confirmada',
    'ATR_INVALIDO': 'Volatilidade indisponível ou nula',
    'VOLATILIDADE_BAIXA': 'Volatilidade abaixo da faixa exploratória',
    'VOLATILIDADE_ALTA': 'Volatilidade acima da faixa exploratória',
    'CANDLE_EXTREMO': 'Candle grande demais em relação ao ATR',
    'LATERALIZACAO': 'Possível lateralização: médias próximas',
    'SEM_DIRECAO': 'Sem direção definida nas médias de 5 minutos',
    'TENDENCIAS_DIVERGENTES': 'Tendências de 5 e 15 minutos não concordam',
    'RSI_FORA': 'RSI fora da faixa escolhida para a direção',
    'SEM_ROMPIMENTO': 'Sem rompimento confirmado dos três candles anteriores',
    'FILTROS_COMPRA': 'Filtros exploratórios alinhados para compra',
    'FILTROS_VENDA': 'Filtros exploratórios alinhados para venda',
}


def analyze(data, contract=None, profile='seletivo'):
    """Gera sinais determinísticos, sempre com informações conhecidas no candle.

    'base' reproduz a regra v0.5; 'seletivo' acrescenta filtros exploratórios
    não otimizados em dados reais. Nenhum perfil implica acurácia conhecida.
    """
    if profile not in ('base', 'seletivo'):
        raise ValueError('Perfil inválido. Escolha base ou seletivo.')
    df = validate_win_candles(data, contract=contract)
    df['ema9'] = df.close.ewm(span=9, adjust=False).mean()
    df['ema21'] = df.close.ewm(span=21, adjust=False).mean()
    delta = df.close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rs = gains / losses.replace(0,np.nan)
    rsi = 100 - (100/(1+rs))
    df['rsi'] = rsi.mask(losses.eq(0) & gains.gt(0), 100).mask(losses.eq(0) & gains.eq(0),50)
    prev = df.close.shift()
    tr = pd.concat([df.high-df.low, (df.high-prev).abs(), (df.low-prev).abs()],axis=1).max(axis=1)
    df['atr'] = tr.rolling(14,min_periods=14).mean()
    df['trend'] = np.select([df.ema9>df.ema21,df.ema9<df.ema21],['ALTA','BAIXA'],default='NEUTRA')
    df['condition'] = np.where((df.ema9-df.ema21).abs()<df.atr*0.2,'POSSÍVEL LATERALIZAÇÃO','MOVIMENTO')

    # Confirmação 15m sem olhar futuro: cada bloco é publicado SOMENTE ao fechar
    # os três candles 5m; merge_asof usa o último fechamento de 15m já conhecido.
    grouped = df.set_index('datetime').resample('15min',label='right',closed='left').agg(
        close15=('close','last'),count15=('close','count'))
    grouped = grouped[grouped.count15.eq(3)].copy()
    grouped['ema9_15'] = grouped.close15.ewm(span=9,adjust=False,min_periods=21).mean()
    grouped['ema21_15'] = grouped.close15.ewm(span=21,adjust=False,min_periods=21).mean()
    grouped['trend15'] = np.select([grouped.ema9_15 > grouped.ema21_15,
                                     grouped.ema9_15 < grouped.ema21_15],['ALTA','BAIXA'],default='NEUTRA')
    grouped.loc[grouped.ema21_15.isna(), 'trend15'] = 'SEM CONFIRMAÇÃO'
    df['candle_close'] = df.datetime + pd.Timedelta(minutes=5)
    df = pd.merge_asof(df.sort_values('candle_close'),grouped[['trend15']].reset_index().rename(columns={'datetime':'bar15_close'}).sort_values('bar15_close'),
                       left_on='candle_close',right_on='bar15_close',direction='backward')
    df['trend15'] = df['trend15'].fillna('SEM CONFIRMAÇÃO')

    # Comparações usando o candle atual já fechado e apenas candles anteriores.
    prior_high = df.high.shift(1).rolling(3, min_periods=3).max()
    prior_low = df.low.shift(1).rolling(3, min_periods=3).min()
    df['atr_mediana60'] = df.atr.shift(1).rolling(60, min_periods=60).median()
    df['atr_ratio'] = df.atr / df.atr_mediana60.replace(0, np.nan)
    df['candle_atr'] = (df.high-df.low) / df.atr.replace(0, np.nan)
    has_trend = df.trend.isin(('ALTA', 'BAIXA'))
    agreeing = has_trend & df.trend15.eq(df.trend)
    rsi_ok = ((df.trend.eq('ALTA') & df.rsi.between(52, 67)) |
              (df.trend.eq('BAIXA') & df.rsi.between(33, 48)))
    breakout = ((df.trend.eq('ALTA') & df.close.gt(prior_high)) |
                (df.trend.eq('BAIXA') & df.close.lt(prior_low)))
    basic_ok = (df.atr.gt(0) & df.condition.eq('MOVIMENTO') & agreeing
                & rsi_ok & breakout)
    # Critérios demonstrativos de 0.65 a 1.8 vezes a mediana ATR anterior,
    # candle máximo de 2.2 ATR. NÃO calibrados nem validados em WIN real.
    regime_ok = df.atr_ratio.between(0.65, 1.8, inclusive='both')
    spike_ok = df.candle_atr.le(2.2)
    allowed = basic_ok if profile == 'base' else basic_ok & regime_ok & spike_ok
    df['signal'] = np.select(
        [allowed & df.trend.eq('ALTA'), allowed & df.trend.eq('BAIXA')],
        ['COMPRA', 'VENDA'], default='AGUARDAR')
    # O legado também exige o período inicial de 34 candles sem negociação.
    df.loc[:33, 'signal'] = 'AGUARDAR'
    warmup = (pd.Series(np.arange(len(df)), index=df.index) < (34 if profile == 'base' else 75))
    if profile == 'seletivo':
        df.loc[warmup, 'signal'] = 'AGUARDAR'
    # Todos os motivos de bloqueio são calculados independentemente.
    # O primeiro preserva o resumo antigo; a nova coluna guarda os demais.
    ordered_checks = [
        ('AQUECIMENTO', warmup),
        ('SEM_CONFIRMACAO_15M', df.trend15.eq('SEM CONFIRMAÇÃO')),
        ('ATR_INVALIDO', df.atr.isna() | df.atr.le(0)),
    ]
    if profile == 'seletivo':
        ordered_checks += [
            ('VOLATILIDADE_BAIXA', df.atr_ratio.lt(0.65)),
            ('VOLATILIDADE_ALTA', df.atr_ratio.gt(1.8)),
            ('CANDLE_EXTREMO', df.candle_atr.gt(2.2)),
        ]
    ordered_checks += [
        ('LATERALIZACAO', df.condition.eq('POSSÍVEL LATERALIZAÇÃO')),
        ('SEM_DIRECAO', ~has_trend),
        ('TENDENCIAS_DIVERGENTES', has_trend & df.trend15.ne('SEM CONFIRMAÇÃO') & ~agreeing),
        ('RSI_FORA', has_trend & ~rsi_ok),
        ('SEM_ROMPIMENTO', has_trend & ~breakout),
    ]
    checks_as_arrays = [(code, series.fillna(False).to_numpy(dtype=bool))
                        for code, series in ordered_checks]
    reasons=[]
    for rowidx, signal in enumerate(df['signal']):
        if signal in ('COMPRA','VENDA'):
            reasons.append(['FILTROS_COMPRA' if signal == 'COMPRA' else 'FILTROS_VENDA'])
        else:
            matches=[code for code, mask in checks_as_arrays if mask[rowidx]]
            # Toda decisão de espera deve ser explicável.
            reasons.append(matches or ['SEM_ROMPIMENTO'])
    df['all_reason_codes'] = [' | '.join(codes) for codes in reasons]
    df['all_reason_details'] = [' | '.join(REASON_LABELS[code] for code in codes)
                                for codes in reasons]
    df['reason_code'] = [codes[0] for codes in reasons]
    df['reason_detail'] = df.reason_code.map(REASON_LABELS)
    df['profile'] = profile

    # "Candidato" não é ordem executada nem garantia de disponibilidade real.
    next_dates = df.datetime.shift(-1)
    gates = [signal_entry_gate(signal, dt,
              None if pd.isna(next_dates.iat[i]) else next_dates.iat[i],contract)
              for i,(signal,dt) in enumerate(zip(df.signal,df.datetime))]
    df['entry_gate_code'] = gates
    df['entry_gate_detail'] = df.entry_gate_code.map(ENTRY_GATE_LABELS)
    df['signal_eligible'] = df.signal.where(df.entry_gate_code.eq('ELEGIVEL_HORARIO'),'AGUARDAR')
    df['expected_entry_time'] = df.datetime + pd.Timedelta(minutes=5)
    df['stop'] = np.where(df.signal.eq('COMPRA'),np.floor((df.close - 1.5*df.atr)/TICK)*TICK,
                   np.where(df.signal.eq('VENDA'),np.ceil((df.close+1.5*df.atr)/TICK)*TICK,np.nan))
    df['target'] = np.where(df.signal.eq('COMPRA'),np.ceil((df.close+2*df.atr)/TICK)*TICK,
                     np.where(df.signal.eq('VENDA'),np.floor((df.close-2*df.atr)/TICK)*TICK,np.nan))
    return df.reset_index(drop=True)
