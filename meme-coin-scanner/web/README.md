# Rugsense Scanner (web)

SPA de escritorio que monitorea meme coins en tiempo real con un pipeline
de seguridad on-chain. React + Vite + Tailwind CSS + lucide-react.

![stack](https://img.shields.io/badge/React-18-61dafb) ![stack](https://img.shields.io/badge/Vite-7-646cff) ![stack](https://img.shields.io/badge/Tailwind-3.4-38bdf8)

> **Esto no es asesoramiento financiero.** Las meme coins son de riesgo
> extremo: la mayoría no tiene fundamentales y muchas son rug pulls
> deliberados. Un DegenScore alto no es una recomendación de compra, y la
> ausencia de alertas no prueba que un token sea seguro.

## Arrancar

```bash
cd meme-coin-scanner/web
npm install
npm run dev      # http://localhost:5173
```

| Comando | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo con HMR |
| `npm run build` | Build de producción en `dist/` |
| `npm run preview` | Sirve el build local |
| `npm run artifact` | Build + reescribe `dist/index.html` como página publicable (`dist/artifact.html`) |

## Módulos

**Dashboard.** Panel superior con cuatro métricas globales (tokens
escaneados, alertas de rugpull, tokens sin fallos, volumen monitoreado),
buscador por dirección de contrato / mint / ticker, y filtros rápidos por
red (Solana, Base, Ethereum).

**Pipeline de seguridad** (`src/lib/securityRules.js`). Seis controles,
cada uno con umbral explícito:

| Control | Umbral | Fallo significa |
|---|---|---|
| Liquidez bloqueada | LP quemado/bloqueado ≥ 95% | El creador aún puede retirar la liquidez |
| Contrato vendible | Simulación de venta correcta | Honeypot: compras pero no puedes vender |
| Impuestos de tx | Compra y venta < 5% | El contrato se queda parte de cada operación |
| Autoridad de minteo | Revocada | Se puede acuñar supply nuevo y diluirte |
| Autoridad de congelación | Revocada | Te pueden congelar los tokens |
| Concentración top 10 | ≤ 20% del supply | Unas pocas wallets pueden hundir el precio |

Cada control devuelve `pass`, `fail` o **`unknown`**. `unknown` es un
estado de primera clase y nunca se pliega a `pass`: la API de seguridad
devuelve listas de holders vacías, datos de LP vacíos y campos de tax
vacíos para tokens que no ha indexado, y leer eso como «0% de tax, 0% de
concentración» convertiría la falta de datos en un certificado de
seguridad — el peor fallo posible en un detector de rugs.

**DegenScore** (`src/lib/degenScore.js`). 0–100. Un honeypot lo fija en 0;
cada control fallido resta su peso, cada control sin datos resta un cuarto
de ese peso, y las condiciones de mercado (liquidez frente a market cap,
actividad real) solo ajustan el resultado. Bandas: ≥70 SEGURO, 40–69
PRECAUCIÓN, <40 PELIGRO.

**Tabla de monitoreo.** Ordenable por cualquier columna y paginada, con
edad legible («Hace 12 minutos»), market cap, liquidez, volumen, contador
de transacciones de 5m que avanza en vivo, y el badge de DegenScore.

**Simulador de feed** (`src/hooks/useTokenFeed.js` + `src/data/tokenFactory.js`).
Un `useEffect` con intervalo configurable (LENTO / NORMAL / TURBO) genera
pares recién creados, los pasa por el pipeline y los aprueba o descarta en
vivo con animación de entrada.

## Origen de los datos

La tabla **arranca con un escaneo real**: datos de mercado de
[DexScreener](https://docs.dexscreener.com/api/reference) y banderas de
seguridad de [GoPlus Security](https://docs.gopluslabs.io/reference/token-security-api),
capturados por `scripts/export_seed.py` del paquete Python de este mismo
repo:

```bash
cd meme-coin-scanner
python scripts/export_seed.py --limit 18 --chain solana --chain base --chain ethereum
```

Esas filas no llevan etiqueta. Las que genera el simulador se marcan
**`sim`** en la tabla, porque el websocket de pares nuevos exige llave
privada de un proveedor de pago. Ninguna fila simulada se presenta como
dato escaneado.

## Estructura

```
web/
├── index.html
├── vite.config.js · tailwind.config.js · postcss.config.js
├── scripts/make-artifact.mjs      # build -> página publicable
└── src/
    ├── App.jsx                    # composición del dashboard
    ├── lib/
    │   ├── securityRules.js       # los seis controles + veredicto
    │   ├── degenScore.js          # puntuación 0-100 y bandas
    │   ├── chains.js              # identidad visual de cada red
    │   └── format.js              # USD, precios, edades en español
    ├── hooks/
    │   ├── useTokenFeed.js        # streaming, métricas, pausa/velocidad
    │   └── useTokenTable.js       # filtrado, orden y paginación
    ├── data/
    │   ├── seedTokens.js          # escaneo real (generado)
    │   └── tokenFactory.js        # generador de pares simulados
    └── components/                # Header, MetricsPanel, Toolbar,
                                   # TokenTable/Row, SecurityChecklist,
                                   # PipelineSummary, FeedTicker, TokenDetail
```
