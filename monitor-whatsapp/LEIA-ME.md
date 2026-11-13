# Monitor de Demandas

Fica rodando minimizado, **olha os grupos de WhatsApp que você escolher** e, a cada demanda que chega:
- baixa as fotos e cria a pasta `MARCA REFERÊNCIA` com elas dentro;
- anota na **lista da demanda do dia** (na tela e em arquivo `.txt`, que abre em qualquer editor).

A cada item salvo, aparece um **aviso no canto da tela** (mesmo com tudo minimizado) dizendo de qual grupo veio, a marca, a referência e quantas fotos. Dá para desligar o aviso ou o som em Configurações.

Ele **só lê**: nunca envia mensagem e nunca apaga nada.

## Onde ficam as pastas
Você escolhe uma **pasta principal**. Dentro dela o programa cria **uma pasta para cada grupo**, e dentro dela uma por dia. Os grupos nunca se misturam:

```
Demandas (pasta principal)/
├── PROGRAMAÇÃO/                  <- um grupo (emojis do nome são tirados)
│   └── 13-11-2026/
│       ├── BEIRA RIO 8513.115/   foto_01.jpg ...
│       ├── DAKOTA rosa Choque/
│       ├── _Conferir .../        <- o que o programa não soube identificar
│       ├── lista_do_dia.txt
│       └── lista_do_dia.json
└── FOTOS DA CAIXA/
    └── 13-11-2026/ ...
```

## Três tipos (quantos grupos e conversas você quiser)
- **Grupo A (foto + marca + referência na legenda):** o programa separa a marca da referência pela legenda
  (`BEIRA RIO 8513.115` → pasta `BEIRA RIO 8513.115`). Se a foto vier sem legenda, ele espera o texto por 2 minutos; se não vier, vai para `_Conferir`.
- **Grupo B (só a foto da caixa):** o programa **lê a etiqueta** (na sua máquina, sem internet) e acha a referência (e a marca,
  se aparecer). Foto que não deu para ler vai para `_Conferir`, marcada na lista.

- **Conversa individual:** em vez de fotos, o programa salva **o texto do que a pessoa escrever** em `mensagens.txt`
  (`[09:41] bom dia, segue a lista...`). Como é salvo na hora, **fica guardado mesmo que a pessoa apague a mensagem depois**.
  Só entram as mensagens dela (não as suas), de hoje em diante. **Fotos** que a pessoa mandar também são salvas, na pasta `fotos`, com o **nome do contato** no arquivo (`Maria Silva - foto_01.jpg`). Foto sem texto aparece como `[foto]` no `mensagens.txt`; áudio/arquivo como `[mídia sem texto]`.
  Aviso: o monitor passa pelas conversas uma de cada vez (alguns segundos entre uma e outra); se alguém apagar uma mensagem em poucos segundos, ele pode não ter lido.

**Por padrão o monitor salva só o que chegar DEPOIS de iniciar** e ignora todo o histórico da conversa. Se você quiser que ele também leia o que já chegou hoje, ligue "Ler também o que já chegou hoje" em Configurações: nesse caso, ao iniciar, ele sobe cada conversa até o começo do dia e lê tudo.

No **Grupo B** ele também guarda uma cópia de cada foto na pasta `_Todas as fotos`, com o nome do que foi lido (`13h37 - OLYMPIKUS CORRE 2 - foto_01.jpg`, ou `não lida`), para você conferir rápido no fim do dia.

Álbum com "+N" fotos: o programa tenta abrir o álbum e baixar todas. Se não conseguir tudo, avisa na lista ("álbum incompleto").

## Como instalar
Rode o **MonitorDeDemandas-Instalador-1.0.0.exe** (não pede senha de administrador) e siga as telas. Ele cria o atalho no Menu Iniciar e, se você quiser, na Área de Trabalho e para abrir junto com o Windows. Se preferir sem instalar, use o `.zip` portátil.
Se o Windows avisar "O Windows protegeu o computador", clique em **Mais informações** > **Executar assim mesmo** (o programa ainda não tem assinatura digital paga).

## Como usar
1. Abra o `MonitorDeDemandas.exe`. Na aba **Configurações**, escolha a **pasta principal** e adicione os **grupos** (nome igual ao do WhatsApp) com o tipo A ou B.
2. Clique em **Abrir WhatsApp**. Abre uma janela do **Chrome** **só do monitor** (com perfil próprio, sem mexer no seu Chrome; se não achar o Chrome, usa o Edge): entre com o **QR code** do seu número
   (WhatsApp > Aparelhos conectados). Só na primeira vez. O seu atalho do WhatsApp Web e o WhatsApp instalado no Windows **não são mexidos**.
3. Clique em **Iniciar monitor**. Pode minimizar a janela do navegador e a do programa (fechar a janela manda o programa para a **bandeja**, o ícone perto do relógio: clique nele para abrir, ou use o botão direito para pausar, abrir a pasta ou sair; para encerrar de vez use **Sair de vez**).
4. Na aba **Demanda do dia** aparece tudo que chegou, com caixinha de "feito", pasta de cada item e avisos ⚠.

Obs.: o monitor precisa "abrir" cada grupo na janela dele, um de cada vez, para ler as mensagens. Por isso ele usa uma janela separada.

## Tudo é salvo em `.txt` (nada de CSV ou Excel).

## Referência sem a cor (regras por marca)
Algumas marcas têm no fim da referência um código que é só a **cor** (ex.: Pegada `(133) 161-01`, o `-01` é a cor).
Em **Configurações > Regras de referência por marca** você abre um arquivo de texto simples e escreve, por marca, o que cortar no final:

```
PEGADA | -NN        (corta "-01": a pasta fica "PEGADA (133) 161")
```
`N` = um número, `L` = uma letra. Sem regra para a marca, a referência fica completa. Cores diferentes do mesmo modelo caem na **mesma pasta**,
e a referência completa que veio na legenda/etiqueta aparece como observação na lista. A referência pode ser só número, letras e números, ou só nome (ex.: Olympikus `CORRE 2`).
Vamos ajustando as marcas com o tempo.

## Log do dia
Tudo o que acontece (monitor iniciado, itens salvos, erros) fica na aba **Registro do dia** e também no arquivo `_Log/log_DD-MM-AAAA.txt`, dentro da pasta principal, uma linha por evento.

## Se algo não funcionar
Aba **Registro** > **Testar leitura (diagnóstico)** mostra o que o programa enxerga na tela (sem o texto das conversas).
Me mande esse resultado: o WhatsApp muda a tela de vez em quando e eu ajusto.
