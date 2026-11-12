# Separador de fotos por marca e referência

Lê (OCR) a etiqueta que aparece em cada foto de calçado, descobre **marca** e **referência**
e copia as fotos para pastas `Marca - Referência` dentro da própria pasta escolhida.
Os originais **não** são movidos.

Exemplo, depois de rodar:

```
fotos/
├── IMG_001.jpg … (originais, intactos)
├── Beira Rio - 123.456/   (2 fotos)
├── Beira Rio - 987.654/   (2 fotos)
├── Dakota - 555.111/
├── _Nao_identificadas/    (fotos em que não deu para ler marca + referência)
└── relatorio_separacao.csv
```

## Instalação (uma vez)

1. Instale o Python 3.9+ (python.org; marque "Add to PATH").
2. No terminal, dentro desta pasta: `pip install -r requirements.txt`

## Uso

- `python separador.py` abre a janela: escolha a pasta e clique em **Separar fotos**.
- `python separador.py "C:\caminho\fotos"` roda direto, sem janela.

Roda 100% local (o primeiro uso carrega o modelo de OCR). Pode rodar de novo na mesma pasta:
as subpastas criadas são ignoradas na leitura.

## Ajustes

- **Marca nova**: adicione uma linha em `marcas.txt` (`Nome | apelido | outro apelido`).
- Fotos com `123.456` e `123-456` caem na mesma pasta (pontuação é ignorada).
- Confira `relatorio_separacao.csv` e a pasta `_Nao_identificadas` — fotos tremidas ou com
  etiqueta cortada podem não ser lidas.

## Testes

`pip install pytest && pytest`
