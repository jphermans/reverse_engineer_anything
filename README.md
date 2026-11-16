# Reverse Engineer Anything

Agent Zero plugin v0.1.0: de werkbank voor reverse engineering met de leanrea-methode.

## Basis: leanrea

Deze plugin is gemaakt op basis van [leanrea](https://github.com/aicodeking/leanrea), de skill die de agent de reverse-engineering-methode geeft (routeer op magic bytes, werk op een kopie, slice in plaats van lezen, antwoord op evidence). De categorieën van de tool-inventaris en de copy-first werkruimtes volgen direct de leanrea-router en -regels.

## Wat doet deze plugin?

De [leanrea-skill](https://github.com/aicodeking/leanrea) geeft de agent de *methode* om software te reverse engineeren. Deze plugin levert de *werkplek* in de Agent Zero WebUI:

1. **Tool-inventaris** — live overzicht van reverse-engineering-tools in de container, gegroepeerd per leanrea-categorie (basis, native binaries, Electron/JS, mobiel, firmware, WASM, data/netwerk, Go/Rust/.NET, decompilers). Per tool: beschikbaar of niet, wat het doet en bij afwezigheid een installatiehint.
2. **Werkruimtes** — beheerde analyselmappen onder één root (standaard `/a0/usr/workdir/rea`), volgens de leanrea-regel: werk altijd op een kopie. Aanmaken en verwijderen vanuit de WebUI; namen worden gevalideerd en blijven binnen de root.
3. **Historiek** — logboek van workspace-acties en notities (JSONL in de workspace-root), met limiet-instelling en aparte verwijderacties.

De plugin voegt geen analyse-capaciteit toe; de agent voert de analyse zelf uit met de leanrea-skill en de tools in de container. De plugin maakt het werk zichtbaar, herhaalbaar en opruimbaar.

## Installatie

Plugin-map kopiëren naar `/a0/usr/plugins/reverse_engineer_anything/` (of installeren via zip/git in het Plugins-scherm). Na het laden verschijnt de **REA**-knop in de sidebar; daarop opent de werkbank.

De plugin heeft geen externe dependencies, geen credentials en geen achtergrondprocessen. `install()` maakt alleen de standaard workspace-root aan; bij een aangepaste root gebeurt dat automatisch bij eerste gebruik.

## Instellingen (Settings > Developer)

| Instelling | Standaard | Betekenis |
|---|---|---|
| `workspace_root` | `/a0/usr/workdir/rea` | Map waarin werkruimtes worden aangemaakt |
| `history_limit` | `200` (10–2000) | Maximaal aantal bewaarde historiekregels |

## API

| Route | Methode | Functie |
|---|---|---|
| `/api/plugins/reverse_engineer_anything/tools` | GET/POST | Tool-inventaris per categorie (read-only) |
| `/api/plugins/reverse_engineer_anything/workspaces` | GET/POST | Werkruimtes listing (read-only) |
| `/api/plugins/reverse_engineer_anything/workspace` | POST | `create` (name) of `delete` (name + confirm) |
| `/api/plugins/reverse_engineer_anything/history` | GET/POST | Historiek listing (read-only) |
| `/api/plugins/reverse_engineer_anything/history_action` | POST | `note` (text, workspace?), `remove` (id), `clear` (confirm) |

Mutatie-routes gebruiken het standaard CSRF-beleid van Agent Zero; read-only routes staan GET-polling toe.

## Gebruik met de agent

Voorbeeldprompt bij een analyseklus:

> Analyseer deze app met leanrea. Gebruik een werkruimte `mij app-v1` (maak die aan als die nog niet bestaat) en zet al je extracties daarin; log belangrijke bevindingen als notitie in de REA-historiek.

De agent kan de API-routes ook zelf aanroepen om de werkbank bij te werken, en de tool-inventaris raadplegen voordat hij een aanpak kiest.

## Verwijderen

Plugin verwijderen via het Plugins-scherm. De workspace-root (met werkruimtes en historiek) blijft bewust bestaan: dat zijn gebruikersgegevens. Wis zelf `/a0/usr/workdir/rea` als je die niet meer nodig hebt.

## Licentie

MIT — zie [LICENSE](LICENSE).
