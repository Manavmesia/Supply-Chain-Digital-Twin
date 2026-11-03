/**
 * Enterprise presentation formatters for Supply Chain Digital Twin.
 * Converts raw UUIDs, timestamps, and currency amounts into clean, branded enterprise labels.
 */

export const CUSTOMER_DIRECTORY: Record<string, { name: string; tier: string; code: string; icon: string }> = {
  '50000000-0000-0000-0000-000000000001': { name: 'Siemens Global Automations', tier: 'Enterprise Tier', code: 'CUST-SIEMENS', icon: '🏢' },
  '50000000-0000-0000-0000-000000000002': { name: 'Tesla Energy & Storage', tier: 'Strategic Partner', code: 'CUST-TESLA', icon: '⚡' },
  '50000000-0000-0000-0000-000000000003': { name: 'Schneider Electric Grid', tier: 'Critical Infra', code: 'CUST-SCHNEIDER', icon: '🏭' },
  '50000000-0000-0000-0000-000000000004': { name: 'Honeywell Aerospace', tier: 'Commercial Tier', code: 'CUST-HONEYWELL', icon: '✈️' },
  '00000000-0000-0000-0000-000000000001': { name: 'Siemens Global Automations', tier: 'Enterprise Tier', code: 'CUST-SIEMENS', icon: '🏢' },
  'cust0000-0000-0000-0000-000000000001': { name: 'Tesla Energy Solutions', tier: 'Enterprise Tier', code: 'CUST-TESLA', icon: '⚡' },
  'cust0000-0000-0000-0000-000000000002': { name: 'Siemens Robotics Global', tier: 'Strategic Partner', code: 'CUST-SIEMENS', icon: '🏢' },
  'cust0000-0000-0000-0000-000000000003': { name: 'Schneider Power Grid', tier: 'Critical Infra', code: 'CUST-SCHNEIDER', icon: '🏭' },
  'cust0000-0000-0000-0000-000000000004': { name: 'Honeywell Industrial', tier: 'Commercial Tier', code: 'CUST-HONEYWELL', icon: '✈️' },
};

export const PRODUCT_DIRECTORY: Record<string, { name: string; sku: string; price: number }> = {
  '30000000-0000-0000-0000-000000000001': { name: 'Industrial Sensor Module', sku: 'ELEC-001', price: 150.00 },
  '30000000-0000-0000-0000-000000000002': { name: 'High-Torque Servo Motor', sku: 'ELEC-002', price: 280.00 },
  '30000000-0000-0000-0000-000000000003': { name: 'IoT Gateway Device', sku: 'ELEC-003', price: 1249.99 },
  '30000000-0000-0000-0000-000000000004': { name: 'Precision Ball Bearing Set', sku: 'MECH-001', price: 95.00 },
  '30000000-0000-0000-0000-000000000005': { name: 'Hydraulic Actuator Cylinder', sku: 'MECH-002', price: 3450.00 },
  '30000000-0000-0000-0000-000000000006': { name: 'Stainless Steel Valve Assembly', sku: 'MECH-003', price: 575.00 },
  '30000000-0000-0000-0000-000000000007': { name: 'Industrial Lubricant (20L)', sku: 'CHEM-001', price: 185.00 },
  '30000000-0000-0000-0000-000000000008': { name: 'Epoxy Adhesive Kit', sku: 'CHEM-002', price: 95.00 },
  '30000000-0000-0000-0000-000000000009': { name: 'Safety Relay Module', sku: 'SAFE-001', price: 120.00 },
  '30000000-0000-0000-0000-000000000010': { name: 'Emergency Stop Assembly', sku: 'SAFE-002', price: 145.00 },
  '00000000-0000-0000-0000-000000000002': { name: 'Industrial IoT Sensor Hub v2', sku: 'ELEC-001', price: 150.00 },
};

/** Formats an order ID into a branded code: e.g. ORD-3E52C323 */
export function formatOrderId(id: string | null | undefined): string {
  if (!id) return 'ORD-PENDING';
  const clean = id.replace(/[^a-zA-Z0-9]/g, '');
  const prefix = clean.startsWith('ord') ? clean.slice(3) : clean;
  return `#ORD-${prefix.slice(0, 8).toUpperCase()}`;
}

/** Formats a workflow ID into a branded code: e.g. WF-63B555BE */
export function formatWorkflowId(id: string | null | undefined): string {
  if (!id) return 'WF-DIRECT';
  const clean = id.replace(/[^a-zA-Z0-9]/g, '');
  const prefix = clean.startsWith('wf') ? clean.slice(2) : clean;
  return `#WF-${prefix.slice(0, 8).toUpperCase()}`;
}

/** Formats an event ID into a branded code: e.g. EVT-EAA2D0 */
export function formatEventId(id: string | null | undefined): string {
  if (!id) return 'EVT-SYSTEM';
  const clean = id.replace(/[^a-zA-Z0-9]/g, '');
  return `#EVT-${clean.slice(0, 8).toUpperCase()}`;
}

/** Formats a simulation ID into a branded code: e.g. SIM-C92D74 */
export function formatSimulationId(id: string | null | undefined): string {
  if (!id) return 'SIM-RUN';
  const clean = id.replace(/[^a-zA-Z0-9]/g, '');
  return `#SIM-${clean.slice(0, 8).toUpperCase()}`;
}

/** Formats a report ID into a branded code: e.g. RPT-B82F63 */
export function formatReportId(id: string | null | undefined): string {
  if (!id) return 'RPT-EXEC';
  const clean = id.replace(/[^a-zA-Z0-9]/g, '');
  const prefix = clean.startsWith('rpt') ? clean.slice(3) : clean;
  return `#RPT-${prefix.slice(0, 8).toUpperCase()}`;
}

/** Formats a carrier tracking ID into a professional shipping code: e.g. TRK-8F2B9A10 */
export function formatTrackingId(id: string | null | undefined): string {
  if (!id) return 'TRK-EXP-01';
  const clean = id.replace(/[^a-zA-Z0-9]/g, '');
  const prefix = clean.startsWith('trk') ? clean.slice(3) : clean;
  return `TRK-${prefix.slice(0, 10).toUpperCase()}`;
}

/** Resolves a customer ID into a friendly enterprise company name */
export function getCustomerName(id: string | null | undefined): string {
  if (!id) return 'Enterprise Client';
  const match = CUSTOMER_DIRECTORY[id];
  if (match) return match.name;
  return `Client (${id.slice(0, 8).toUpperCase()})`;
}

/** Resolves a customer tier */
export function getCustomerTier(id: string | null | undefined): string {
  if (!id) return 'Standard Tier';
  const match = CUSTOMER_DIRECTORY[id];
  return match?.tier || 'Enterprise Tier';
}

/** Resolves product details from product ID */
export function getProductInfo(id: string | null | undefined) {
  if (!id) return { name: 'Industrial Component', sku: 'SKU-001', price: 150.00 };
  return PRODUCT_DIRECTORY[id] || { name: 'Industrial Component', sku: id.slice(0, 8).toUpperCase(), price: 150.00 };
}

/** Formats a numerical currency string: e.g. $1,800.00 */
export function formatCurrency(amount: string | number | null | undefined): string {
  const num = typeof amount === 'number' ? amount : parseFloat(String(amount || 0));
  if (isNaN(num)) return '$0.00';
  return num.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

/** Formats an ISO date into a clean enterprise timestamp */
export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

/** Relative time formatter: e.g. "2 mins ago", "1 hour ago" */
export function formatTimeAgo(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diffSec < 60) return 'Just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return `${Math.floor(diffSec / 86400)}d ago`;
  } catch {
    return isoString;
  }
}
