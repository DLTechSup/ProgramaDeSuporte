# Monitor de Demandas

Fica rodando minimizado, **olha os grupos de WhatsApp que você escolher** e, a cada demanda que chega:
- baixa as fotos e cria a pasta `MARCA REFERÊNCIA` com elas dentro;
- anota na **lista da demanda do dia** (na tela e em arquivo `.csv`, que abre no Excel).

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
│       ├── lista_do_dia.csv
│       └── lista_do_dia.json
└── FOTOS DA CAIXA/
    └── 13-11-2026/ ...
```

## Dois tipos de grupo
- **Grupo A (foto + marca + referência na legenda):** o programa separa a marca da referência pela legenda
  (`BEIRA RIO 8513.115` → pasta `BEIRA RIO 8513.115`). Se a foto vier sem legenda, ele espera o texto por 2 minutos; se não vier, vai para `_Conferir`.
- **Grupo B (só a foto da caixa):** o programa **lê a etiqueta** (na sua máquina, sem internet) e acha a referência (e a marca,
  se aparecer). Foto que não deu para ler vai para `_Conferir`, marcada na lista.

Álbum com "+N" fotos: o programa tenta abrir o álbum e baixar todas. Se não conseguir tudo, avisa na lista ("álbum incompleto").

## Como usar
1. Abra o `MonitorDeDemandas.exe`. Na aba **Configurações**, escolha a **pasta principal** e adicione os **grupos** (nome igual ao do WhatsApp) com o tipo A ou B.
2. Clique em **Abrir WhatsApp**. Abre uma janela de navegador (Edge) **só do monitor**: entre com o **QR code** do seu número
   (WhatsApp > Aparelhos conectados). Só na primeira vez. O seu atalho do WhatsApp Web e o WhatsApp instalado no Windows **não são mexidos**.
3. Clique em **Iniciar monitor**. Pode minimizar a janela do navegador e a do programa (fechar o programa só minimiza; para encerrar use **Sair de vez**).
4. Na aba **Demanda do dia** aparece tudo que chegou, com caixinha de "feito", pasta de cada item e avisos ⚠.

Obs.: o monitor precisa "abrir" cada grupo na janela dele, um de cada vez, para ler as mensagens. Por isso ele usa uma janela separada.

## Se algo não funcionar
Aba **Registro** > **Testar leitura (diagnóstico)** mostra o que o programa enxerga na tela (sem o texto das conversas).
Me mande esse resultado: o WhatsApp muda a tela de vez em quando e eu ajusto.
