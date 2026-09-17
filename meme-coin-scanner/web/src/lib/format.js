const USD_UNITS = [
  { limit: 1e9, suffix: "B" },
  { limit: 1e6, suffix: "M" },
  { limit: 1e3, suffix: "K" },
];

export function formatUsd(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  for (const { limit, suffix } of USD_UNITS) {
    if (abs >= limit) return `$${(value / limit).toFixed(abs >= limit * 100 ? 0 : 1)}${suffix}`;
  }
  return `$${value.toFixed(0)}`;
}

export function formatPrice(value) {
  if (!value) return "—";
  if (value >= 1) return `$${value.toFixed(4)}`;
  if (value >= 0.0001) return `$${value.toFixed(6)}`;
  return `$${value.toExponential(2)}`;
}

export function formatPct(value, { sign = true, digits = 1 } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const prefix = sign && value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}%`;
}

export function formatNumber(value) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("es-ES").format(Math.round(value));
}

/** "Hace 12 minutos" — the age reading the spec asks for. */
export function formatAge(ageMinutes) {
  if (ageMinutes === null || ageMinutes === undefined) return "Desconocida";
  if (ageMinutes < 1) return "Recién creado";
  if (ageMinutes < 60) {
    return `Hace ${Math.round(ageMinutes)} ${Math.round(ageMinutes) === 1 ? "minuto" : "minutos"}`;
  }
  const hours = ageMinutes / 60;
  if (hours < 24) {
    const rounded = Math.floor(hours);
    return `Hace ${rounded} ${rounded === 1 ? "hora" : "horas"}`;
  }
  const days = Math.floor(hours / 24);
  return `Hace ${days} ${days === 1 ? "día" : "días"}`;
}

/** Compact age for dense table cells: 4m, 3h, 12d. */
export function formatAgeShort(ageMinutes) {
  if (ageMinutes === null || ageMinutes === undefined) return "—";
  if (ageMinutes < 60) return `${Math.max(1, Math.round(ageMinutes))}m`;
  if (ageMinutes < 1440) return `${Math.floor(ageMinutes / 60)}h`;
  return `${Math.floor(ageMinutes / 1440)}d`;
}

export function shortAddress(address) {
  if (!address) return "—";
  if (address.length <= 12) return address;
  return `${address.slice(0, 5)}…${address.slice(-4)}`;
}

export function formatClock(date) {
  return date.toLocaleTimeString("es-ES", { hour12: false });
}
