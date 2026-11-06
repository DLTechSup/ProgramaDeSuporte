# Automação WhatsApp — Demanda do Dia

Projeto novo, separado do Suporte Informax (`../rustdesk`).

Monitora o WhatsApp Web (somente leitura), baixa as fotos dos álbuns de lançamento,
cria a pasta `MARCA\MARCA REFERÊNCIA` e mantém uma lista da demanda do dia com dois OKs
por produto: **Site** e **Atacado**.

## Situação

- `PLANO.md` — plano completo (problema, pastas, regras de legenda, arquitetura,
  interface, testes). É a fonte da verdade do projeto.
- **Falta** o protótipo `demanda_whatsapp.py` (versão 5) e os arquivos
  `iniciar.bat` e `criar_exe.bat`. Eles não vieram junto com o plano; só o texto veio.
  Quando você colocar esses arquivos nesta pasta, o trabalho segue a seção 6 do plano.

## Ordem de trabalho (seção 6 do plano)

1. Interface bonita (customtkinter), legível num canto da tela (~360 px).
2. Integração com o Note Deck (precisa ler o código do Note Deck na máquina do DLTechSup).
3. Gerar o `.exe` com PyInstaller.
4. Testar no WhatsApp Web real (roteiro na seção 6.4; ponto mais incerto: contagem de
   fotos do álbum com `+N`).

## Regras que não podem ser quebradas

- Tudo em português do Brasil.
- **Nunca enviar** mensagem no WhatsApp.
- **Nunca apagar** pastas ou fotos do usuário (o ✕ só tira da lista).
- A pasta principal das marcas é a fonte da verdade.
