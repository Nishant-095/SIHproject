export const formatNumber = (value: string | number | null, digits = 1) =>
  value === null ? "Not available" : new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits }).format(Number(value));

export const formatCurrency = (value: string | number | null) =>
  value === null ? "Not available" : new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value));

export const formatDate = (value: string | null) =>
  value === null ? "Not available" : new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));

export const formatDateTime = (value: string | null) =>
  value === null ? "Not available" : new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));

export function percentChange(current: string | null, previous: string | null) {
  if (current === null || previous === null || Number(previous) === 0) return null;
  return ((Number(current) - Number(previous)) / Number(previous)) * 100;
}

export const formatAdvanceWindow = (value: string) =>
  value.startsWith("T_PLUS_") ? value.replace("T_PLUS_", "T+") : value.replace(/^T/, "T+");
