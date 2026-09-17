/**
 * The security pipeline every token is put through.
 *
 * Each rule returns one of four states. `unknown` is a first-class result,
 * never folded into `pass`: the upstream security API returns empty holder
 * lists, empty LP data and empty tax fields for tokens it has not indexed,
 * and reading those as "0% tax, 0% concentration" would turn missing data
 * into a clean bill of health.
 */

export const THRESHOLDS = {
  minLpLockedPct: 95,
  maxTaxPct: 5,
  maxTop10Pct: 20,
};

export const STATUS = {
  PASS: "pass",
  FAIL: "fail",
  UNKNOWN: "unknown",
};

/** Weight each rule carries in the DegenScore penalty. */
const WEIGHTS = {
  honeypot: 100,
  liquidity: 30,
  mint: 20,
  freeze: 15,
  holders: 20,
  taxes: 15,
};

function ruleLiquidity(security) {
  const pct = security.lpLockedPct;
  if (pct === null || pct === undefined) {
    return {
      status: STATUS.UNKNOWN,
      detail: "Sin datos de LP",
      hint: "No se pudo verificar si la liquidez está bloqueada o quemada.",
    };
  }
  const pass = pct >= THRESHOLDS.minLpLockedPct;
  return {
    status: pass ? STATUS.PASS : STATUS.FAIL,
    detail: `${pct.toFixed(1)}% bloqueado/quemado`,
    hint: pass
      ? "La liquidez no se puede retirar del pool."
      : `Por debajo del mínimo del ${THRESHOLDS.minLpLockedPct}%: el creador aún puede retirar liquidez.`,
  };
}

function ruleHoneypot(security) {
  if (security.isHoneypot === true) {
    return {
      status: STATUS.FAIL,
      detail: "Honeypot detectado",
      hint: "La simulación de venta falla: podrías comprar y no poder vender.",
    };
  }
  if (security.isHoneypot === false) {
    return {
      status: STATUS.PASS,
      detail: "Venta simulada correcta",
      hint: "La simulación de compra/venta se ejecuta sin bloqueos.",
    };
  }
  return {
    status: STATUS.UNKNOWN,
    detail: "Sin simulación",
    hint: "La simulación de honeypot no está disponible para esta red.",
  };
}

function ruleTaxes(security) {
  const { buyTaxPct, sellTaxPct } = security;
  if (buyTaxPct === null || sellTaxPct === null || buyTaxPct === undefined || sellTaxPct === undefined) {
    return {
      status: STATUS.UNKNOWN,
      detail: "Impuestos sin reportar",
      hint: "No hay datos de tax de compra/venta para este contrato.",
    };
  }
  const worst = Math.max(buyTaxPct, sellTaxPct);
  const pass = worst < THRESHOLDS.maxTaxPct;
  return {
    status: pass ? STATUS.PASS : STATUS.FAIL,
    detail: `Compra ${buyTaxPct.toFixed(1)}% · Venta ${sellTaxPct.toFixed(1)}%`,
    hint: pass
      ? `Ambos por debajo del ${THRESHOLDS.maxTaxPct}%.`
      : `Supera el límite del ${THRESHOLDS.maxTaxPct}%: el contrato se queda parte de cada operación.`,
  };
}

function ruleRevoked(value, { label, activeHint, revokedHint }) {
  if (value === true) {
    return { status: STATUS.PASS, detail: `${label} revocada`, hint: revokedHint };
  }
  if (value === false) {
    return { status: STATUS.FAIL, detail: `${label} ACTIVA`, hint: activeHint };
  }
  return {
    status: STATUS.UNKNOWN,
    detail: `${label} sin verificar`,
    hint: "El estado de la autoridad no fue reportado.",
  };
}

function ruleHolders(security) {
  const pct = security.top10HoldersPct;
  if (pct === null || pct === undefined) {
    return {
      status: STATUS.UNKNOWN,
      detail: "Distribución sin indexar",
      hint: "No hay lista de holders disponible para este token.",
    };
  }
  const pass = pct <= THRESHOLDS.maxTop10Pct;
  return {
    status: pass ? STATUS.PASS : STATUS.FAIL,
    detail: `Top 10 = ${pct.toFixed(1)}% del supply`,
    hint: pass
      ? "Supply repartido entre muchas wallets."
      : `Supera el ${THRESHOLDS.maxTop10Pct}%: unas pocas wallets pueden hundir el precio.`,
  };
}

/**
 * Run every rule over a token's security payload.
 * Returns an ordered array so the UI renders a stable checklist.
 */
export function evaluateSecurity(security = {}) {
  return [
    { id: "liquidity", label: "Liquidez bloqueada", weight: WEIGHTS.liquidity, ...ruleLiquidity(security) },
    { id: "honeypot", label: "Contrato vendible", weight: WEIGHTS.honeypot, ...ruleHoneypot(security) },
    { id: "taxes", label: "Impuestos de tx", weight: WEIGHTS.taxes, ...ruleTaxes(security) },
    {
      id: "mint",
      label: "Autoridad de minteo",
      weight: WEIGHTS.mint,
      ...ruleRevoked(security.mintRevoked, {
        label: "Mint",
        activeHint: "El creador puede acuñar supply nuevo y diluir a los holders.",
        revokedHint: "El supply es fijo, nadie puede acuñar más.",
      }),
    },
    {
      id: "freeze",
      label: "Autoridad de congelación",
      weight: WEIGHTS.freeze,
      ...ruleRevoked(security.freezeRevoked, {
        label: "Freeze",
        activeHint: "El creador puede congelar tus tokens y dejarte sin salida.",
        revokedHint: "Nadie puede congelar los balances.",
      }),
    },
    { id: "holders", label: "Concentración top 10", weight: WEIGHTS.holders, ...ruleHolders(security) },
  ];
}

export function countByStatus(checks) {
  return checks.reduce(
    (acc, check) => {
      acc[check.status] += 1;
      return acc;
    },
    { pass: 0, fail: 0, unknown: 0 }
  );
}

/**
 * The pipeline's verdict. A honeypot or unlocked liquidity is an outright
 * rejection; anything with open questions lands in manual review rather
 * than being approved by default.
 */
export function verdictFor(checks) {
  const failed = checks.filter((c) => c.status === STATUS.FAIL);
  const critical = failed.some((c) => c.id === "honeypot" || c.id === "liquidity" || c.id === "mint");

  if (critical) return { id: "rejected", label: "RECHAZADO", tone: "danger" };
  if (failed.length > 0) return { id: "review", label: "REVISAR", tone: "caution" };
  if (checks.some((c) => c.status === STATUS.UNKNOWN)) {
    return { id: "partial", label: "PARCIAL", tone: "info" };
  }
  return { id: "approved", label: "APROBADO", tone: "neon" };
}
