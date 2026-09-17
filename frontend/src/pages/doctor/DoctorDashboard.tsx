import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { 
  Stethoscope, 
  Calendar, 
  Clock, 
  FileText, 
  UserCheck, 
  CheckCircle2, 
  RefreshCw,
  Eye,
  AlertCircle
} from 'lucide-react';

export const DoctorDashboard: React.FC = () => {
  const { user } = useAuth();
  const [responses, setResponses] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedResponse, setSelectedResponse] = useState<any | null>(null);

  const fetchDoctorData = async () => {
    setLoading(true);
    try {
      // Fetch Dr. Rao's doctor info or use current user
      const doctors = await api.getDoctors({ specialty: 'Orthopedics' });
      const drRao = doctors.find((d) => d.name.includes('Rao')) || doctors[0];
      if (drRao) {
        const data = await api.getDoctorQuestionnaireResponses(drRao.id);
        setResponses(data.responses);
      }
    } catch (err) {
      console.error('Failed to load doctor responses:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoctorData();
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6">
      {/* Doctor Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center shadow-md">
            <Stethoscope className="h-7 w-7" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-slate-900">Dr. Rao, MS, MCh</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                Active Clinician
              </span>
            </div>
            <p className="text-sm text-slate-600">
              Orthopedics & Joint Surgery • CityCare Hospital
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={fetchDoctorData}
            title="Refresh"
            className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-600 hover:text-slate-900 transition-colors shadow-2xs"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <div className="px-4 py-2 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs font-semibold flex items-center space-x-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Consultation Calendar: Online</span>
          </div>
        </div>
      </div>

      {/* Grid: Upcoming Patient Intakes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Intakes List */}
        <div className="lg:col-span-1 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-1.5">
              <FileText className="h-4 w-4 text-blue-600" />
              <span>Pre-Visit Patient Intakes ({responses.length})</span>
            </h2>
          </div>

          {loading ? (
            <div className="p-8 text-center text-slate-500 text-sm">
              <div className="h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              <span>Loading intakes...</span>
            </div>
          ) : responses.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 text-center text-slate-500 text-sm">
              No completed pre-visit questionnaires yet. When patients confirm an appointment and submit the questionnaire, their clinical intake appears here.
            </div>
          ) : (
            <div className="space-y-2">
              {responses.map((resp) => (
                <div
                  key={resp.appointment_id}
                  onClick={() => setSelectedResponse(resp)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    selectedResponse?.appointment_id === resp.appointment_id
                      ? 'bg-blue-50/70 border-blue-500 shadow-xs'
                      : 'bg-white border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <h3 className="font-semibold text-sm text-slate-900">{resp.patient_name}</h3>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      COMPLETED
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 flex items-center space-x-1 mt-1">
                    <Clock className="h-3 w-3" />
                    <span>{resp.appointment_time}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Detailed Intake View */}
        <div className="lg:col-span-2">
          {selectedResponse ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
              <div className="border-b border-slate-100 pb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Intake: {selectedResponse.patient_name}
                  </h2>
                  <div className="text-xs text-slate-500 mt-0.5">
                    Appointment: {selectedResponse.appointment_time}
                  </div>
                </div>
                <div className="text-right text-xs text-slate-400">
                  Submitted: {new Date(selectedResponse.completed_at).toLocaleString()}
                </div>
              </div>

              {/* Answers Display */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Patient Responses
                </h3>
                <div className="space-y-3">
                  {Object.entries(selectedResponse.answers).map(([key, val]: [string, any], idx) => (
                    <div key={key} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/70">
                      <div className="text-xs font-semibold text-slate-600 mb-1">
                        Question {idx + 1}
                      </div>
                      <div className="text-sm font-bold text-slate-900">
                        {String(val)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-12 text-center text-slate-400 text-sm flex flex-col items-center justify-center h-full min-h-[300px]">
              <Eye className="h-10 w-10 text-slate-300 mb-2" />
              <p className="font-medium text-slate-600">Select a patient intake from the left</p>
              <p className="text-xs text-slate-400 mt-1 max-w-sm">
                Review verified chief complaints, pain severity scales, and prior imaging before consultation.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
