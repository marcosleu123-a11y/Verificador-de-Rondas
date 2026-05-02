# Auditor de justificativas de ronda

Para o manual detalhado de uso, comandos, colunas do resultado e interpretacao dos grupos, veja `README_COMPLETO.md`.

Este MVP analisa atividades justificadas e separa as evidencias em quatro grupos:

- `sem_comprovacao`: justificativa sem foto/link de evidencia.
- `vermelho`: alta certeza de evidencia inconforme, como foto preta, arquivo invalido ou imagem quase vazia.
- `amarelo`: suspeita, mas sem certeza suficiente para reprovar automaticamente.
- `verde`: imagem passou nos criterios tecnicos basicos.

## Entrada esperada

Crie ou exporte um CSV com pelo menos estas colunas:

```csv
atividade_id,colaborador,data,justificativa,image_path
123,Joao,2026-04-28,"Portao bloqueado",C:\fotos\ronda_123.jpg
```

Tambem pode usar `image_url` no lugar de `image_path` quando a imagem estiver em um link acessivel.

## Como rodar

Instale as dependencias:

```powershell
pip install -r requirements.txt
```

Rode a auditoria:

```powershell
python ronda_auditor.py --entrada exemplos\atividades_justificadas_exemplo.csv --saida resultados\resultado_auditoria.csv
```

## Rodando direto no banco

Edite o arquivo `.env` e preencha as credenciais:

```env
SQL_SERVER=172.31.50.62,1433
SQL_DATABASE=PROJETOS
SQL_AUTH=sql
SQL_USER=seu_usuario
SQL_PASSWORD=sua_senha
SQL_DRIVER=ODBC Driver 17 for SQL Server
SQL_CAMPO_PERIODO=disponibilizacao
```

Depois rode para uma data especifica:

```powershell
python ronda_auditor.py --data 2026-04-27 --saida resultados\resultado_2026-04-27.csv
```

Ou para um periodo:

```powershell
python ronda_auditor.py --data-inicio 2026-04-20 --data-fim 2026-04-27 --saida resultados\resultado_periodo.csv
```

O modo banco busca as execucoes em que `INICIAR A RONDA?` foi respondido como `Nao/Não`, junta a justificativa e o link da foto pelo mesmo `Numero` e `Tarefa_id`, e mantem os casos sem imagem como `sem_comprovacao`.

Por padrao, o filtro de periodo usa `dbo.Execucao.Disponibilizacao`. Se precisar comparar outro campo:

```powershell
python ronda_auditor.py --data 2026-04-27 --campo-periodo inicio --saida resultados\resultado_inicio.csv
```

Opcoes: `disponibilizacao`, `tarefa_disponibilizacao`, `inicio`, `termino`, `prazo`, `inicio_real`, `execucao`.

## Usando IA de visao

A analise local ja detecta foto preta, imagem escura, arquivo quebrado e imagem quase sem variacao. Para analisar coerencia visual, rode com IA:

```powershell
$env:OPENAI_API_KEY="sua_chave"
python ronda_auditor.py --entrada atividades.csv --saida resultado.csv --usar-ia
```

Por padrao, a IA so e chamada para casos `amarelo`, para economizar custo. Para analisar todas:

```powershell
python ronda_auditor.py --entrada atividades.csv --saida resultado.csv --usar-ia --ia-em todos
```

## Saida

O CSV de saida inclui:

- `grupo`: `sem_comprovacao`, `vermelho`, `amarelo` ou `verde`.
- `confianca`: pontuacao entre 0 e 1.
- `motivo`: explicacao curta da decisao.
- metricas tecnicas, como brilho medio, variacao visual e percentual de pixels escuros.
- campos de IA, quando habilitada.

Recomendacao de negocio: aceite automaticamente apenas `verde`, recuse automaticamente `sem_comprovacao` e `vermelho` com regra bem definida, e deixe `amarelo` para fila reduzida de auditoria ou reprocessamento.
