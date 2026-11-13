"""Validações e leitura segura das entradas do usuário.

Tem dois tipos de função:
- validar_...: só conferem o texto e devolvem True ou False
  (cartão SUS com 15 dígitos, data/hora DD/MM/AAAA HH:MM, opção de menu).
- ler_...: fazem a pergunta e repetem até o usuário digitar algo válido
  (opção de menu, S/N, texto não vazio, cartão SUS, inteiro num intervalo
  e data/hora, que aceita ENTER vazio para voltar ao relógio real).

Assim o resto do programa já recebe os dados corretos e não quebra
com entradas erradas.
"""

from datetime import datetime

FORMATO_DIGITADO = "%d/%m/%Y %H:%M"

#cns = cartao nacional de saúde
def validar_cns(texto: str) -> bool:
    """Cartão SUS válido = exatamente 15 dígitos (ignora espaços nas pontas)."""
    texto = texto.strip()
    return texto.isdigit() and len(texto) == 15


def validar_data_hora(texto: str) -> bool:
    """Confere se o texto está no formato DD/MM/AAAA HH:MM e é uma data real."""
    try:
        datetime.strptime(texto.strip(), FORMATO_DIGITADO)
        return True
    except ValueError:
        return False


def validar_opcao(texto: str, validas: tuple) -> bool:
    """True se a opção digitada está entre as opções permitidas."""
    return texto.strip() in validas


def ler_opcao(validas: tuple) -> str:
    """Pede uma opção e repete até o usuário digitar uma válida."""
    while True:
        opcao = input("Opção: ").strip()
        if validar_opcao(opcao, validas):
            return opcao
        print(f"Opção inválida. Escolha entre: {', '.join(validas)}")


def ler_sn(pergunta: str) -> bool:
    """Faz uma pergunta S/N. Devolve True para sim e False para não."""
    while True:
        resposta = input(f"{pergunta} (S/N): ").strip().upper()
        if resposta == "S":
            return True
        elif resposta == "N":
            return False
        print("Responda com S ou N.")


def ler_texto(pergunta: str) -> str:
    """Lê um texto e repete enquanto estiver vazio."""
    while True:
        texto = input(f"{pergunta}: ").strip()
        if texto != "":
            return texto
        print("O campo não pode ficar vazio.")


def ler_cns() -> str:
    """Lê o cartão SUS e repete até ter 15 números."""
    while True:
        cns = input("Cartão SUS (15 números): ").strip()
        if validar_cns(cns):
            return cns
        print("Cartão SUS deve ter 15 números.")


def ler_inteiro(pergunta: str, minimo: int, maximo: int) -> int:
    """Lê um número inteiro dentro do intervalo [minimo, maximo]."""
    while True:
        texto = input(f"{pergunta} ({minimo}-{maximo}): ").strip()
        if texto.isdigit() and minimo <= int(texto) <= maximo:
            return int(texto)
        print(f"Digite um número entre {minimo} e {maximo}.")


def ler_data_hora(pergunta: str) -> str:
    """Lê data/hora no formato DD/MM/AAAA HH:MM. ENTER vazio devolve texto vazio."""
    while True:
        texto = input(f"{pergunta} (DD/MM/AAAA HH:MM, ENTER = relógio real): ").strip()
        if texto == "" or validar_data_hora(texto):
            return texto
        print("Formato inválido. Exemplo: 10/11/2026 08:00")
