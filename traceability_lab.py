"""v1.4: rastreabilidade de SERIE DECLARADA, exclusivamente descritiva.

Mapas opcionais do usuario NAO provam ticker, rolagem, origem primaria ou ajustes.
Nenhum dado deste modulo vai para geracao de sinal, backtest ou corretora.
"""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
import hashlib
import re

import pandas as pd

MAX_MAP_BYTES = 512_000
MAX_MAP_ROWS = 500
MONTH_CODE = {'G': 2, 'J': 4, 'M': 6, 'Q': 8, 'V': 10, 'Z': 12}
REQUIRED_MAP_COLUMNS = {'inicio', 'fim', 'contrato', 'documento'}
EMPTY_TEMPLATE = 'inicio,fim,contrato,documento\n'.encode('utf-8-sig')


def nominal_expiry(ticker: str) -> date:
    """Data teorica: quarta mais proxima do dia 15, sem ajuste de feriados.

    Nao confere listagem real do instrumento, ultimo pregao, suspensoes ou
    regras historicas excepcionais. Ano de dois digitos = 20YY somente.
    """
    name = str(ticker).strip().upper()
    match = re.fullmatch(r'WIN([GJMQVZ])(\d{2})', name)
    if not match:
        raise ValueError('Contrato inválido: use WIN + G/J/M/Q/V/Z + ano, ex.: WINZ19.')
    month = MONTH_CODE[match.group(1)]
    year = 2000 + int(match.group(2))
    options = [date(year, month, n) for n in range(12, 19)
               if date(year, month, n).weekday() == 2]
    return min(options, key=lambda x: abs(x.day-15))


def read_contract_map(payload: bytes) -> tuple[pd.DataFrame, str]:
    """Lê um mapa opcional de contratos ALEGADOS por intervalo de dias.

    Valida somente sintaxe, consistência e unicidade de datas. Nunca autentica
    a fonte nem marca o ticker como negociado de fato.
    """
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_MAP_BYTES:
        raise ValueError('Mapa não vazio necessário; tamanho máximo 512 KB.')
    try:
        frame = pd.read_csv(BytesIO(payload), encoding='utf-8-sig', keep_default_na=False, dtype=str)
    except (UnicodeError, ValueError, pd.errors.ParserError) as exc:
        raise ValueError('Mapa CSV inválido ou ilegível.') from exc
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    if (not REQUIRED_MAP_COLUMNS.issubset(frame.columns) or frame.columns.duplicated().any()
        or frame.empty or len(frame) > MAX_MAP_ROWS):
        raise ValueError('Mapa precisa de 1 a 500 linhas e colunas inicio,fim,contrato,documento.')
    frame = frame[['inicio','fim','contrato','documento']].copy()
    for col in ['inicio','fim','contrato','documento']:
        frame[col] = frame[col].astype(str).str.strip()
    for col in ['inicio','fim']:
        try:
            if any(re.fullmatch(r'\d{4}-\d{2}-\d{2}', x) is None for x in frame[col]):
                raise ValueError('Formato de data inválido.')
            parsed = [datetime.strptime(x, '%Y-%m-%d').date() for x in frame[col]]
        except ValueError as exc:
            raise ValueError('Datas do mapa precisam seguir AAAA-MM-DD, sem horário.') from exc
        if any(not 2019 <= x.year <= 2020 for x in parsed):
            raise ValueError('Mapa restrito ao histórico de 2019–2020.')
        frame[col] = [x.isoformat() for x in parsed]
    frame['contrato'] = frame['contrato'].str.upper()
    for contract in frame.contrato:
        nominal_expiry(contract)
    if any(a > b for a,b in zip(frame.inicio,frame.fim)):
        raise ValueError('Início após fim no mapa de contratos.')
    if any(len(x) > 300 for x in frame.documento):
        raise ValueError('Documento/referência longo demais (limite 300 caracteres).')
    if any(re.match(r'^[=+@\-\t\r]', x) for x in frame.documento):
        raise ValueError('Referência não pode começar com fórmula de planilha (=, +, -, @).')
    if any(any(ord(ch) < 32 for ch in x) for x in frame.documento):
        raise ValueError('Referência contém caractere de controle não permitido.')
    frame = frame.sort_values(['inicio','fim']).reset_index(drop=True)
    for idx in range(1,len(frame)):
        if frame.loc[idx,'inicio'] <= frame.loc[idx-1,'fim']:
            raise ValueError('Intervalos sobrepostos no mapa; cada data pode ter apenas um contrato declarado.')
    return frame, hashlib.sha256(payload).hexdigest()


def traceability_audit(daily: pd.DataFrame, integrity_days: pd.DataFrame,
                       origin_report: dict, contract_map: pd.DataFrame | None = None,
                       map_sha256: str | None = None):
    """Retorna (dias, transicoes, pendencias, dossier), tudo NAO CERTIFICADO.

    Mapa, mesmo com URL de documento, serve apenas para registrar alegacoes
    revisaveis. Nenhuma comparacao de precos usa ticker assumido como fato.
    """
    if not isinstance(daily, pd.DataFrame) or not isinstance(integrity_days,pd.DataFrame):
        raise ValueError('Relatórios diários ausentes.')
    required_daily = {'dia','candles_5min','primeiro_candle','ultimo_candle',
                      'lacunas_internas','abertura_referencia'}
    if (daily.empty or not required_daily.issubset(daily.columns)
        or not {'dia','candles_5min','diferenca_entre_sessoes_pts','vencimento_nominal','avisos_investigacao'}.issubset(integrity_days.columns)):
        raise ValueError('Auditorias v1.3 incompletas para rastreabilidade.')
    d = daily.copy(); k = integrity_days.copy()
    for frame in (d,k):
        frame['dia'] = pd.to_datetime(frame.dia, format='%Y-%m-%d', errors='raise').dt.strftime('%Y-%m-%d')
        if frame.dia.duplicated().any() or frame.dia.isna().any():
            raise ValueError('Dias duplicados ou datas inválidas.')
    if (set(d.dia) != set(k.dia) or
        any(int(a)!=int(b) for a,b in zip(d.set_index('dia').sort_index().candles_5min,
                                         k.set_index('dia').sort_index().candles_5min))):
        raise ValueError('Os relatórios de qualidade e integridade divergem.')
    if not isinstance(origin_report,dict) or not re.fullmatch(r'[a-f0-9]{64}',str(origin_report.get('sha256_recebido',''))):
        raise ValueError('Falta o SHA-256 do arquivo original recebido.')
    if contract_map is not None:
        if not isinstance(contract_map,pd.DataFrame) or not REQUIRED_MAP_COLUMNS.issubset(contract_map.columns):
            raise ValueError('Mapa de contratos não está no formato aceito.')
        # Só aceitar mapas produzidos pelo parser de arquivo, não estruturas arbitrárias.
        for r in contract_map.to_dict('records'):
            nominal_expiry(r['contrato'])
    by_day = k.sort_values('dia').reset_index(drop=True).copy()
    daily_index=d.set_index('dia')
    contracts=[]; docs=[]; statuses=[]; expiry_flags=[]
    for raw in by_day.to_dict('records'):
        day=raw['dia']
        hit=None
        if contract_map is not None:
            matching=contract_map[(contract_map.inicio<=day) & (contract_map.fim>=day)]
            if len(matching)>1:
                raise ValueError('Mapa ambíguo: mais de um ticker para o mesmo dia.')
            if len(matching): hit=matching.iloc[0]
        if hit is None:
            contracts.append('NÃO INFORMADO'); docs.append(''); statuses.append('SEM_MAPA_DE_CONTRATO'); expiry_flags.append(False)
        else:
            symbol=str(hit.contrato)
            contracts.append(symbol); docs.append(str(hit.documento))
            statuses.append('DECLARADO_COM_REFERENCIA_NAO_VERIFICADA' if str(hit.documento) else 'DECLARADO_SEM_DOCUMENTO')
            expiry_flags.append(date.fromisoformat(day)>nominal_expiry(symbol))
    by_day['contrato_alegado']=contracts
    by_day['documento_alegado']=docs
    by_day['status_contrato']=statuses
    by_day['apos_vencimento_nominal_do_contrato_alegado']=expiry_flags
    by_day['sessao_fechamento_comprovado']=False
    by_day['ticker_por_candle_autenticado']=False
    by_day['origem_primaria_autenticada']=False
    by_day['backtest_liberado']=False
    boundaries=[]
    for idx in range(1,len(by_day)):
        prev=by_day.iloc[idx-1]; cur=by_day.iloc[idx]
        left,right=str(prev.contrato_alegado),str(cur.contrato_alegado)
        if 'NÃO INFORMADO' in (left,right):
            status='TICKER_INDETERMINADO'
        elif left!=right:
            status='MUDANCA_DECLARADA_NAO_COMPROVADA'
        else:
            status='MESMO_TICKER_ALEGADO_SEM_AUTENTICACAO'
        boundaries.append({'dia_anterior':str(prev.dia),'dia_seguinte':str(cur.dia),
                           'ticker_anterior_alegado':left,'ticker_seguinte_alegado':right,
                           'situacao':status,
                           'diferenca_entre_sessoes_pts':None if pd.isna(cur.diferenca_entre_sessoes_pts) else float(cur.diferenca_entre_sessoes_pts),
                           'troca_efetiva_comprovada':False,'ajuste_serie_comprovado':False,
                           'observacao':'Diferença de preço e troca de ticker declarada não provam rolagem ou ajuste.'})
    transition=pd.DataFrame(boundaries,columns=['dia_anterior','dia_seguinte','ticker_anterior_alegado',
           'ticker_seguinte_alegado','situacao','diferenca_entre_sessoes_pts','troca_efetiva_comprovada',
           'ajuste_serie_comprovado','observacao'])
    claims=int(by_day.status_contrato.ne('SEM_MAPA_DE_CONTRATO').sum())
    suspect=int(by_day.apos_vencimento_nominal_do_contrato_alegado.sum())
    uncovered=int(len(by_day)-claims)
    checklist=[
        ('Fonte primária de cotações', 'PENDENTE', 'Obter identificação do fornecedor original e documento da entrega.'),
        ('SHA-256 dos bytes recebidos', 'REGISTRADO_NAO_AUTENTICA', 'Comparar hash com cópia independente assinada pelo fornecedor, se houver.'),
        ('Ticker por candle', 'PENDENTE', 'Obter exportação original que associe cada candle a um vencimento WIN identificado.'),
        ('Mapa de contratos por dia', 'DECLARADO_NAO_COMPROVADO' if claims else 'PENDENTE', 'Comparar com ticker por candle e documentação de negociação/rolagem.'),
        ('Eventos de rolagem e ajustes', 'PENDENTE', 'Obter critérios do fornecedor para datas de troca, tipo de série e fatores de ajuste.'),
        ('Fuso e horários completos', 'PENDENTE', 'Comprovar horário dos candles, abertura e fechamento de cada sessão histórica.'),
        ('Lacunas e possíveis suspensões', 'PENDENTE', 'Verificar interrupções contra boletins oficiais e dados originais.'),
        ('Licença e direito de uso', 'PENDENTE', 'Conferir autorização de exportação e redistribuição do histórico.'),
        ('Backtest e ordens', 'BLOQUEADOS', 'Somente após certificação independente e nova etapa de validação.')]
    checklist_df=pd.DataFrame(checklist,columns=['requisito','situacao','proxima_evidencia_necessaria'])
    dossier={'versao':'1.4','classificacao':'DOSSIÊ_DESCRITIVO_SEM_CERTIFICACAO',
             'arquivo':str(origin_report.get('arquivo','')),'fonte_declarada':str(origin_report.get('fonte_declarada','')),
             'sha256_historico_recebido':origin_report['sha256_recebido'],
             'sha256_mapa_recebido':map_sha256,
             'pregoes_observados':int(len(by_day)),
             'dias_com_contrato_alegado':claims,'dias_sem_contrato_alegado':uncovered,
             'dias_declarados_apos_vencimento_nominal':suspect,
             'fronteiras_entre_sessoes':int(len(transition)),
             'mudancas_de_ticker_declaradas':int(transition.situacao.eq('MUDANCA_DECLARADA_NAO_COMPROVADA').sum()),
             'dias_com_ticker_autenticado':0,'dias_certificados':0,
             'origem_primaria_autenticada':False,'serie_ajustada_verificada':False,
             'contrato_por_candle_verificado':False,'horario_sessoes_certificado':False,
             'autoriza_sinais_backtest_ou_ordens':False,
             'aviso':'Mapa e hash apenas registram alegações e bytes; NÃO certificam preço, ticker, vencimento, rolagem, direitos ou origem B3.',
             'fontes_referencia':[
                 'https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/futuro-mini-de-ibovespa.htm',
                 'https://github.com/BernardoAflalo/FGV_Trabalho_WIN'],
             'pendencias':checklist_df.to_dict('records')}
    return by_day,transition,checklist_df,dossier
