export type Role = 'PATIENT' | 'DOCTOR' | 'HOSPITAL_ADMIN' | 'PLATFORM_ADMIN';

export interface User {
  id: string;
  email: string;
  role: Role;
  first_name: string;
  last_name: string;
  phone?: string;
  is_active: boolean;
  hospital_id?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Hospital {
  id: string;
  name: string;
  status: string;
  city: string;
  address?: string;
  phone?: string;
  email?: string;
}

export interface Doctor {
  id: string;
  name: string;
  specialty?: string;
  hospital_id: string;
  hospital_name?: string;
  qualification?: string;
  experience_years?: number;
  consultation_fee?: number;
  languages?: string;
  status: string;
}

export interface AvailabilitySlot {
  slot_id: string;
  doctor_id: string;
  doctor_name: string;
  hospital_id: string;
  hospital_name: string;
  specialty: string;
  start_time: string;
  end_time: string;
  formatted_time: string;
  is_booked?: boolean;
}

export interface Appointment {
  id: string;
  hospital_id: string;
  patient_id: string;
  doctor_id: string;
  slot_id: string;
  status: 'PENDING' | 'CONFIRMED' | 'RESCHEDULED' | 'CANCELLED' | 'SYNCHRONIZATION_PENDING' | 'RECONCILIATION_REQUIRED' | 'FAILED';
  appointment_type: string;
  reason_for_visit?: string;
  external_appointment_id?: string;
  correlation_id: string;
  idempotency_key?: string;
  created_at: string;
  doctor_name?: string;
  hospital_name?: string;
  slot_time?: string;
}

export interface Question {
  id: string;
  order_index: number;
  prompt: string;
  question_type: 'YES_NO' | 'CHOICE' | 'MULTIPLE_CHOICE' | 'NUMERIC' | 'SHORT_TEXT';
  options?: string[];
  is_required: boolean;
}

export interface Questionnaire {
  id: string;
  hospital_id: string;
  title: string;
  description?: string;
  questions: Question[];
}

export interface QuestionnaireResponse {
  id: string;
  status: string;
  answers: Record<string, any>;
  completed_at?: string;
}

export interface AIChatResponse {
  conversation_id: string;
  message: string;
  intent: string;
  is_safe: boolean;
  requires_clarification: boolean;
  slots: AvailabilitySlot[];
  appointment?: Appointment;
  tool_calls: Array<{ name: string; result: any }>;
  context: Record<string, any>;
}

export interface IntegrationOperation {
  id: string;
  correlation_id: string;
  operation_type: string;
  status: string;
  external_system: string;
  latency_ms: number;
  created_at: string;
}

export interface ReconciliationRecord {
  id: string;
  appointment_id: string;
  hospital_id: string;
  correlation_id: string;
  reason: string;
  status: 'OPEN' | 'INVESTIGATING' | 'RESOLVED';
  created_at: string;
}
