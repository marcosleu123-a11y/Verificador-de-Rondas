import argparse
import base64
import csv
import json
import mimetypes
import os
import tempfile
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Tuple


COLUNA_ANALISADA = "analisada por IA"
COLUNA_GRUPO = "grupo_analise_ia"
COLUNA_CONFIANCA = "confianca_analise_ia"
COLUNA_MOTIVO = "motivo_analise_ia"
COLUNA_DESCRICAO_VISUAL = "descricao_visual_ia"
COLUNA_ACAO = "acao_sugerida_ia"
COLUNA_ERRO = "erro_analise_ia"

GRUPOS_IA = {"aprovada", "reprovada", "duvidosa", "sem_imagem"}
TERMOS_EVIDENCIA_FRACA = [
    "nao da para",
    "nao e possivel",
    "nao permite",
    "nao identifica",
    "nao consigo",
    "sem detalhes",
    "pouco detalhe",
    "baixa qualidade",
    "borrada",
    "desfocada",
    "escura",
    "muito escura",
    "preta",
    "distante",
    "ilegivel",
    "nao conclusiva",
    "inconclusiva",
    "generica",
    "parcial",
]


def carregar_env(caminho: Path) -> None:
    if not caminho.exists():
        return

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue

        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor


def carregar_env_automatico() -> None:
    pasta_script = Path(__file__).resolve().parent
    carregar_env(pasta_script.parent / ".env")
    carregar_env(pasta_script / ".env")
    carregar_env(Path.cwd() / ".env")


def ler_csv(caminho: Path) -> List[Dict[str, str]]:
    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        amostra = arquivo.read(4096)
        arquivo.seek(0)
        try:
            dialecto = csv.Sniffer().sniff(amostra, delimiters=",;") if amostra else csv.excel
        except csv.Error:
            dialecto = csv.excel
        leitor = csv.DictReader(arquivo, dialect=dialecto)
        if not leitor.fieldnames:
            raise ValueError("CSV de entrada esta vazio ou sem cabecalho")
        return [dict(linha) for linha in leitor]


def valor(linha: Dict[str, str], *nomes: str) -> str:
    for nome in nomes:
        if nome in linha and linha[nome]:
            return str(linha[nome]).strip()
    return ""


def decimal_texto(texto: str) -> Optional[Decimal]:
    if not texto:
        return None
    try:
        return Decimal(str(texto).replace(",", "."))
    except InvalidOperation:
        return None


def float_texto(texto: str) -> Optional[float]:
    decimal = decimal_texto(texto)
    return float(decimal) if decimal is not None else None


def contem_termo(texto: str, termos: List[str]) -> bool:
    texto_normalizado = texto.lower()
    return any(termo in texto_normalizado for termo in termos)


def baixar_imagem(image_url: str) -> Path:
    suffix = Path(image_url.split("?")[0]).suffix or ".jpg"
    destino = Path(tempfile.gettempdir()) / f"agente_ia_{abs(hash(image_url))}{suffix}"
    if not destino.exists():
        urllib.request.urlretrieve(image_url, destino)
    return destino


def imagem_para_data_url(caminho: Path) -> str:
    mime_type = mimetypes.guess_type(caminho.name)[0] or "image/jpeg"
    conteudo = base64.b64encode(caminho.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{conteudo}"


def obter_imagem_para_ia(linha: Dict[str, str], pasta_base: Path, baixar_links: bool) -> Optional[str]:
    image_path = valor(linha, "image_path", "caminho_imagem", "foto_path")
    image_url = valor(linha, "image_url", "url_imagem", "foto_url", "link_foto")

    if image_path:
        caminho = Path(image_path)
        if not caminho.is_absolute():
            caminho = pasta_base / caminho
        if not caminho.exists():
            raise FileNotFoundError(f"imagem local nao encontrada: {caminho}")
        return imagem_para_data_url(caminho)

    if image_url:
        if baixar_links:
            caminho = baixar_imagem(image_url)
            return imagem_para_data_url(caminho)
        return image_url

    return None


def extrair_json(texto: str) -> Dict[str, object]:
    texto = texto.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        inicio = texto.find("{")
        fim = texto.rfind("}")
        if inicio == -1 or fim == -1 or fim <= inicio:
            raise
        return json.loads(texto[inicio : fim + 1])


def imagem_data_url_para_base64(imagem: str) -> str:
    if not imagem.startswith("data:"):
        raise ValueError("Ollama precisa da imagem baixada em base64. Rode sem --nao-baixar-links.")
    return imagem.split(",", 1)[1]


def chamar_openai(prompt: str, imagem: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY nao configurada no .env")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    modelo = os.getenv("OPENAI_MODEL", "gpt-4.1")
    resposta = client.responses.create(
        model=modelo,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": imagem, "detail": "low"},
                ],
            }
        ],
    )
    return resposta.output_text


def chamar_ollama(prompt: str, imagem: str) -> str:
    from ollama import chat

    modelo = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
    response = chat(
        model=modelo,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [imagem_data_url_para_base64(imagem)],
            }
        ],
    )

    if hasattr(response, "message") and hasattr(response.message, "content"):
        return response.message.content
    return response["message"]["content"]


def chamar_ia(prompt: str, imagem: str, provedor_ia: str) -> str:
    if provedor_ia == "ollama":
        return chamar_ollama(prompt, imagem)
    if provedor_ia == "openai":
        return chamar_openai(prompt, imagem)
    raise ValueError(f"provedor de IA invalido: {provedor_ia}")


def montar_contexto(linha: Dict[str, str]) -> str:
    campos_interessantes = [
        "atividade_id",
        "tarefa_id",
        "contrato_cr",
        "estrutura_id",
        "nivel_03",
        "nivel_04",
        "andar",
        "local",
        "ambiente",
        "qrcode",
        "colaborador",
        "data",
        "tarefa_nome",
        "checklist_nome",
        "checklist_descricao",
        "justificativa",
        "grupo",
        "grupo_local",
        "grupo_script",
        "motivo",
        "motivo_local",
        "motivo_script",
        "image_url",
    ]

    partes = []
    for campo in campos_interessantes:
        conteudo = valor(linha, campo)
        if conteudo:
            partes.append(f"{campo}: {conteudo}")
    return "\n".join(partes) if partes else "Sem contexto textual estruturado."


def montar_analise_script(linha: Dict[str, str]) -> Tuple[str, str]:
    grupo = valor(linha, "grupo_script", "grupo_local", "grupo")
    confianca = valor(linha, "confianca_script", "confianca_local", "confianca")
    motivo = valor(linha, "motivo_script", "motivo_local", "motivo")
    brilho = valor(linha, "brilho_medio")
    variacao = valor(linha, "variacao_visual")
    pixels_escuros = valor(linha, "pixels_escuros")
    pixels_quase_pretos = valor(linha, "pixels_quase_pretos")
    nitidez = valor(linha, "nitidez_aproximada")
    largura = valor(linha, "largura")
    altura = valor(linha, "altura")

    sinais = []
    brilho_num = float_texto(brilho)
    variacao_num = float_texto(variacao)
    pixels_escuros_num = float_texto(pixels_escuros)
    pixels_quase_pretos_num = float_texto(pixels_quase_pretos)
    nitidez_num = float_texto(nitidez)

    if grupo:
        sinais.append(f"classificacao_script={grupo}")
    if brilho_num is not None and brilho_num < 12:
        sinais.append("brilho muito baixo")
    if pixels_quase_pretos_num is not None and pixels_quase_pretos_num >= 0.75:
        sinais.append("muitos pixels quase pretos")
    if pixels_escuros_num is not None and pixels_escuros_num >= 0.80:
        sinais.append("imagem predominantemente escura")
    if variacao_num is not None and variacao_num < 10:
        sinais.append("pouca variacao visual")
    if nitidez_num is not None and nitidez_num < 2.5:
        sinais.append("nitidez baixa")

    linhas = [
        f"grupo_script: {grupo or 'nao informado'}",
        f"confianca_script: {confianca or 'nao informada'}",
        f"motivo_script: {motivo or 'nao informado'}",
        f"brilho_medio: {brilho or 'nao informado'}",
        f"variacao_visual: {variacao or 'nao informada'}",
        f"pixels_escuros: {pixels_escuros or 'nao informado'}",
        f"pixels_quase_pretos: {pixels_quase_pretos or 'nao informado'}",
        f"nitidez_aproximada: {nitidez or 'nao informada'}",
        f"dimensoes: {largura or '?'}x{altura or '?'}",
    ]

    resumo_sinais = "; ".join(sinais) if sinais else "sem alerta tecnico forte"
    linhas.append(f"sinais_tecnicos_interpretados: {resumo_sinais}")
    return "\n".join(linhas), resumo_sinais


def script_tem_alerta_critico(linha: Dict[str, str]) -> bool:
    grupo = valor(linha, "grupo_script", "grupo_local", "grupo").lower()
    motivo = valor(linha, "motivo_script", "motivo_local", "motivo").lower()
    brilho = float_texto(valor(linha, "brilho_medio"))
    variacao = float_texto(valor(linha, "variacao_visual"))
    pixels_quase_pretos = float_texto(valor(linha, "pixels_quase_pretos"))

    if grupo in {"vermelho", "sem_comprovacao"}:
        return True
    if "sem imagem" in motivo or "sem comprovacao" in motivo or "preta" in motivo:
        return True
    if brilho is not None and brilho < 8:
        return True
    if pixels_quase_pretos is not None and pixels_quase_pretos >= 0.85:
        return True
    if variacao is not None and variacao < 6:
        return True
    return False


def aplicar_guardrails(linha: Dict[str, str], analise: Dict[str, str]) -> Dict[str, str]:
    if analise.get(COLUNA_ANALISADA) != "aprovada":
        return analise

    descricao = analise.get(COLUNA_DESCRICAO_VISUAL, "")
    motivo = analise.get(COLUNA_MOTIVO, "")
    acao = analise.get(COLUNA_ACAO, "").lower()
    confianca = float_texto(analise.get(COLUNA_CONFIANCA, "")) or 0.0
    texto_ia = f"{descricao} {motivo}"

    motivos_bloqueio = []
    if confianca < 0.75:
        motivos_bloqueio.append("confianca abaixo do minimo para aprovacao")
    if acao in {"revisar", "recusar"}:
        motivos_bloqueio.append(f"acao sugerida pela IA foi {acao}")
    if contem_termo(texto_ia, TERMOS_EVIDENCIA_FRACA):
        motivos_bloqueio.append("a propria descricao da IA indica evidencia visual fraca")
    if script_tem_alerta_critico(linha):
        motivos_bloqueio.append("script tecnico apontou alerta critico na imagem")

    if not motivos_bloqueio:
        return analise

    analise_corrigida = {**analise}
    analise_corrigida[COLUNA_ANALISADA] = "duvidosa"
    analise_corrigida[COLUNA_GRUPO] = "duvidosa"
    analise_corrigida[COLUNA_CONFIANCA] = f"{min(confianca, 0.74):.2f}"
    complemento = "; ".join(motivos_bloqueio)
    motivo_original = analise.get(COLUNA_MOTIVO, "").strip()
    analise_corrigida[COLUNA_MOTIVO] = (
        f"{motivo_original} Guardrail: aprovacao convertida para duvidosa porque {complemento}."
    ).strip()
    analise_corrigida[COLUNA_ACAO] = "revisar"
    return analise_corrigida


def analisar_linha_com_ia(linha: Dict[str, str], pasta_base: Path, baixar_links: bool, provedor_ia: str) -> Dict[str, str]:
    imagem = obter_imagem_para_ia(linha, pasta_base, baixar_links)
    justificativa = valor(linha, "justificativa")

    if not imagem:
        return {
            COLUNA_ANALISADA: "sem imagem",
            COLUNA_GRUPO: "sem_imagem",
            COLUNA_CONFIANCA: "1.00",
            COLUNA_MOTIVO: "Nao existe image_url ou image_path para a IA validar.",
            COLUNA_DESCRICAO_VISUAL: "",
            COLUNA_ACAO: "recusar por falta de comprovacao",
            COLUNA_ERRO: "",
        }

    contexto = montar_contexto(linha)
    analise_script, sinais_script = montar_analise_script(linha)

    prompt = f"""
Voce e um agente auditor de rondas operacionais.

Sua tarefa e comparar:
1. a justificativa textual do colaborador;
2. o contexto da tarefa/ronda;
3. a imagem enviada como evidencia;
4. a analise tecnica feita previamente pelo script Python.

Decida se a evidencia visual comprova ou apoia claramente a justificativa e o contexto operacional.
A analise do script e uma evidencia auxiliar: use os numeros para perceber imagem escura,
uniforme, borrada ou sem comprovacao, mas nao aceite nem recuse apenas pela metrica.
Se a imagem contradizer a justificativa, priorize a imagem e explique a divergencia.
Se a imagem nao permitir decidir com seguranca, nao aprove. Classifique como duvidosa.

Use:
- aprovada: somente quando a imagem mostra evidencia visual clara, especifica e coerente com a justificativa.
- reprovada: quando a imagem e preta, vazia, inutil, sem relacao aparente, ou contradiz a justificativa.
- duvidosa: quando a imagem tem alguma informacao, mas nao comprova bem, esta longe, borrada, escura, generica, parcial, ou nao permite decidir.
- sem_imagem: quando nao houver imagem, mas esse caso normalmente ja sera tratado antes.

Regras conservadoras:
- Na duvida, use duvidosa, nao aprovada.
- Nao aprove fotos que apenas parecem plausiveis; aprove apenas quando houver evidencia visual suficiente.
- Se voce escrever que nao da para identificar, confirmar, ler, ver detalhes ou decidir, a classificacao deve ser duvidosa ou reprovada.
- Para aprovar, o motivo deve citar qual elemento visivel da imagem confirma a justificativa.

Contexto da linha:
{contexto}

Justificativa principal:
{justificativa or "nao informada"}

Analise tecnica do script:
{analise_script}

Sinais que merecem atencao:
{sinais_script}

Responda somente em JSON valido neste formato:
{{
  "analisada_por_ia": "aprovada|reprovada|duvidosa|sem_imagem",
  "confianca": 0.0,
  "motivo": "explicacao curta",
  "descricao_visual": "o que a imagem parece mostrar",
  "acao_sugerida": "aceitar|revisar|recusar"
}}
""".strip()

    resposta_texto = chamar_ia(prompt, imagem, provedor_ia)
    dados = extrair_json(resposta_texto)
    analisada = str(dados.get("analisada_por_ia", "duvidosa")).strip().lower()
    if analisada not in GRUPOS_IA:
        analisada = "duvidosa"

    confianca = float(dados.get("confianca", 0.0))
    confianca = max(0.0, min(1.0, confianca))

    analise = {
        COLUNA_ANALISADA: analisada,
        COLUNA_GRUPO: analisada,
        COLUNA_CONFIANCA: f"{confianca:.2f}",
        COLUNA_MOTIVO: str(dados.get("motivo", "")).strip(),
        COLUNA_DESCRICAO_VISUAL: str(dados.get("descricao_visual", "")).strip(),
        COLUNA_ACAO: str(dados.get("acao_sugerida", "")).strip(),
        COLUNA_ERRO: "",
    }
    return aplicar_guardrails(linha, analise)


def salvar_xlsx(linhas: List[Dict[str, str]], saida: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    saida.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Analise IA"

    colunas = list(linhas[0].keys()) if linhas else []
    sheet.append(colunas)

    for linha in linhas:
        sheet.append([linha.get(coluna, "") for coluna in colunas])

    header_fill = PatternFill("solid", fgColor="1F2937")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    cores = {
        "aprovada": "DCFCE7",
        "reprovada": "FEE2E2",
        "duvidosa": "FEF3C7",
        "sem imagem": "E5E7EB",
        "sem_imagem": "E5E7EB",
    }

    if COLUNA_ANALISADA in colunas:
        indice = colunas.index(COLUNA_ANALISADA) + 1
        for row in range(2, sheet.max_row + 1):
            status = str(sheet.cell(row=row, column=indice).value or "").lower()
            fill = PatternFill("solid", fgColor=cores.get(status, "FFFFFF"))
            for col in range(1, sheet.max_column + 1):
                sheet.cell(row=row, column=col).fill = fill

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    for coluna in range(1, sheet.max_column + 1):
        letra = get_column_letter(coluna)
        maior = 12
        for cell in sheet[letra]:
            maior = max(maior, len(str(cell.value or "")) + 2)
        sheet.column_dimensions[letra].width = min(maior, 55)

    workbook.save(saida)


def analisar_csv(entrada: Path, saida: Path, limite: Optional[int], baixar_links: bool, provedor_ia: str) -> None:
    linhas = ler_csv(entrada)
    pasta_base = entrada.parent
    linhas_saida = []

    for indice, linha in enumerate(linhas, start=1):
        if limite and indice > limite:
            linha_saida = {**linha}
            linha_saida[COLUNA_ANALISADA] = "nao analisada"
            linha_saida[COLUNA_GRUPO] = ""
            linha_saida[COLUNA_CONFIANCA] = ""
            linha_saida[COLUNA_MOTIVO] = "Limite de analise atingido."
            linha_saida[COLUNA_DESCRICAO_VISUAL] = ""
            linha_saida[COLUNA_ACAO] = ""
            linha_saida[COLUNA_ERRO] = ""
            linhas_saida.append(linha_saida)
            continue

        try:
            analise = analisar_linha_com_ia(linha, pasta_base, baixar_links, provedor_ia)
        except Exception as exc:
            analise = {
                COLUNA_ANALISADA: "erro",
                COLUNA_GRUPO: "erro",
                COLUNA_CONFIANCA: "0.00",
                COLUNA_MOTIVO: "A IA nao conseguiu analisar esta linha.",
                COLUNA_DESCRICAO_VISUAL: "",
                COLUNA_ACAO: "revisar",
                COLUNA_ERRO: str(exc),
            }

        linhas_saida.append({**linha, **analise})
        print(f"Analisado {indice}/{len(linhas)}: {analise[COLUNA_ANALISADA]}")

    salvar_xlsx(linhas_saida, saida)
    print(f"Arquivo gerado: {saida}")


def conexao_postgres_kwargs() -> Dict[str, object]:
    dsn = os.getenv("POSTGRES_DSN")
    if dsn:
        return {"conninfo": dsn}

    host = os.getenv("POSTGRES_HOST") or os.getenv("PGHOST")
    database = os.getenv("POSTGRES_DATABASE") or os.getenv("PGDATABASE")
    user = os.getenv("POSTGRES_USER") or os.getenv("PGUSER")
    password = os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD")
    port = os.getenv("POSTGRES_PORT") or os.getenv("PGPORT") or "5432"
    sslmode = os.getenv("POSTGRES_SSLMODE") or os.getenv("PGSSLMODE") or "prefer"

    if not host or not database or not user or not password:
        raise ValueError(
            "configure POSTGRES_HOST, POSTGRES_DATABASE, POSTGRES_USER e POSTGRES_PASSWORD "
            "ou use POSTGRES_DSN"
        )

    return {
        "host": host,
        "dbname": database,
        "user": user,
        "password": password,
        "port": int(port),
        "sslmode": sslmode,
    }


def modelo_ia(provedor_ia: str) -> str:
    if provedor_ia == "ollama":
        return os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
    return os.getenv("OPENAI_MODEL", "gpt-4.1")


def buscar_pendentes_postgres(limite: Optional[int], execucao_id: Optional[int]) -> List[Dict[str, str]]:
    import psycopg
    from psycopg import sql

    schema = os.getenv("POSTGRES_SCHEMA", "dbo")
    filtros = [
        sql.SQL(
            "NOT EXISTS (SELECT 1 FROM {} ia WHERE ia.ronda_id = r.id)"
        ).format(sql.Identifier(schema, "analise_ia"))
    ]
    parametros: List[object] = []

    if execucao_id is not None:
        filtros.append(sql.SQL("r.execucao_id = %s"))
        parametros.append(execucao_id)

    limite_sql = sql.SQL("")
    if limite:
        limite_sql = sql.SQL("LIMIT %s")
        parametros.append(limite)

    query = sql.SQL(
        """
        SELECT
            r.id AS ronda_id,
            r.execucao_id,
            s.id AS analise_script_id,
            r.atividade_id,
            r.tarefa_id,
            r.contrato_cr,
            r.estrutura_id,
            r.nivel_03,
            r.nivel_04,
            r.andar,
            r.local,
            r.ambiente,
            r.qrcode,
            r.colaborador,
            r.data,
            r.data_execucao_inicio,
            r.execucao_disponibilizacao,
            r.tarefa_disponibilizacao,
            r.tarefa_inicio,
            r.tarefa_termino,
            r.tarefa_prazo,
            r.tarefa_nome,
            r.checklist_nome,
            r.checklist_descricao,
            r.justificativa,
            r.image_url,
            r.image_path,
            r.data_justificativa,
            s.grupo AS grupo_script,
            s.confianca AS confianca_script,
            s.motivo AS motivo_script,
            s.brilho_medio,
            s.variacao_visual,
            s.pixels_escuros,
            s.pixels_quase_pretos,
            s.nitidez_aproximada,
            s.largura,
            s.altura
        FROM {} r
        JOIN {} s
            ON s.ronda_id = r.id
        WHERE {}
        ORDER BY r.id
        {}
        """
    ).format(
        sql.Identifier(schema, "rondas_base"),
        sql.Identifier(schema, "analise_script"),
        sql.SQL(" AND ").join(filtros),
        limite_sql,
    )

    with psycopg.connect(**conexao_postgres_kwargs()) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(query, parametros)
            colunas = [coluna.name for coluna in cursor.description]
            return [
                {coluna: "" if valor_linha is None else str(valor_linha) for coluna, valor_linha in zip(colunas, linha)}
                for linha in cursor.fetchall()
            ]


def salvar_analise_ia_postgres(linha: Dict[str, str], analise: Dict[str, str], provedor_ia: str) -> None:
    import psycopg
    from psycopg import sql

    schema = os.getenv("POSTGRES_SCHEMA", "dbo")
    with psycopg.connect(**conexao_postgres_kwargs()) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    """
                    INSERT INTO {} (
                        ronda_id,
                        analise_script_id,
                        analisada_por_ia,
                        grupo,
                        confianca,
                        motivo,
                        descricao_visual,
                        acao_sugerida,
                        erro,
                        provedor_ia,
                        modelo_ia
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                ).format(sql.Identifier(schema, "analise_ia")),
                (
                    int(valor(linha, "ronda_id")),
                    int(valor(linha, "analise_script_id")),
                    analise.get(COLUNA_ANALISADA),
                    analise.get(COLUNA_GRUPO),
                    decimal_texto(analise.get(COLUNA_CONFIANCA, "")),
                    analise.get(COLUNA_MOTIVO),
                    analise.get(COLUNA_DESCRICAO_VISUAL),
                    analise.get(COLUNA_ACAO),
                    analise.get(COLUNA_ERRO),
                    provedor_ia,
                    modelo_ia(provedor_ia),
                ),
            )


def analisar_postgres(limite: Optional[int], execucao_id: Optional[int], baixar_links: bool, provedor_ia: str) -> None:
    linhas = buscar_pendentes_postgres(limite, execucao_id)
    if not linhas:
        print("Nenhuma ronda pendente de analise por IA no Postgres.")
        return

    pasta_base = Path.cwd()
    for indice, linha in enumerate(linhas, start=1):
        try:
            analise = analisar_linha_com_ia(linha, pasta_base, baixar_links, provedor_ia)
        except Exception as exc:
            analise = {
                COLUNA_ANALISADA: "erro",
                COLUNA_GRUPO: "erro",
                COLUNA_CONFIANCA: "0.00",
                COLUNA_MOTIVO: "A IA nao conseguiu analisar esta linha.",
                COLUNA_DESCRICAO_VISUAL: "",
                COLUNA_ACAO: "revisar",
                COLUNA_ERRO: str(exc),
            }

        salvar_analise_ia_postgres(linha, analise, provedor_ia)
        print(
            f"Postgres {indice}/{len(linhas)} - ronda_id={valor(linha, 'ronda_id')}: "
            f"{analise[COLUNA_ANALISADA]}"
        )

    print(f"Analises de IA salvas no Postgres: {len(linhas)}")


def criar_parser() -> argparse.ArgumentParser:
    carregar_env_automatico()

    parser = argparse.ArgumentParser(description="Agente de IA para validar justificativa + foto de rondas.")
    parser.add_argument("--entrada", help="CSV gerado pelo auditor ou exportado do BI")
    parser.add_argument("--saida", help="Arquivo XLSX final com a coluna 'analisada por IA'")
    parser.add_argument("--postgres", action="store_true", help="Le pendencias do Postgres e grava em dbo.analise_ia")
    parser.add_argument("--execucao-id", type=int, help="No modo --postgres, analisa apenas uma execucao especifica")
    parser.add_argument("--limite", type=int, help="Limita a quantidade de linhas analisadas, util para teste")
    parser.add_argument(
        "--nao-baixar-links",
        action="store_true",
        help="Envia image_url direto para a IA em vez de baixar e enviar como base64",
    )
    parser.add_argument(
        "--provedor-ia",
        choices=["openai", "ollama"],
        default=(os.getenv("IA_PROVIDER") or os.getenv("AI_PROVIDER") or "openai").lower(),
        help="Provedor usado para analisar justificativa + imagem",
    )
    return parser


def main() -> None:
    parser = criar_parser()
    args = parser.parse_args()

    if args.postgres:
        analisar_postgres(
            limite=args.limite,
            execucao_id=args.execucao_id,
            baixar_links=not args.nao_baixar_links,
            provedor_ia=args.provedor_ia,
        )
        return

    if not args.entrada or not args.saida:
        parser.error("informe --entrada e --saida, ou use --postgres")

    analisar_csv(
        entrada=Path(args.entrada),
        saida=Path(args.saida),
        limite=args.limite,
        baixar_links=not args.nao_baixar_links,
        provedor_ia=args.provedor_ia,
    )


if __name__ == "__main__":
    main()
