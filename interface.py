import os


def limpar_tela() -> None:
    """Limpa o terminal (cls no Windows, clear no Linux/Mac)."""
    os.system("cls" if os.name == "nt" else "clear")

def pausar() -> None:
    """Espera o usuário apertar ENTER para ele conseguir ler a tela."""
    input("\nPressione ENTER para continuar...")


def titulo(texto: str) -> None:
    """Imprime um título destacado entre linhas."""
    linha = "=" * 60
    print(linha)
    print(f"  {texto}")
    print(linha)


def mostrar_tabela(colunas: tuple, linhas: list) -> None:
    """Imprime uma tabela com cabeçalho e separador.
    colunas: tupla de pares (nome, largura). Ex.: (("ID", 4), ("Nome", 20))
    linhas: lista de tuplas, uma por linha, na mesma ordem das colunas.
    """
    cabecalho = ""
    for nome, largura in colunas:
        cabecalho += f"{nome:<{largura}} "
    print(cabecalho)
    print("-" * len(cabecalho))
    for linha in linhas:
        texto = ""
        posicao = 0
        for nome, largura in colunas:
            texto += f"{linha[posicao]!s:<{largura}} "
            posicao += 1
        print(texto)
    print()
