# Auditor de Justificativas de Ronda

Este projeto analisa automaticamente rondas que foram marcadas como **nao realizadas com justificativa**. Ele foi criado para encontrar casos em que o colaborador respondeu `Nao` em **"INICIAR A RONDA?"**, mas enviou uma evidencia ruim, uma foto preta, uma imagem sem informacao ou nenhuma imagem.

A ideia principal e simples:

```text
Banco ou CSV -> auditor Python -> classificacao -> CSV de resultado
```

O resultado final separa as ocorrencias em grupos para facilitar a tomada de decisao.

## Por Que Esse Programa Existe

No fluxo atual, uma ronda pode deixar de aparecer como **nao realizada** quando o colaborador envia uma justificativa. O problema e que algumas justificativas podem vir com:

- foto preta;
- foto muito escura;
- foto sem conteudo util;
- imagem quebrada;
- nenhuma foto;
- justificativa textual sem comprovacao real.

Sem auditoria automatica, esses casos podem parecer justificados mesmo sem uma evidencia valida.

Este programa cria uma camada de verificacao antes de aceitar a justificativa como confiavel.

## O Que Ele Faz

O auditor:

- busca rondas justificadas direto do SQL Server ou de um CSV;
- identifica quem respondeu **"INICIAR A RONDA?" = Nao**;
- junta justificativa e link da foto pelo mesmo `Numero` e `Tarefa_id`;
- baixa a imagem quando existe `image_url`;
- detecta foto preta ou escura por metricas tecnicas;
- separa os casos sem imagem em um grupo proprio;
- gera um CSV final para abrir no Excel, BI ou outro relatorio;
- opcionalmente usa IA de visao para analisar casos suspeitos.

## Estrutura Das Pastas

```text
auditor_rondas/
  ronda_auditor.py
  .env
  requirements.txt
  README_RONDAS.md
  README_COMPLETO.md
  exemplos/
    atividades_justificadas_exemplo.csv
    foto_exemplo.jpg
    foto_preta.jpg
  resultados/
    resultado_*.csv
```

## Arquivo .env

O arquivo `.env` guarda as configuracoes do banco e, se necessario, da IA.

Exemplo:

```env
SQL_SERVER=172.31.50.62,1433
SQL_DATABASE=PROJETOS
SQL_AUTH=sql
SQL_USER=administrador
SQL_PASSWORD=sua_senha
SQL_DRIVER=ODBC Driver 17 for SQL Server
SQL_CAMPO_PERIODO=disponibilizacao

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1
```

Nao coloque esse arquivo em repositorio publico. Ele pode conter senha.

## Instalacao

Na primeira vez, rode:

```powershell
cd C:\Users\marcos_barros\Downloads\auditor_rondas
python -m pip install -r requirements.txt
```

## Modo Banco

Este e o modo recomendado para uso real.

```powershell
python ronda_auditor.py --data 2026-04-27 --saida resultados\resultado_2026-04-27.csv
```

Esse comando:

1. le servidor, banco, usuario e senha do `.env`;
2. busca rondas do dia `2026-04-27`;
3. filtra execucoes em que `INICIAR A RONDA?` foi respondido como `Nao`;
4. localiza a justificativa e a foto;
5. analisa as evidencias;
6. salva o resultado em `resultados\resultado_2026-04-27.csv`.

Para um periodo:

```powershell
python ronda_auditor.py --data-inicio 2026-04-20 --data-fim 2026-04-27 --saida resultados\resultado_periodo.csv
```

## Modo CSV

Este modo e util para testes, homologacao ou quando alguem exporta dados do BI.

```powershell
python ronda_auditor.py --entrada exemplos\atividades_justificadas_exemplo.csv --saida resultados\resultado_auditoria.csv
```

O CSV de entrada deve ter pelo menos:

```csv
atividade_id,colaborador,data,justificativa,image_url
```

Tambem pode usar `image_path` no lugar de `image_url`, quando a imagem estiver salva localmente.

## Qual Comando Usar

Use banco quando quiser analisar dados reais:

```powershell
python ronda_auditor.py --data 2026-04-27 --saida resultados\resultado_2026-04-27.csv
```

Use CSV quando quiser testar:

```powershell
python ronda_auditor.py --entrada exemplos\atividades_justificadas_exemplo.csv --saida resultados\resultado_teste.csv
```

## Campo De Periodo

Por padrao, o filtro de data usa:

```text
dbo.Execucao.Disponibilizacao
```

Isso esta configurado no `.env`:

```env
SQL_CAMPO_PERIODO=disponibilizacao
```

Se for necessario comparar com outro campo:

```powershell
python ronda_auditor.py --data 2026-04-27 --campo-periodo execucao --saida resultados\resultado_execucao.csv
```

Opcoes:

- `disponibilizacao`: usa `dbo.Execucao.Disponibilizacao`;
- `tarefa_disponibilizacao`: usa `dbo.TAREFA.Disponibilizacao`;
- `execucao`: usa a data em que a resposta foi registrada;
- `inicio`: usa `dbo.TAREFA.Inicio`;
- `termino`: usa `dbo.TAREFA.Termino`;
- `prazo`: usa `dbo.TAREFA.Prazo`;
- `inicio_real`: usa `dbo.TAREFA.InicioReal`.

## Grupos De Classificacao

### sem_comprovacao

Existe justificativa, mas nao existe foto/link.

Esse grupo e importante porque prova que o colaborador justificou sem enviar comprovacao visual.

Exemplo:

```text
image_url = vazio ou NULL
grupo = sem_comprovacao
```

### vermelho

A evidencia existe, mas parece claramente invalida.

Exemplos:

- foto preta;
- quase todos os pixels pretos;
- imagem escura demais;
- arquivo invalido;
- link que nao baixa corretamente.

### amarelo

A imagem e suspeita, mas o programa nao tem certeza suficiente para reprovar automaticamente.

Exemplos:

- imagem escura, mas nao totalmente preta;
- imagem borrada;
- imagem com pouca informacao visual;
- possivel evidencia, mas ruim.

Esse grupo e bom para auditoria reduzida.

### verde

A imagem passou nos criterios tecnicos basicos.

Isso nao significa que a justificativa e 100% verdadeira. Significa apenas que a evidencia visual nao parece preta, vazia ou tecnicamente inutil.

## Como O Programa Analisa Uma Foto

O programa calcula algumas metricas:

- brilho medio;
- variacao visual;
- percentual de pixels escuros;
- percentual de pixels quase pretos;
- nitidez aproximada;
- largura e altura.

Com base nesses sinais, ele decide se a imagem esta aceitavel, suspeita ou claramente ruim.

## Explicacao Das Colunas Do Resultado

### atividade_id

Numero da execucao/ronda. No banco vem da coluna `Numero`.

### tarefa_id

Identificador tecnico da tarefa. Ajuda a cruzar com `dbo.TAREFA`.

### colaborador

Nome do colaborador que respondeu a ronda.

### data

Data usada para o filtro do relatorio. Depende do `--campo-periodo`.

### data_execucao_inicio

Data/hora em que apareceu a resposta **"INICIAR A RONDA?" = Nao**.

### execucao_disponibilizacao

Disponibilizacao registrada na tabela `dbo.Execucao`.

### tarefa_disponibilizacao

Disponibilizacao registrada na tabela `dbo.TAREFA`.

### tarefa_inicio, tarefa_termino, tarefa_prazo

Campos de agenda da tarefa.

### tarefa_nome

Nome da tarefa/plano de ronda.

### checklist_nome

Nome do checklist associado.

### checklist_descricao

Descricao do checklist.

### justificativa

Texto informado pelo colaborador na pergunta de justificativa.

### image_url

Link da foto/evidencia. Quando estiver vazio, o grupo tende a ser `sem_comprovacao`.

### data_justificativa

Data/hora em que a justificativa ou evidencia foi registrada.

### grupo

Classificacao final:

```text
sem_comprovacao
vermelho
amarelo
verde
```

### confianca

Pontuacao de confianca entre `0.00` e `1.00`.

Exemplo:

```text
0.99 = alta confianca
0.70 = confianca moderada
```

### motivo

Explicacao curta da decisao.

Exemplo:

```text
imagem praticamente preta, com brilho e variacao visual muito baixos
```

### grupo_local

Classificacao feita pelas regras tecnicas locais, sem IA.

### confianca_local

Confianca das regras tecnicas locais.

### motivo_local

Motivo da classificacao local.

### brilho_medio

Media de brilho da imagem em escala de cinza.

Quanto menor, mais escura e a imagem.

### variacao_visual

Mede o quanto a imagem varia visualmente.

Foto preta ou imagem lisa tende a ter variacao muito baixa.

### pixels_escuros

Percentual de pixels considerados escuros.

Exemplo:

```text
1.0000 = 100% dos pixels escuros
0.8000 = 80% dos pixels escuros
```

### pixels_quase_pretos

Percentual de pixels quase totalmente pretos.

Esse campo ajuda a detectar lente tampada ou foto preta.

### nitidez_aproximada

Indicador simples de detalhes e bordas na imagem.

Valores muito baixos podem indicar imagem lisa ou muito borrada.

### largura e altura

Resolucao da imagem baixada.

### grupo_ia, confianca_ia, motivo_ia

Preenchidos apenas quando o modo IA esta ativado.

### erro_ia

Mostra erro relacionado a IA quando ela foi solicitada mas nao conseguiu rodar.

Exemplo:

```text
OPENAI_API_KEY nao configurada
```

## Usando IA De Visao

O uso de IA e opcional. O programa funciona sem IA.

Para ativar:

```env
IA_PROVIDER=openai
OPENAI_API_KEY=sua_chave
OPENAI_MODEL=gpt-4.1
```

Para usar Ollama Cloud no agente de validacao por IA:

```env
IA_PROVIDER=ollama
OLLAMA_MODEL=gemma4:31b-cloud
```

Depois rode:

```powershell
python ronda_auditor.py --data 2026-04-27 --saida resultados\resultado_ia.csv --usar-ia
```

Por padrao, a IA e chamada apenas nos casos `amarelo`, para economizar custo.

Para mandar todas as imagens para IA:

```powershell
python ronda_auditor.py --data 2026-04-27 --saida resultados\resultado_ia_todos.csv --usar-ia --ia-em todos
```

## Fluxo Recomendado De Operacao

1. Rode o auditor para a data desejada.
2. Abra o CSV em Excel.
3. Filtre primeiro `sem_comprovacao`.
4. Depois filtre `vermelho`.
5. Analise `amarelo` se quiser uma auditoria mais fina.
6. Use `verde` como baixo risco tecnico.

## Interpretacao Pratica

Uma sugestao de regra de negocio:

```text
verde            -> aceita automaticamente
amarelo          -> revisar ou reprocessar com IA
vermelho         -> recusar justificativa
sem_comprovacao  -> recusar por falta de evidencia
```

## Problemas Comuns

### Poucos registros no resultado

Teste outro campo de periodo:

```powershell
python ronda_auditor.py --data 2026-04-27 --campo-periodo execucao --saida resultados\resultado_execucao.csv
```

### Erro de driver ODBC

Verifique se o driver do SQL Server instalado bate com o `.env`:

```env
SQL_DRIVER=ODBC Driver 17 for SQL Server
```

Em algumas maquinas pode ser:

```env
SQL_DRIVER=ODBC Driver 18 for SQL Server
```

### CSV abre estranho no Excel

O programa gera CSV separado por virgula. Se o Excel abrir tudo em uma coluna, use **Dados > De Texto/CSV** e escolha delimitador `,`.

### Fotos nao baixam

Possiveis causas:

- link expirado;
- falta de permissao;
- rede bloqueando o dominio;
- API exigindo token;
- URL salva parcialmente no banco.

Nesses casos, o registro tende a cair como `vermelho` com motivo de erro ao baixar imagem.

## Resumo Curto

Para usar no dia a dia:

```powershell
cd C:\Users\marcos_barros\Downloads\auditor_rondas
python ronda_auditor.py --data 2026-04-27 --saida resultados\resultado_2026-04-27.csv
```

Depois abra o CSV em `resultados/` e filtre a coluna `grupo`.
