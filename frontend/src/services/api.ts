import axios, { type AxiosError } from 'axios';
import type {
  WorkflowRequest,
  WorkflowAccepted,
  WorkflowStatus,
  WorkflowTrace,
  WorkflowSummary,
  DashboardData,
  PaginatedResponse,
  Order,
  InventoryRecord,
  InventorySummary,
  PurchaseOrder,
  Supplier,
  SupplierStats,
  Report,
  AgentDefinition,
  SimulationScenario,
  SimulationAccepted,
  SimulationResult,
  EventRecord,
  Shipment,
  ShipmentStats,
  ProcurementPO,
  ProcurementStats,
  SupplierScorecard,
  CreateOrderPayload,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_URL = `${BASE_URL}/api/v1`;

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach bearer token if stored
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Unified error handler
function handleError(err: unknown): never {
  const axiosErr = err as AxiosError<{ detail?: string }>;
  const message = axiosErr.response?.data?.detail ?? axiosErr.message ?? 'Unknown error';
  throw new Error(message);
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  login: async (username: string, password: string) => {
    try {
      const form = new URLSearchParams();
      form.set('username', username);
      form.set('password', password);
      const { data } = await apiClient.post('/auth/token', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      localStorage.setItem('access_token', data.access_token);
      return data;
    } catch (err) { handleError(err); }
  },
  logout: () => localStorage.removeItem('access_token'),
};

// ── Workflows ─────────────────────────────────────────────────────────────────

export const workflowApi = {
  list: async (limit = 50): Promise<{ items: WorkflowSummary[]; total: number }> => {
    try {
      const { data } = await apiClient.get<{ items: WorkflowSummary[]; total: number }>('/workflows', { params: { limit } });
      return data;
    } catch (err) { return handleError(err); }
  },

  start: async (req: WorkflowRequest): Promise<WorkflowAccepted> => {
    try {
      const { data } = await apiClient.post<WorkflowAccepted>('/workflows/orders', req);
      return data;
    } catch (err) { return handleError(err); }
  },

  getStatus: async (id: string): Promise<WorkflowStatus> => {
    try {
      const { data } = await apiClient.get<WorkflowStatus>(`/workflows/${id}`);
      return data;
    } catch (err) { return handleError(err); }
  },

  getTrace: async (id: string): Promise<WorkflowTrace> => {
    try {
      const { data } = await apiClient.get<WorkflowTrace>(`/workflows/${id}/trace`);
      return data;
    } catch (err) { return handleError(err); }
  },

  overrideDecision: async (id: string, req: { topic: string; action: 'pin' | 'revert'; value: unknown }): Promise<{ status: string; message: string }> => {
    try {
      const { data } = await apiClient.post<{ status: string; message: string }>(`/workflows/${id}/override`, req);
      return data;
    } catch (err) { return handleError(err); }
  },

  approve: async (id: string, notes?: string): Promise<{ workflow_id: string; status: string; message: string }> => {
    try {
      const { data } = await apiClient.post<{ workflow_id: string; status: string; message: string }>(`/workflows/${id}/approve`, { notes });
      return data;
    } catch (err) { return handleError(err); }
  },

  reject: async (id: string, notes?: string): Promise<{ workflow_id: string; status: string; message: string }> => {
    try {
      const { data } = await apiClient.post<{ workflow_id: string; status: string; message: string }>(`/workflows/${id}/reject`, { notes });
      return data;
    } catch (err) { return handleError(err); }
  },
};

// ── Analytics / Dashboard ─────────────────────────────────────────────────────

export const analyticsApi = {
  getDashboard: async (): Promise<DashboardData> => {
    try {
      const { data } = await apiClient.get<DashboardData>('/analytics/dashboard');
      return data;
    } catch (err) { return handleError(err); }
  },

  getSummary: async () => {
    try {
      const { data } = await apiClient.get('/analytics/summary');
      return data;
    } catch (err) { return handleError(err); }
  },

  getAgents: async (): Promise<{ agents: AgentDefinition[]; total: number; layers: Record<string, number> }> => {
    try {
      const { data } = await apiClient.get('/analytics/agents');
      return data;
    } catch (err) { return handleError(err); }
  },

  getNetworkTopology: async (): Promise<import('../types').TwinNetworkData> => {
    try {
      const { data } = await apiClient.get<import('../types').TwinNetworkData>('/analytics/network');
      return data;
    } catch (err) { return handleError(err); }
  },
};

// ── Orders (OMS) ──────────────────────────────────────────────────────────────

export const ordersApi = {
  list: async (params?: { skip?: number; limit?: number; status?: string; priority?: string }) => {
    try {
      const { data } = await apiClient.get<PaginatedResponse<Order>>('/orders', { params });
      return data;
    } catch (err) { return handleError(err); }
  },

  getStats: async () => {
    try {
      const { data } = await apiClient.get('/orders/stats');
      return data;
    } catch (err) { return handleError(err); }
  },

  getById: async (id: string): Promise<Order> => {
    try {
      const { data } = await apiClient.get<Order>(`/orders/${id}`);
      return data;
    } catch (err) { return handleError(err); }
  },

  create: async (payload: CreateOrderPayload) => {
    try {
      const { data } = await apiClient.post('/orders', payload);
      return data;
    } catch (err) { return handleError(err); }
  },

  updateStatus: async (orderId: string, status: string) => {
    try {
      const { data } = await apiClient.patch(`/orders/${orderId}/status`, { status });
      return data;
    } catch (err) { return handleError(err); }
  },
};

// ── Transportation & Logistics (TMS) ─────────────────────────────────────────

export const shipmentsApi = {
  list: async (params?: { skip?: number; limit?: number; status?: string; freight_mode?: string }) => {
    try {
      const { data } = await apiClient.get<PaginatedResponse<Shipment>>('/shipments', { params });
      return data;
    } catch (err) { return handleError(err); }
  },

  getStats: async (): Promise<ShipmentStats> => {
    try {
      const { data } = await apiClient.get<ShipmentStats>('/shipments/stats');
      return data;
    } catch (err) { return handleError(err); }
  },

  getById: async (id: string): Promise<Shipment> => {
    try {
      const { data } = await apiClient.get<Shipment>(`/shipments/${id}`);
      return data;
    } catch (err) { return handleError(err); }
  },

  create: async (payload: {
    order_id?: string;
    warehouse_id?: string;
    carrier: string;
    freight_mode: 'road' | 'air' | 'ocean' | 'rail';
    origin: string;
    destination: string;
    eta?: string;
  }) => {
    try {
      const { data } = await apiClient.post('/shipments', payload);
      return data;
    } catch (err) { return handleError(err); }
  },

  updateStatus: async (id: string, payload: {
    status: 'pending' | 'assigned' | 'dispatched' | 'in_transit' | 'delivered' | 'delayed' | 'failed';
    current_location?: string;
    delay_reason?: string;
  }) => {
    try {
      const { data } = await apiClient.post(`/shipments/${id}/status`, payload);
      return data;
    } catch (err) { return handleError(err); }
  },

  reroute: async (id: string, payload: {
    new_freight_mode: 'road' | 'air' | 'ocean' | 'rail';
    new_carrier?: string;
    reason?: string;
  }) => {
    try {
      const { data } = await apiClient.post(`/shipments/${id}/reroute`, payload);
      return data;
    } catch (err) { return handleError(err); }
  },
};

// ── Supplier Relationship Management & Procurement (SRM) ──────────────────────

export const procurementApi = {
  listOrders: async (params?: { status?: string; limit?: number }) => {
    try {
      const { data } = await apiClient.get<{ items: ProcurementPO[]; total: number; limit: number }>('/procurement/orders', { params });
      return data;
    } catch (err) { return handleError(err); }
  },

  getStats: async (): Promise<ProcurementStats> => {
    try {
      const { data } = await apiClient.get<ProcurementStats>('/procurement/stats');
      return data;
    } catch (err) { return handleError(err); }
  },

  createOrder: async (payload: {
    supplier_id: string;
    product_id: string;
    warehouse_id: string;
    quantity: number;
    unit_cost: number;
    lead_time_days?: number;
  }) => {
    try {
      const { data } = await apiClient.post('/procurement/orders', payload);
      return data;
    } catch (err) { return handleError(err); }
  },

  receiveOrder: async (poId: string) => {
    try {
      const { data } = await apiClient.post(`/procurement/orders/${poId}/receive`);
      return data;
    } catch (err) { return handleError(err); }
  },

  getSuppliers: async () => {
    try {
      const { data } = await apiClient.get<{ items: SupplierScorecard[]; total: number }>('/procurement/suppliers');
      return data;
    } catch (err) { return handleError(err); }
  },
};

// ── Inventory ─────────────────────────────────────────────────────────────────

export const inventoryApi = {
  list: async (params?: { skip?: number; limit?: number; low_stock_only?: boolean }) => {
    try {
      const { data } = await apiClient.get<PaginatedResponse<InventoryRecord> & { low_stock_count: number }>('/inventory', { params });
      return data;
    } catch (err) { return handleError(err); }
  },

  getSummary: async (): Promise<InventorySummary> => {
    try {
      const { data } = await apiClient.get<InventorySummary>('/inventory/summary');
      return data;
    } catch (err) { return handleError(err); }
  },

  getByProduct: async (productId: string) => {
    try {
      const { data } = await apiClient.get(`/inventory/${productId}`);
      return data;
    } catch (err) { return handleError(err); }
  },

  getReplenishmentOrders: async (params?: { limit?: number; status?: string }): Promise<{ items: PurchaseOrder[]; total: number }> => {
    try {
      const { data } = await apiClient.get<{ items: PurchaseOrder[]; total: number }>('/inventory/replenishment-orders', { params });
      return data;
    } catch (err) { return handleError(err); }
  },

  receiveReplenishmentOrder: async (poId: string): Promise<{ success: boolean; message: string }> => {
    try {
      const { data } = await apiClient.post<{ success: boolean; message: string }>(`/inventory/replenishment-orders/${poId}/receive`);
      return data;
    } catch (err) { return handleError(err); }
  },

  runAutonomousScan: async (): Promise<{
    status: string;
    scanned_sku_locations: number;
    deficits_detected: number;
    autonomous_remediations_executed: number;
    message: string;
    remediation_actions: Array<{ agent: string; action: string; details: string; timestamp: string }>;
  }> => {
    try {
      const { data } = await apiClient.post('/inventory/autonomous-scan');
      return data;
    } catch (err) { return handleError(err); }
  },

  autoHealAll: async (): Promise<{
    status: string;
    orders_received_count: number;
    message: string;
  }> => {
    try {
      const { data } = await apiClient.post('/inventory/replenish/auto-heal');
      return data;
    } catch (err) { return handleError(err); }
  },
};

// ── Suppliers ─────────────────────────────────────────────────────────────────

export const suppliersApi = {
  list: async (params?: { skip?: number; limit?: number; active_only?: boolean }) => {
    try {
      const { data } = await apiClient.get<PaginatedResponse<Supplier>>('/suppliers', { params });
      return data;
    } catch (err) { return handleError(err); }
  },

  getStats: async (): Promise<SupplierStats> => {
    try {
      const { data } = await apiClient.get<SupplierStats>('/suppliers/stats');
      return data;
    } catch (err) { return handleError(err); }
  },

  getById: async (id: string) => {
    try {
      const { data } = await apiClient.get(`/suppliers/${id}`);
      return data;
    } catch (err) { return handleError(err); }
  },
};

// ── Reports ───────────────────────────────────────────────────────────────────

export const reportsApi = {
  list: async (params?: { skip?: number; limit?: number; status?: string }) => {
    try {
      const { data } = await apiClient.get<PaginatedResponse<Report>>('/reports', { params });
      return data;
    } catch (err) { return handleError(err); }
  },

  getById: async (id: string): Promise<Report> => {
    try {
      const { data } = await apiClient.get<Report>(`/reports/${id}`);
      return data;
    } catch (err) { return handleError(err); }
  },
};

// ── Simulate ──────────────────────────────────────────────────────────────────

export const simulateApi = {
  run: async (scenario: SimulationScenario): Promise<SimulationAccepted> => {
    try {
      const { data } = await apiClient.post<SimulationAccepted>('/simulate', scenario);
      return data;
    } catch (err) { return handleError(err); }
  },

  list: async (limit = 20) => {
    try {
      const { data } = await apiClient.get('/simulate', { params: { limit } });
      return data;
    } catch (err) { return handleError(err); }
  },

  getResult: async (id: string): Promise<SimulationResult> => {
    try {
      const { data } = await apiClient.get<SimulationResult>(`/simulate/${id}`);
      return data;
    } catch (err) { return handleError(err); }
  },

  getScenarios: async () => {
    try {
      const { data } = await apiClient.get('/simulate/scenarios');
      return data;
    } catch (err) { return handleError(err); }
  },
};

// ── Events ────────────────────────────────────────────────────────────────────

export const eventsApi = {
  list: async (params?: { limit?: number; event_type?: string }) => {
    try {
      const { data } = await apiClient.get<{ items: EventRecord[]; total: number; limit: number }>('/events', { params });
      return data;
    } catch (err) { return handleError(err); }
  },

  inject: async (payload: { event_type: string; source_agent?: string; payload?: Record<string, unknown>; workflow_id?: string }) => {
    try {
      const { data } = await apiClient.post('/events', payload);
      return data;
    } catch (err) { return handleError(err); }
  },

  getTypes: async () => {
    try {
      const { data } = await apiClient.get('/events/types');
      return data;
    } catch (err) { return handleError(err); }
  },
};

// ── Health ────────────────────────────────────────────────────────────────────

export const healthApi = {
  check: async () => {
    try {
      const { data } = await axios.get(`${BASE_URL}/health`, { timeout: 5000 });
      return data;
    } catch {
      return { status: 'offline', dependencies: { db: 'error', redis: 'error', rabbitmq: 'error' } };
    }
  },
};
