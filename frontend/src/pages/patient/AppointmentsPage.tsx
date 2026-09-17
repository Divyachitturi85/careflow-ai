import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../../api/client';
import { 
  Calendar, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  FileText, 
  Bot, 
  Trash2, 
  RefreshCw,
  Hospital as HospIcon,
  ShieldCheck
} from 'lucide-react';
import { Appointment } from '../../types';

export const AppointmentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const data = await api.getAppointments();
      setAppointments(data);
    } catch (err) {
      console.error('Failed to load appointments:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, []);

  const handleCancel = async (id: string) => {
    if (!confirm('Are you sure you want to cancel this appointment?')) return;
    setCancellingId(id);
    try {
      await api.cancelAppointment(id, 'Patient requested cancellation via web portal');
      await fetchAppointments();
    } catch (err: any) {
      alert(`Cancellation failed: ${err.message}`);
    } finally {
      setCancellingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'CONFIRMED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="h-3 w-3" />
            <span>CONFIRMED</span>
          </span>
        );
      case 'CANCELLED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            <XCircle className="h-3 w-3" />
            <span>CANCELLED</span>
          </span>
        );
      case 'RECONCILIATION_REQUIRED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="h-3 w-3" />
            <span>RECONCILIATION REQUIRED</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            <Clock className="h-3 w-3" />
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My Appointments</h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Real-time database records verified with external Mock EHR
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={fetchAppointments}
            title="Refresh list"
            className="p-2 bg-white border border-slate-200 rounded-xl text-slate-600 hover:text-slate-900 shadow-2xs hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <Link
            to="/"
            className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-semibold shadow-sm transition-colors flex items-center space-x-1.5"
          >
            <Bot className="h-4 w-4" />
            <span>Schedule via Voice AI</span>
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="py-12 text-center text-slate-500 text-sm flex flex-col items-center">
          <div className="h-7 w-7 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mb-3" />
          <span>Loading scheduled appointments...</span>
        </div>
      ) : appointments.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center shadow-xs">
          <Calendar className="h-10 w-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">No appointments scheduled</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
            Use our autonomous voice assistant to discover available doctors and schedule an appointment in seconds.
          </p>
          <Link
            to="/"
            className="mt-4 inline-flex items-center space-x-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-semibold shadow-sm transition-colors"
          >
            <Bot className="h-4 w-4" />
            <span>Talk with Voice Assistant</span>
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {appointments.map((appt) => (
            <div
              key={appt.id}
              className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs hover:border-slate-300 transition-all flex flex-col md:flex-row justify-between md:items-center gap-4"
            >
              <div className="space-y-2">
                <div className="flex items-center space-x-3">
                  {getStatusBadge(appt.status)}
                  {appt.external_appointment_id && (
                    <span className="inline-flex items-center space-x-1 text-xs text-slate-600 font-mono bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                      <ShieldCheck className="h-3 w-3 text-emerald-600" />
                      <span>EHR ID: {appt.external_appointment_id}</span>
                    </span>
                  )}
                </div>

                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    {appt.doctor_name || 'Dr. Rao'}
                  </h3>
                  <div className="text-xs text-slate-600 flex items-center space-x-3 mt-1">
                    <span className="flex items-center space-x-1">
                      <HospIcon className="h-3.5 w-3.5 text-slate-400" />
                      <span>{appt.hospital_name || 'CityCare Hospital'}</span>
                    </span>
                    <span className="flex items-center space-x-1 font-medium text-slate-800">
                      <Clock className="h-3.5 w-3.5 text-teal-600" />
                      <span>{appt.slot_time || 'Consultation Slot'}</span>
                    </span>
                  </div>
                </div>

                <div className="text-xs text-slate-500 font-mono">
                  <span>Correlation ID: {appt.correlation_id}</span>
                  {appt.reason_for_visit && (
                    <div className="text-slate-700 mt-1 font-sans">
                      <span className="font-medium">Reason:</span> {appt.reason_for_visit}
                    </div>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-2 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100">
                {appt.status === 'CONFIRMED' && (
                  <button
                    onClick={() => navigate(`/questionnaire?appointment_id=${appt.id}`)}
                    className="px-3.5 py-2 bg-teal-50 hover:bg-teal-100 text-teal-700 border border-teal-200 rounded-xl text-xs font-semibold transition-colors flex items-center space-x-1.5 shadow-2xs"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    <span>Intake Questionnaire</span>
                  </button>
                )}

                {appt.status !== 'CANCELLED' && (
                  <button
                    onClick={() => handleCancel(appt.id)}
                    disabled={cancellingId === appt.id}
                    className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-colors"
                    title="Cancel Appointment"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
