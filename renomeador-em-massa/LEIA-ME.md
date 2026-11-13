# Renomeador em Massa

Fica na **bandeja do Windows** (perto do relógio). Selecione arquivos no Explorador, aperte **Ctrl+Alt+R**, digite um nome e confirme:
todos viram `nome 01`, `nome 02`, `nome 03`... na ordem certa. Depois aparece um aviso no canto da tela com o botão **Desfazer**.

## Como instalar
Rode o **RenomeadorEmMassa-Instalador-1.0.0.exe** (não pede senha de administrador). Ele pode iniciar junto com o Windows.
Se o Windows avisar "O Windows protegeu o computador", clique em **Mais informações** > **Executar assim mesmo** (o programa ainda não tem assinatura digital paga).

## Como usar
1. No Explorador de Arquivos, selecione as fotos (ou quaisquer arquivos).
2. Aperte **Ctrl+Alt+R**. A janela abre já pronta para digitar o nome (**Enter** renomeia, **Esc** cancela).
3. Veja a **prévia** do antes e depois. Se estiver certo, **Enter**.
Se o atalho for apertado sem nada selecionado no Explorador, o programa abre uma janela para você escolher os arquivos.

## O que ele faz de útil
- **Continua a numeração:** se a pasta já tem `branco 01` a `branco 07`, o próximo grupo começa em `branco 08` (dá para desligar ou escolher o número inicial).
- **Ordem certa:** por data do arquivo, pela **data em que a foto foi tirada**, pelo nome (1, 2, 10...) ou pela ordem da seleção.
- **Zeros** (`01`), **separador** (espaço, traço, sublinhado ou nenhum) e extensão em minúsculas.
- **Nomes recentes** em botões (`branco`, `preto`...) para repetir com um clique.
- **Seguro:** nunca sobrescreve outro arquivo; se algo falhar, volta tudo como estava; e o **Desfazer** funciona até depois de fechar o programa (também pelo menu da bandeja).
- **Atalho configurável:** clique com o botão direito no ícone da bandeja > Configurações.

Os dados (configuração e histórico de desfazer) ficam em `%APPDATA%\RenomeadorEmMassa`.
