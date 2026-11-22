# ◈ Trader Pro AI Elite v1.2 — pesquisa de qualidade histórica (celular primeiro)

Aplicativo Streamlit **experimental**, visual premium escuro/roxo, sem IA treinada, corretora, cotações ao vivo ou ordens reais. **Não há taxa de acerto comprovada nem garantia de ganho**.

## Como atualizar pelo Android

1. Baixe e **extraia** o arquivo `Trader_Pro_AI_Elite_v1_1_GitHub.zip`.
2. Abra **o mesmo repositório GitHub** que já está ligado ao seu Streamlit Community Cloud.
3. Use **Add file → Upload files** e escolha **os 18 arquivos extraídos** (não o ZIP). Substitua os arquivos antigos de mesmo nome e acrescente os novos arquivos `quality_lab.py` e `test_quality_lab.py`.
4. Confirme **Commit changes** na `main`. O aplicativo continua apontando para **`app.py`**.
5. Abra o endereço Streamlit existente. No cabeçalho, procure **RESEARCH TERMINAL · V1.2**.
6. Selecione **🔬 Explorar 2019–2020 · SEM backtest** e carregue o arquivo `WIN_2019_2020_5min_exploratorio.csv` já recebido, **ou** o `data.csv` original. Veja a aba **🔬 Histórico**.
7. A fonte declarada pode ser `GitHub — FGV_Trabalho_WIN (origem primária não verificada)`; é apenas uma declaração, não um aval da B3.

Não é necessário pagar Replit ou instalar Python no celular. A instalação automática do Streamlit Cloud pode requerer alguns ajustes de hospedagem. A barra superior **Manage app** pertence ao Streamlit Cloud e pode continuar visível no navegador móvel. O app não controla o navegador do usuário.

## Novidades importantes — v1.2 (Laboratório de Qualidade)

- Novos módulos `quality_lab.py` e `test_quality_lab.py`: classificação reprodutível por dia, sem alterar as decisões do motor de sinais ou abrir backtest do CSV 2019–2020.
- Filtros para **dias com alerta**, **todos os dias**, **lacunas internas**, **abertura divergente**, **vencimento nominal**, **proximidade de vencimento** e **sem alertas locais**.
- Métrica de **trechos consecutivos entre candles observados** (NÃO mede completude de pregão); os resultados podem ser baixados em CSV e JSON.
- Vencimentos calculados novamente pela data: **10/02/2020 é proximidade de rolagem**, e **12/02/2020 é vencimento nominal**. O relatório gerado localmente pela v1.1 estava correto, embora um print da interface mostrasse o primeiro dia com um rótulo a mais. A v1.2 sinaliza qualquer discordância entre o rótulo antigo e a data.
- **97 dias sem alertas locais** na amostra pública fornecida; permanecem TODOS **não certificados**. Atribuir status sem alerta local **não autoriza backtest**, nem infere origem primária, contrato, preços, encerramento ou continuidade da sessão completa.
- Na amostra observada: **181 dias**, **15 com lacunas**, **64 com abertura divergente** e **5 vencimentos nominais**. Os grupos podem se sobrepor.
- **64 testes de código aprovados** no ambiente de desenvolvimento, inclusive as regressões v1.1 e a distinção 10/02 vs 12/02. Ainda é necessário testar o Streamlit após o commit.

## O que mudou na v1.2

- **Novo modo separado, EXPLORATÓRIO, para 2019–2020**: aceita CSV já convertido para 5 minutos ou CSV/TSV original com DATE, TIME, OPEN, HIGH, LOW, CLOSE, VOL (1 minuto). CSV é processado no Streamlit Cloud, não há download automático de preços pela aplicação.
- **Conversão conservadora 1m → 5m**: um candle 5m só é gerado se os cinco minutos exatos estiverem presentes. Janelas parciais são descartadas e contabilizadas. Não cria preços, preenche lacunas ou arredonda ticks fora da grade de 5 pontos.
- **Calendário histórico auditável**: feriados B3 de 2019 e 2020 e abertura às 13h na quarta de cinzas. Em 2020, 11/06 é fechado; 09/07 e 20/11 **tiveram negociação normal** por exceção posterior aos calendários iniciais.
- **Qualidade verificável**: detecta candles inválidos/duplicados, horários, lacunas internas, dias de pregão sem nenhum dado, abertura divergente da referência, e datas **nominais** de vencimento como pontos de investigação de eventual rolagem.
- **Leitura mobile**: novos cartões/relatos verticais com alertas; exportação em JSON e CSV para auditoria.
- **Proteção para não induzir conclusões falsas**: o modo 2019–2020 **NÃO** passa pelo `engine.analyze()` ou pelo `backtest()`. Sinais e rentabilidade ficam bloqueados porque não se conhece o ticker/contrato de cada candle, os ajustes de rolagem, o fuso comprovado, a origem primária ou o fechamento de todas as sessões.
- **Modo 2026 separado e preservado**: a validação estrita e o backtest existentes não foram afrouxados para aceitar a série antiga.

## Resultado verificado com o arquivo recebido

Quando importado o CSV fornecido nesta conversa:

- **96.937** barras de 1 minuto de origem, convertidas em **19.257** candles completos de 5 minutos (ou 19.257 no CSV convertido).
- **227 janelas 5min parciais descartadas**, ao ler o original de 1 minuto.
- **181 dias com registros**, de **09/12/2019 a 31/08/2020**.
- **0 dias de pregão inteiros ausentes** entre as datas extremas conforme os feriados e exceções 2019–2020 mapeados; esse número NÃO comprova sessões completas.
- **72 saltos internos** entre candles 5 minutos (em **15 dias**); **64 dias** têm primeiro candle convertido diferente da abertura de referência (09h, ou 13h na quarta-feira de cinzas).

**Importante:** o fechamento das sessões individuais não foi autenticado; a causa de cada lacuna (ausência de negócios, dados perdidos, interrupção ou outra condição) é **desconhecida**. A B3 registrou regras especiais e limites de oscilação em 2020. Não atribuir automaticamente qualquer lacuna ao circuit breaker.

## Calendário e vencimentos

- 2019: B3 Ofício 049/2018-VOP (calendário de 2019): https://www.b3.com.br/data/files/F8/B3/88/A0/33E97610F157B776AC094EA8/CL%20049-2018_EN_VOP%20Feriados%202019_v7%20R_2.pdf
- 2020: B3 Ofício 003/2020-VOP (corrigido): https://www.b3.com.br/data/files/97/C7/BB/E1/F50BF6109A4874F6AC094EA8/OC%20003-2020-VOP%20Feriados%202020.pdf
- Exceções 2020: https://www.b3.com.br/pt_br/noticias/funcionamento-da-b3-8AE490C97215B74E0172959F18F11323.htm
- Contrato WIN: B3, 5 pontos de tick e vencimento na quarta mais próxima do dia 15 dos meses pares: https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/futuro-mini-de-ibovespa.htm

Os dias de vencimento exibidos pelo app são **datas nominais**, não uma prova de que o preço foi corretamente emendado, corrigido ou negociado em determinado contrato. A grade histórica de **encerramento** do WIN, por data, **não** foi homologada neste módulo. Não inferir sessão completa a partir de ter dados até um horário típico.

## Como testar o código (opcional)

```bash
pip install -r requirements.txt
pip install pytest
pytest -q
streamlit run app.py
```

Os testes locais incluem o modo 2026 legado e os cenários 2019–2020. As verificações de Python e pytest não garantem que a implantação visual funcione no Streamlit Cloud. A interface deve ser confirmada depois do commit.

## Limitações de confiança e direitos de dados

O hash SHA-256 identifica os bytes recebidos, **não atesta cotações negociadas na B3**. O conjunto público não comprova o contrato/mês de cada linha, os ajustes da série, a permissão da fonte primária nem o fuso. Não redistribua dados sem verificar os direitos. A aplicação **não inclui** nem publica o arquivo histórico no repositório: ele é enviado pelo próprio usuário ao navegador. Backtests históricos com capital real e execução de corretora permanecem desativados.
