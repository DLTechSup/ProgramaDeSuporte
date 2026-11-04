# Informax Suporte — duas edições

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
