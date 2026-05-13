import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


EXECUCAO_ID_RE = re.compile(r"execucao_id=(\d+)")


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Roda o fluxo completo: auditoria, Postgres e opcionalmente analise IA."
    )
    parser.add_argument("--data", help="Data unica da auditoria, no formato AAAA-MM-DD")
    parser.add_argument("--data-inicio", help="Data inicial, no formato AAAA-MM-DD")
    parser.add_argument("--data-fim", help="Data final inclusiva, no formato AAAA-MM-DD")
    parser.add_argument("--entrada", help="CSV com atividades justificadas")
    parser.add_argument("--saida", help="Arquivo de saida. Padrao: saidas/auditoria_<periodo>.xlsx")
    parser.add_argument(
        "--substituir-periodo",
        action="store_true",
        help="Remove execucoes anteriores do mesmo periodo antes de inserir a nova",
    )
    parser.add_argument(
        "--substituir-sobreposicoes",
        action="store_true",
        help="Remove execucoes antigas com periodo sobreposto ao novo antes de inserir a nova",
    )
    parser.add_argument(
        "--rodar-ia",
        action="store_true",
        help="Depois da auditoria, roda o agente IA somente na execucao criada",
    )
    parser.add_argument("--limite-ia", type=int, help="Limita a quantidade de linhas analisadas pela IA")
    parser.add_argument(
        "--provedor-ia",
        choices=["openai", "ollama"],
        help="Provedor usado pelo agente IA. Se omitido, usa IA_PROVIDER do .env",
    )
    parser.add_argument(
        "--nao-baixar-links",
        action="store_true",
        help="No agente IA, envia image_url direto em vez de baixar e enviar como base64",
    )
    parser.add_argument(
        "--campo-periodo",
        choices=["disponibilizacao", "tarefa_disponibilizacao", "inicio", "termino", "prazo", "inicio_real", "execucao"],
        help="Campo usado para filtrar o periodo no SQL Server",
    )
    parser.add_argument("--usar-ia", action="store_true", help="Usa IA de visao dentro do auditor principal")
    parser.add_argument(
        "--ia-em",
        choices=["amarelo", "amarelo-verde", "todos"],
        help="Define quais grupos locais o auditor principal envia para IA",
    )
    parser.add_argument("--sql-server", help="Servidor SQL Server")
    parser.add_argument("--sql-database", help="Nome do banco SQL Server")
    parser.add_argument("--sql-auth", choices=["sql", "windows"], help="Tipo de autenticacao no SQL Server")
    parser.add_argument("--sql-user", help="Usuario SQL Server")
    parser.add_argument("--sql-password-env", help="Nome da variavel de ambiente com a senha SQL Server")
    parser.add_argument("--sql-coluna-cr", help="Coluna do SQL Server usada como CR do contrato. Exemplo: t.CR")
    return parser


def nome_saida_padrao(args: argparse.Namespace) -> Path:
    if args.data:
        sufixo = args.data
    elif args.data_inicio and args.data_fim:
        sufixo = f"{args.data_inicio}_a_{args.data_fim}"
    elif args.entrada:
        sufixo = Path(args.entrada).stem
    else:
        sufixo = "auditoria"
    return Path("saidas") / f"auditoria_{sufixo}.xlsx"


def adicionar_opcional(comando: List[str], nome: str, valor: Optional[str]) -> None:
    if valor:
        comando.extend([nome, valor])


def montar_comando_auditor(args: argparse.Namespace, saida: Path) -> List[str]:
    comando = [
        sys.executable,
        "ronda_auditor.py",
        "--saida",
        str(saida),
        "--salvar-postgres",
    ]

    adicionar_opcional(comando, "--data", args.data)
    adicionar_opcional(comando, "--data-inicio", args.data_inicio)
    adicionar_opcional(comando, "--data-fim", args.data_fim)
    adicionar_opcional(comando, "--entrada", args.entrada)
    adicionar_opcional(comando, "--campo-periodo", args.campo_periodo)
    adicionar_opcional(comando, "--ia-em", args.ia_em)
    adicionar_opcional(comando, "--sql-server", args.sql_server)
    adicionar_opcional(comando, "--sql-database", args.sql_database)
    adicionar_opcional(comando, "--sql-auth", args.sql_auth)
    adicionar_opcional(comando, "--sql-user", args.sql_user)
    adicionar_opcional(comando, "--sql-password-env", args.sql_password_env)
    adicionar_opcional(comando, "--sql-coluna-cr", args.sql_coluna_cr)

    if args.substituir_periodo:
        comando.append("--substituir-periodo")
    if args.substituir_sobreposicoes:
        comando.append("--substituir-sobreposicoes")
    if args.usar_ia:
        comando.append("--usar-ia")

    return comando


def montar_comando_ia(args: argparse.Namespace, execucao_id: int) -> List[str]:
    comando = [
        sys.executable,
        str(Path("agente_IA") / "agente_analise_ia.py"),
        "--postgres",
        "--execucao-id",
        str(execucao_id),
    ]

    if args.limite_ia:
        comando.extend(["--limite", str(args.limite_ia)])
    if args.provedor_ia:
        comando.extend(["--provedor-ia", args.provedor_ia])
    if args.nao_baixar_links:
        comando.append("--nao-baixar-links")

    return comando


def executar(comando: List[str], titulo: str, pasta_projeto: Path) -> str:
    print(f"\n== {titulo} ==")
    print(" ".join(f'"{parte}"' if " " in parte else parte for parte in comando))
    resultado = subprocess.run(
        comando,
        cwd=pasta_projeto,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if resultado.stdout:
        print(resultado.stdout, end="" if resultado.stdout.endswith("\n") else "\n")
    if resultado.stderr:
        print(resultado.stderr, end="" if resultado.stderr.endswith("\n") else "\n", file=sys.stderr)

    if resultado.returncode != 0:
        raise SystemExit(resultado.returncode)

    return resultado.stdout


def extrair_execucao_id(saida_auditor: str) -> int:
    match = EXECUCAO_ID_RE.search(saida_auditor)
    if not match:
        raise RuntimeError("nao consegui encontrar execucao_id na saida do auditor")
    return int(match.group(1))


def validar_args(args: argparse.Namespace) -> None:
    tem_periodo = bool(args.data or (args.data_inicio and args.data_fim))
    if not args.entrada and not tem_periodo:
        raise ValueError("informe --data, ou --data-inicio/--data-fim, ou --entrada")
    if args.substituir_periodo and not tem_periodo:
        raise ValueError("--substituir-periodo exige --data ou --data-inicio/--data-fim")
    if args.substituir_sobreposicoes and not tem_periodo:
        raise ValueError("--substituir-sobreposicoes exige --data ou --data-inicio/--data-fim")


def main() -> None:
    parser = criar_parser()
    args = parser.parse_args()
    try:
        validar_args(args)
    except ValueError as exc:
        parser.error(str(exc))

    pasta_projeto = Path(__file__).resolve().parent
    saida = Path(args.saida) if args.saida else nome_saida_padrao(args)

    comando_auditor = montar_comando_auditor(args, saida)
    saida_auditor = executar(comando_auditor, "Auditoria", pasta_projeto)
    execucao_id = extrair_execucao_id(saida_auditor)
    print(f"Execucao criada: {execucao_id}")

    if args.rodar_ia:
        comando_ia = montar_comando_ia(args, execucao_id)
        executar(comando_ia, "Analise IA", pasta_projeto)

    print("\nPipeline concluido.")
    print(f"Arquivo gerado: {saida}")
    print(f"execucao_id={execucao_id}")


if __name__ == "__main__":
    main()
