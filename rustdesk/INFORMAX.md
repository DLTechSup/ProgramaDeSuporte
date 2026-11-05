# Suporte Informax — duas edições

O mesmo código gera dois programas, escolhidos na compilação:

| Edição | Quem usa | Comportamento |
|---|---|---|
| `informax-tech` | Técnico (você) | Só conecta em outras máquinas. Não recebe conexões. |
| `informax-client` | Cliente | Só recebe conexões: mostra ID e senha. Não mostra tela de conexão. |

Compilar (Windows, Flutter):

```bash
python3 build.py --flutter --feature informax-tech
python3 build.py --flutter --feature informax-client
```

Implementação: `src/informax.rs` define o modo (`conn-type`) no início do programa,
e a interface já esconde os painéis correspondentes.
Licença: AGPL-3.0 (herdada do RustDesk) — veja `LICENCE`.

## Compilação automática (GitHub Actions)

O arquivo `.github/workflows/build-windows.yml` (na raiz do repositório) compila as duas edições
para Windows 64 bits. Rode em **Actions > Build Suporte Informax (Windows) > Run workflow**
(também roda a cada push em `rustdesk/`). Os `.zip` ficam em **Artifacts** ao final.

Observação: o arquivo executável interno continua `rustdesk.exe`; o nome "Suporte Informax"
aparece na janela e nas propriedades do arquivo.
