# Executar .py

Depois de instalado, **dar dois cliques em qualquer arquivo `.py`** abre um console, roda o script, mostra tudo
que ele imprime (e os erros, se houver) e espera você apertar **Enter** antes de fechar — assim dá para ler
o resultado, em vez da janela sumir na hora.

## Como instalar
Rode o **ExecutarPy-Instalador-1.0.0.exe** (não pede senha de administrador). Deixe marcada a opção
**"Associar arquivos .py a este programa"**. Se o Windows avisar "O Windows protegeu o computador", clique em
**Mais informações** > **Executar assim mesmo** (o programa ainda não tem assinatura digital paga).

Precisa ter o **Python já instalado** (python.org, marcando "Add python.exe to PATH"). O Executar .py não
substitui o Python, só abre o console e chama o Python certo para rodar o script — inclusive dentro de um
ambiente virtual (venv), se o script indicar isso no shebang.

## Como usar
Dois cliques no `.py`. Só isso. Se o script usar `input()`, a janela espera você digitar normalmente.

## Desfazer a associação
A instalação guarda o que abria os `.py` antes. Para voltar ao que era:
- **Sem desinstalar:** Menu Iniciar → **Desfazer associação com .py**.
- **Desinstalando:** o Windows já restaura sozinho a associação anterior.

## Observações
- Só muda o que acontece ao **dar duplo clique**. Rodar `python arquivo.py` pelo terminal continua igual.
- A associação é só para o seu usuário (não mexe nos outros usuários do computador).
- Se outro programa (uma IDE, por exemplo) já tiver associado o `.py` a si mesmo, o instalador assume o lugar
  dele; use "Desfazer associação" para devolver.
