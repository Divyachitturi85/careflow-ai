import { 
  AuthResponse, 
  User, 
  Hospital, 
  Doctor, 
  AvailabilitySlot, 
  Appointment, 
  AIChatResponse, 
  Questionnaire, 
  QuestionnaireResponse,
  IntegrationOperation,
  ReconciliationRecord
} from '../types';

const API_BASE = '/api';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    if (!window.location.pathname.includes('/login')) {
      window.location.href = '/login';
    }
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    let errorDetail = 'Request failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // Auth
  login: (email: string, password: string): Promise<AuthResponse> =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  getMe: (): Promise<User> => request<User>('/auth/me'),

  // Scheduling & Discovery
  getHospitals: (city?: string): Promise<Hospital[]> => {
    const q = city ? `?city=${encodeURIComponent(city)}` : '';
    return request<Hospital[]>(`/hospitals${q}`);
  },

  getDoctors: (params: { specialty?: string; city?: string; hospital_id?: string } = {}): Promise<Doctor[]> => {
    const search = new URLSearchParams();
    if (params.specialty) search.set('specialty', params.specialty);
    if (params.city) search.set('city', params.city);
    if (params.hospital_id) search.set('hospital_id', params.hospital_id);
    const q = search.toString() ? `?${search.toString()}` : '';
    return request<Doctor[]>(`/doctors${q}`);
  },

  getAvailability: (params: { doctor_id?: string; hospital_id?: string; specialty?: string; city?: string } = {}): Promise<AvailabilitySlot[]> => {
    const search = new URLSearchParams();
    if (params.doctor_id) search.set('doctor_id', params.doctor_id);
    if (params.hospital_id) search.set('hospital_id', params.hospital_id);
    if (params.specialty) search.set('specialty', params.specialty);
    if (params.city) search.set('city', params.city);
    const q = search.toString() ? `?${search.toString()}` : '';
    return request<AvailabilitySlot[]>(`/availability${q}`);
  },

  // Appointments
  bookAppointment: (data: {
    slot_id: string;
    patient_id?: string;
    appointment_type?: string;
    reason_for_visit?: string;
    idempotency_key?: string;
    correlation_id?: string;
  }): Promise<Appointment> =>
    request<Appointment>('/appointments', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getAppointments: (): Promise<Appointment[]> => request<Appointment[]>('/appointments'),

  getAppointmentById: (id: string): Promise<Appointment> => request<Appointment>(`/appointments/${id}`),

  cancelAppointment: (id: string, reason?: string): Promise<Appointment> =>
    request<Appointment>(`/appointments/${id}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ cancellation_reason: reason }),
    }),

  rescheduleAppointment: (id: string, new_slot_id: string): Promise<Appointment> =>
    request<Appointment>(`/appointments/${id}/reschedule`, {
      method: 'POST',
      body: JSON.stringify({ new_slot_id }),
    }),

  // AI Voice & Text Agent
  chatWithAI: (message: string, conversation_id?: string): Promise<AIChatResponse> =>
    request<AIChatResponse>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message, conversation_id }),
    }),

  // Pre-Visit Questionnaires
  getQuestionnaireForAppointment: (appointmentId: string): Promise<{
    questionnaire: Questionnaire;
    response: QuestionnaireResponse | null;
  }> => request(`/questionnaires/appointment/${appointmentId}`),

  submitQuestionnaireResponse: (appointmentId: string, answers: Record<string, any>): Promise<{
    status: string;
    message: string;
    completed_at: string;
  }> =>
    request('/questionnaires/responses', {
      method: 'POST',
      body: JSON.stringify({ appointment_id: appointmentId, answers }),
    }),

  getDoctorQuestionnaireResponses: (doctorId: string): Promise<{
    count: number;
    responses: Array<{
      appointment_id: string;
      patient_name: string;
      appointment_time: string;
      status: string;
      completed_at: string;
      answers: Record<string, any>;
    }>;
  }> => request(`/questionnaires/doctor/${doctorId}/responses`),

  // Admin & Monitoring
  setSimulationMode: (mode: 'NORMAL' | 'TIMEOUT' | 'FAILURE' | 'UNKNOWN_OUTCOME'): Promise<{
    mode: string;
    message: string;
  }> =>
    request('/admin/simulation-mode', {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),

  getSimulationMode: (): Promise<{ mode: string }> => request('/admin/simulation-mode'),

  getOperations: (limit: number = 20): Promise<IntegrationOperation[]> =>
    request<IntegrationOperation[]>(`/admin/operations`),

  getReconciliations: (): Promise<ReconciliationRecord[]> =>
    request<ReconciliationRecord[]>('/admin/reconciliations'),
};
