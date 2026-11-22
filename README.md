# ◈ Trader Pro AI Elite v1.4 — Rastreabilidade dos dados

**Aplicativo experimental para pesquisa de mini-índice WIN, com interface Streamlit responsiva para celular.**

A versão 1.4 amplia os laboratórios de qualidade (v1.2) e integridade (v1.3) com um **dossiê de rastreabilidade** de séries 2019–2020. Não possui IA treinada, acesso a mercado ao vivo, execução de ordens nem resultados de mercado comprovados. **A análise exploratória não produz sinais ou backtests**.

## Atualização pelo Android — GitHub + Streamlit Cloud

1. Baixe o ZIP `Trader_Pro_AI_Elite_v1_4_GitHub.zip` e **extraia** no celular.
2. No mesmo repositório usado pelo Streamlit: **Add file → Upload files** e selecione os **22 arquivos extraídos na raiz**, substituindo arquivos com o mesmo nome. **Não envie o ZIP** como se fosse código.
3. Confirme **Commit changes** na branch `main`. O arquivo principal permanece `app.py`.
4. Abra o mesmo endereço da aplicação Streamlit e confira **RESEARCH TERMINAL · V1.4**.
5. Escolha **🔬 Explorar 2019–2020 · SEM backtest** e carregue o arquivo local `WIN_2019_2020_5min_exploratorio.csv` (ou o original de 1 minuto) na interface; **não publique dados de terceiros no repositório**.
6. Na aba **🔬 Histórico**, veja o novo painel **🧾 Rastreabilidade dos dados · v1.4**, seguido pelas seções de integridade v1.3 e qualidade v1.2.
7. Opcionalmente, baixe o modelo CSV vazio de contratos na própria interface. **Só preencha datas, tickers e referências que você tenha como documentar.** Um contrato presumido a partir de preço, mês ou calendário é apenas palpite e deve permanecer não informado.

## O que faz a v1.4

O módulo `traceability_lab.py` oferece:

- **Dossiê da entrada** com nome, origem *declarada* pelo usuário e hash SHA-256 dos **bytes recebidos**. O hash detecta diferenças de bytes entre arquivos comparados, mas não prova que os dados vieram da B3.
- **Mapa opcional de contratos declarados**, usando `inicio,fim,contrato,documento` com datas `AAAA-MM-DD`, intervalo não sobreposto e códigos `WIN[G/J/M/Q/V/Z][ano com dois dígitos]`. O campo `documento` é texto/URL fornecido pelo usuário, **não uma comprovação automática**. Se o CSV estiver incorreto, ele é rejeitado antes da análise.
- **Análise de vencimentos NOMINAIS**, segundo a quarta-feira mais próxima do dia 15 dos meses pares. Se uma atribuição cruzar essa data, gera um aviso investigativo; NÃO determina o último negócio, a real negociação ou as regras excepcionais daquele período.
- **Fronteiras entre pregões**: separa `TICKER_INDETERMINADO`, `MESMO_TICKER_ALEGADO_SEM_AUTENTICACAO` e `MUDANCA_DECLARADA_NAO_COMPROVADA`. As diferenças de preço são mostradas ao lado, mas **não confirmam rolagem**.
- **Lista de pendências de evidência**: fornecedor primário, ticker por candle, critérios de rolagem, fuso, abertura/encerramento, explicação das lacunas, licença dos dados.
- **Relatórios para download**: rastreabilidade por dia (CSV), fronteiras entre pregões (CSV), pendências (CSV) e dossiê (JSON).
- **Layout mobile** com cartões e filtros limitados a poucos registros na tela, preservando toda a análise nos arquivos CSV/JSON.

### Modelo de contrato (opcional)

O download na aplicação traz **somente o cabeçalho**:

```csv
inicio,fim,contrato,documento
```

Para informar uma hipótese, o campo `documento` deve conter a referência disponível e a fonte ainda precisa ser verificada independentemente. **Não invente datas de rolagem nem reutilize o exemplo de ticker como evidência.** Um mapa preenchido NUNCA muda `backtest_liberado` para verdadeiro.

### Resultado do arquivo público analisado

| Item | Valor |
|---|---:|
| Dias com candles | 181 |
| Fronteiras entre pregões | 180 |
| Dias com ticker comprovado | **0** |
| Dias com ticker alegado sem mapa adicional | 0 |
| Dias sem ticker informado no dossiê atual | 181 |
| Origem primária confirmada | **Não** |
| Dias certificados para backtest | **0** |

O arquivo público **não contém ticker por candle** e não informa os critérios de formação da série. A presença de preços 2019–2020 e de datas nominais de vencimento **não permite identificar automaticamente os contratos negociados**.

## Segurança e limitações

- Esta aplicação não gera ordens, nem habilita automação de execução.
- O modo **2019–2020** nunca chama `analyze` ou `backtest` e não promove informações declaradas a autenticadas.
- O modo histórico rigoroso de **2026** é mantido sem alterações de calendário; exige arquivo e contrato individual conforme validação anterior.
- Os avisos de 2019–2020 não corrigem lacunas, não ajustam preços, não atribuem contratos e não inferem eventos de mercado com base em saltos.
- Mesmo o melhor dia da série permanece **não certificado**, inclusive com mapa preenchido ou referência informada pelo usuário.
- Os parâmetros de preço destacados na v1.3 são percentis descritivos calculados sobre a própria amostra. Não são teste independente, prova de erro ou estratégia lucrativa.
- Os horários de encerramento por data, eventuais suspensões, ticker real, direitos de uso, política de emenda/ajuste e origem primária **não foram auditados externamente**.
- Quando novos dados autenticados forem obtidos, será necessário criar uma **etapa separada de validação**, não simplesmente liberar o bloqueio atual.

## Fontes externas de referência (não autenticam a amostra)

- [B3 — especificações atuais do futuro mini de Ibovespa](https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/futuro-mini-de-ibovespa.htm)
- [B3 — calendário de 2019](https://www.b3.com.br/data/files/F8/B3/88/A0/33E97610F157B776AC094EA8/CL%20049-2018_EN_VOP%20Feriados%202019_v7%20R_2.pdf)
- [B3 — calendário de 2020](https://www.b3.com.br/data/files/97/C7/BB/E1/F50BF6109A4874F6AC094EA8/OC%20003-2020-VOP%20Feriados%202020.pdf)
- [B3 — exceções de funcionamento em 2020](https://www.b3.com.br/pt_br/noticias/funcionamento-da-b3-8AE490C97215B74E0172959F18F11323.htm)
- [GitHub — FGV_Trabalho_WIN, origem secundária do arquivo público](https://github.com/BernardoAflalo/FGV_Trabalho_WIN)

As especificações atualmente publicadas pela B3 são usadas como referência geral e **não comprovam condições contratuais históricas em cada sessão**.

## Testes locais (opcionais; você não precisa executar no celular)

```bash
pip install -r requirements.txt
pip install pytest
pytest -q
streamlit run app.py
```

**101 testes automatizados passaram em 22/11/2026**, incluindo a suíte anterior. O ZIP foi extraído e testado novamente. Isso verifica regras do código e consistência dos arquivos, **não comprova a interface em produção nem desempenho financeiro**.
