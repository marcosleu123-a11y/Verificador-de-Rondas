import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class ExecucaoAuditoria:
    origem: str
    data_inicio: Optional[date]
    data_fim: Optional[date]
    campo_periodo: Optional[str]
    usar_ia: bool
    arquivo_excel: Path


def _valor(linha: Dict[str, object], chave: str) -> Optional[str]:
    valor = linha.get(chave)
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _decimal(linha: Dict[str, object], chave: str) -> Optional[Decimal]:
    texto = _valor(linha, chave)
    if texto is None:
        return None
    try:
        return Decimal(texto.replace(",", "."))
    except InvalidOperation:
        return None


def _inteiro(linha: Dict[str, object], chave: str) -> Optional[int]:
    texto = _valor(linha, chave)
    if texto is None:
        return None
    try:
        return int(texto)
    except ValueError:
        return None


def _conexao_kwargs() -> Dict[str, object]:
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


def _excluir_execucoes_do_periodo(
    cursor,
    sql,
    schema: str,
    execucao: ExecucaoAuditoria,
    substituir_sobreposicoes: bool,
) -> int:
    if substituir_sobreposicoes:
        cursor.execute(
            sql.SQL(
                """
                SELECT id
                FROM {}
                WHERE origem = %s
                  AND campo_periodo IS NOT DISTINCT FROM %s
                  AND data_inicio <= %s
                  AND data_fim >= %s
                """
            ).format(sql.Identifier(schema, "auditoria_execucoes")),
            (
                execucao.origem,
                execucao.campo_periodo,
                execucao.data_fim,
                execucao.data_inicio,
            ),
        )
    else:
        cursor.execute(
            sql.SQL(
                """
                SELECT id
                FROM {}
                WHERE origem = %s
                  AND data_inicio IS NOT DISTINCT FROM %s
                  AND data_fim IS NOT DISTINCT FROM %s
                  AND campo_periodo IS NOT DISTINCT FROM %s
                """
            ).format(sql.Identifier(schema, "auditoria_execucoes")),
            (
                execucao.origem,
                execucao.data_inicio,
                execucao.data_fim,
                execucao.campo_periodo,
            ),
        )
    execucao_ids: List[int] = [linha[0] for linha in cursor.fetchall()]
    if not execucao_ids:
        return 0

    rondas_do_periodo = sql.SQL(
        "SELECT id FROM {} WHERE execucao_id = ANY(%s::bigint[])"
    ).format(sql.Identifier(schema, "rondas_base"))

    cursor.execute(
        sql.SQL("DELETE FROM {} WHERE ronda_id IN ({})").format(
            sql.Identifier(schema, "analise_ia"),
            rondas_do_periodo,
        ),
        (execucao_ids,),
    )
    cursor.execute(
        sql.SQL("DELETE FROM {} WHERE ronda_id IN ({})").format(
            sql.Identifier(schema, "analise_script"),
            rondas_do_periodo,
        ),
        (execucao_ids,),
    )
    cursor.execute(
        sql.SQL("DELETE FROM {} WHERE execucao_id = ANY(%s::bigint[])").format(
            sql.Identifier(schema, "rondas_base")
        ),
        (execucao_ids,),
    )
    cursor.execute(
        sql.SQL("DELETE FROM {} WHERE id = ANY(%s::bigint[])").format(
            sql.Identifier(schema, "auditoria_execucoes")
        ),
        (execucao_ids,),
    )
    return len(execucao_ids)


def salvar_auditoria_postgres(
    linhas: Iterable[Dict[str, object]],
    execucao: ExecucaoAuditoria,
    substituir_periodo: bool = False,
    substituir_sobreposicoes: bool = False,
) -> int:
    try:
        import psycopg
        from psycopg import sql
    except ImportError as exc:
        raise RuntimeError("instale a dependencia psycopg[binary] para salvar no Postgres") from exc

    linhas = list(linhas)
    schema = os.getenv("POSTGRES_SCHEMA", "dbo")
    conexao_kwargs = _conexao_kwargs()

    with psycopg.connect(**conexao_kwargs) as conexao:
        with conexao.cursor() as cursor:
            if substituir_periodo or substituir_sobreposicoes:
                removidas = _excluir_execucoes_do_periodo(
                    cursor,
                    sql,
                    schema,
                    execucao,
                    substituir_sobreposicoes=substituir_sobreposicoes,
                )
                if removidas:
                    print(f"Execucoes anteriores substituidas no Postgres: {removidas}")

            cursor.execute(
                sql.SQL(
                    """
                    INSERT INTO {} (
                        origem,
                        data_inicio,
                        data_fim,
                        campo_periodo,
                        usar_ia,
                        arquivo_excel,
                        total_registros
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """
                ).format(sql.Identifier(schema, "auditoria_execucoes")),
                (
                    execucao.origem,
                    execucao.data_inicio,
                    execucao.data_fim,
                    execucao.campo_periodo,
                    execucao.usar_ia,
                    str(execucao.arquivo_excel),
                    len(linhas),
                ),
            )
            execucao_id = cursor.fetchone()[0]

            for linha in linhas:
                cursor.execute(
                    sql.SQL(
                        """
                        INSERT INTO {} (
                            execucao_id,
                            atividade_id,
                            tarefa_id,
                            contrato_cr,
                            estrutura_id,
                            nivel_03,
                            nivel_04,
                            andar,
                            local,
                            ambiente,
                            qrcode,
                            colaborador,
                            data,
                            data_execucao_inicio,
                            execucao_disponibilizacao,
                            tarefa_disponibilizacao,
                            tarefa_inicio,
                            tarefa_termino,
                            tarefa_prazo,
                            tarefa_nome,
                            checklist_nome,
                            checklist_descricao,
                            justificativa,
                            image_url,
                            image_path,
                            data_justificativa
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        RETURNING id
                        """
                    ).format(sql.Identifier(schema, "rondas_base")),
                    (
                        execucao_id,
                        _valor(linha, "atividade_id"),
                        _valor(linha, "tarefa_id"),
                        _valor(linha, "contrato_cr"),
                        _valor(linha, "estrutura_id"),
                        _valor(linha, "nivel_03"),
                        _valor(linha, "nivel_04"),
                        _valor(linha, "andar"),
                        _valor(linha, "local"),
                        _valor(linha, "ambiente"),
                        _valor(linha, "qrcode"),
                        _valor(linha, "colaborador"),
                        _valor(linha, "data"),
                        _valor(linha, "data_execucao_inicio"),
                        _valor(linha, "execucao_disponibilizacao"),
                        _valor(linha, "tarefa_disponibilizacao"),
                        _valor(linha, "tarefa_inicio"),
                        _valor(linha, "tarefa_termino"),
                        _valor(linha, "tarefa_prazo"),
                        _valor(linha, "tarefa_nome"),
                        _valor(linha, "checklist_nome"),
                        _valor(linha, "checklist_descricao"),
                        _valor(linha, "justificativa"),
                        _valor(linha, "image_url"),
                        _valor(linha, "image_path"),
                        _valor(linha, "data_justificativa"),
                    ),
                )
                ronda_id = cursor.fetchone()[0]

                cursor.execute(
                    sql.SQL(
                        """
                        INSERT INTO {} (
                            ronda_id,
                            grupo,
                            confianca,
                            motivo,
                            brilho_medio,
                            variacao_visual,
                            pixels_escuros,
                            pixels_quase_pretos,
                            nitidez_aproximada,
                            largura,
                            altura
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """
                    ).format(sql.Identifier(schema, "analise_script")),
                    (
                        ronda_id,
                        _valor(linha, "grupo_local") or _valor(linha, "grupo"),
                        _decimal(linha, "confianca_local") or _decimal(linha, "confianca"),
                        _valor(linha, "motivo_local") or _valor(linha, "motivo"),
                        _decimal(linha, "brilho_medio"),
                        _decimal(linha, "variacao_visual"),
                        _decimal(linha, "pixels_escuros"),
                        _decimal(linha, "pixels_quase_pretos"),
                        _decimal(linha, "nitidez_aproximada"),
                        _inteiro(linha, "largura"),
                        _inteiro(linha, "altura"),
                    ),
                )
                analise_script_id = cursor.fetchone()[0]

                if _valor(linha, "grupo_ia") or _valor(linha, "motivo_ia") or _valor(linha, "erro_ia"):
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
                                erro,
                                provedor_ia,
                                modelo_ia
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                        ).format(sql.Identifier(schema, "analise_ia")),
                        (
                            ronda_id,
                            analise_script_id,
                            _valor(linha, "grupo_ia"),
                            _valor(linha, "grupo_ia"),
                            _decimal(linha, "confianca_ia"),
                            _valor(linha, "motivo_ia"),
                            _valor(linha, "erro_ia"),
                            os.getenv("IA_PROVIDER", "openai"),
                            os.getenv("OPENAI_MODEL") or os.getenv("OLLAMA_MODEL"),
                        ),
                    )

            cursor.execute(
                sql.SQL("UPDATE {} SET finalizado_em = NOW() WHERE id = %s").format(
                    sql.Identifier(schema, "auditoria_execucoes")
                ),
                (execucao_id,),
            )

    return execucao_id
