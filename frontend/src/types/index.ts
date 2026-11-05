// TypeScript interfaces for the AI Supply Chain Digital Twin API

export interface WorkflowItem {
  product_id: string;
  quantity: number;
}

export interface WorkflowRequest {
  customer_id: string;
  items: WorkflowItem[];
}

export interface WorkflowAccepted {
  workflow_id: string;
  correlation_id: string;
  status: string;
  message: string;
}

export interface BlackboardEntry {
  agent_id: string;
  timestamp: string;
  confidence: number;
  rationale: string;
  status: 'proposed' | 'contested' | 'accepted' | 'superseded' | string;
  data: Record<string, unknown>;
  message_type?: string | null;
  topic?: string | null;
}

export interface WorkflowStatus {
  workflow_id: string;
  correlation_id: string | null;
  workflow_status: string;
  current_node: string | null;
  active_agents: string[];
  order: Record<string, unknown> | null;
  shipment: Record<string, unknown> | null;
  executive_decision: Record<string, unknown> | null;
  supplier?: Record<string, unknown> | null;
  replenishment_requests?: Record<string, unknown>[] | null;
  requires_human_approval: boolean;
  event_count: number;
  error_count: number;
  blackboard?: Record<string, BlackboardEntry[]> | null;
  human_overrides?: Record<string, unknown> | null;
}

export interface AgentTrace {
  agent_code: string;
  agent_name: string;
  started_at: string;
  finished_at: string;
  duration_ms: number;
  status: 'completed' | 'failed';
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  decision: Record<string, unknown> | null;
  events_published: Record<string, unknown>[];
}

export interface WorkflowTrace {
  workflow_id: string;
  workflow_status: string;
  agents_executed: number;
  traces: AgentTrace[];
}

export interface WorkflowSummary {
  workflow_id: string;
  correlation_id: string;
  workflow_status: string;
  created_at: string;
  updated_at: string;
  order_id?: string;
  customer_id?: string;
  total_amount?: string;
  order_status?: string;
  requires_human_approval: boolean;
  active_agents: string[];
  event_count: number;
  error_count: number;
}

// Analytics / Dashboard
export interface DashboardKPIs {
  total_orders: number;
  total_revenue: string;
  delivered_orders: number;
  fill_rate_pct: number;
  active_suppliers: number;
  avg_supplier_reliability: number;
  low_stock_alerts: number;
  out_of_stock_alerts: number;
  total_inventory_locations?: number;
  sku_availability_pct?: number;
  total_agents: number;
}

export interface DashboardData {
  kpis: DashboardKPIs;
  orders_by_status: Record<string, number>;
  recent_orders: RecentOrder[];
  inventory_health: {
    total_locations: number;
    low_stock: number;
    out_of_stock: number;
    healthy: number;
  };
  recent_reports: RecentReport[];
}

export interface RecentOrder {
  order_id: string;
  customer_id?: string;
  customer_name?: string;
  workflow_id?: string | null;
  status: string;
  priority: string;
  total_amount: string;
  created_at: string | null;
}

export interface RecentReport {
  report_id: string;
  title: string;
  status: string;
  created_at: string | null;
}

// Orders
export interface Order {
  order_id: string;
  customer_id: string;
  customer: {
    name: string | null;
    tier: string | null;
    email: string | null;
  };
  status: string;
  priority: string;
  total_amount: string;
  currency: string;
  workflow_id: string | null;
  created_at: string | null;
  items: OrderItem[];
}

export interface OrderItem {
  order_item_id: string;
  product_id: string;
  quantity: number;
  unit_price: string;
  line_total: string;
}

// Inventory
export interface InventoryRecord {
  inventory_id: string;
  product_id: string;
  product_name: string;
  sku: string;
  warehouse_id: string;
  warehouse_name: string;
  warehouse_city: string;
  available_qty: number;
  reserved_qty: number;
  net_available: number;
  safety_stock: number;
  reorder_point: number | null;
  status: 'ok' | 'low' | 'critical';
}

export interface InventorySummary {
  total_sku_locations: number;
  total_available_units: number;
  total_reserved_units: number;
  net_available_units: number;
  low_stock_locations: number;
  out_of_stock_locations: number;
  fill_rate_pct: number;
}

export interface PurchaseOrder {
  po_id: string;
  supplier_id: string;
  supplier_name: string;
  product_id: string;
  product_name: string;
  sku: string;
  warehouse_id: string;
  warehouse_name: string;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  lead_time_days: number;
  status: 'draft' | 'in_transit' | 'received';
  workflow_id: string | null;
  created_at: string;
}

// Suppliers
export interface Supplier {
  supplier_id: string;
  name: string;
  country: string;
  lead_time_days: number;
  reliability_score: number;
  rating: number | null;
  status: string;
  risk_tier: 'low' | 'medium' | 'high';
}

export interface SupplierStats {
  total_active: number;
  avg_reliability_score: number;
  min_reliability_score: number;
  max_reliability_score: number;
  risk_tier_distribution: Record<string, number>;
}

// Reports
export interface Report {
  report_id: string;
  report_type: string;
  title: string;
  status: string;
  workflow_id: string | null;
  generated_by_agent: string | null;
  created_at: string | null;
  payload_summary: Record<string, unknown> | null;
}

// Agents
export interface AgentDefinition {
  code: string;
  name: string;
  layer: 'operational' | 'business' | 'coordination';
  description: string;
}

// Simulation
export interface SimulationScenario {
  scenario_type: string;
  customer_id: string;
  items: WorkflowItem[];
  description?: string;
}

export interface SimulationAccepted {
  simulation_id: string;
  scenario_type: string;
  status: string;
  message: string;
}

export interface SimulationResult {
  simulation_id: string;
  scenario_type: string;
  status: string;
  description: string;
  agents_executed: number;
  trace: AgentTrace[];
  summary?: {
    workflow_status: string;
    order_status: string;
    total_amount: string;
    risk_score: number;
    risk_level: string;
    ceo_approved: boolean;
    approval_tier: string;
    carrier: string;
    eta: string;
    error_count: number;
    decision_count: number;
    event_count: number;
  };
  error?: string;
}

// Events
export interface EventRecord {
  event_id: string;
  event_type: string;
  source_agent: string;
  payload: Record<string, unknown>;
  workflow_id: string | null;
  timestamp: string;
  status: string;
  subscribers?: string[];
  remediation_summary?: string;
  remediation_status?: string;
  autonomous_actions?: Array<{
    agent: string;
    action: string;
    details: string;
    timestamp: string;
  }>;
}

// Auth
export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  role: string;
  username: string;
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}
