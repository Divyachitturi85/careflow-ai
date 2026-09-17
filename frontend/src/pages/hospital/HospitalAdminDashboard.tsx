import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { 
  Hospital as HospIcon, 
  Users, 
  Calendar, 
  Clock, 
  ShieldCheck, 
  CheckCircle2, 
  Activity,
  RefreshCw
} from 'lucide-react';
import { Doctor, AvailabilitySlot } from '../../types';

export const HospitalAdminDashboard: React.FC = () => {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [docsData, slotsData] = await Promise.all([
        api.getDoctors(),
        api.getAvailability(),
      ]);
      setDoctors(docsData);
      setSlots(slotsData);
    } catch (err) {
      console.error('Failed to load hospital data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center space-x-4">
          <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-600 text-white flex items-center justify-center shadow-md">
            <HospIcon className="h-7 w-7" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-slate-900">CityCare Hospital</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                APPROVED TENANT
              </span>
            </div>
            <p className="text-sm text-slate-600">
              Facility ID: <code className="font-mono text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded">EXT-FAC-CITYCARE</code> • Vijayawada, AP
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={fetchData}
            title="Refresh"
            className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-600 hover:text-slate-900 transition-colors shadow-2xs"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <div className="px-3.5 py-1.5 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs font-semibold flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>EHR Connector: ACTIVE</span>
          </div>
        </div>
      </div>

      {/* Grid: Doctors & Availability Slots */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Doctors Roster */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Users className="h-5 w-5 text-purple-600" />
              <span>Medical Staff & Physicians ({doctors.length})</span>
            </h2>
          </div>

          <div className="space-y-3">
            {doctors.map((doc) => (
              <div key={doc.id} className="p-3.5 rounded-xl border border-slate-200 flex justify-between items-center hover:border-slate-300 transition-colors">
                <div>
                  <h3 className="font-bold text-sm text-slate-900">{doc.name}</h3>
                  <div className="text-xs text-purple-700 font-medium">{doc.specialty}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">{doc.qualification} • {doc.experience_years} yrs exp</div>
                </div>
                <div className="text-right">
                  <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {doc.status}
                  </span>
                  <div className="text-xs font-semibold text-slate-900 mt-1">${doc.consultation_fee} fee</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Real Availability Slots */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Calendar className="h-5 w-5 text-teal-600" />
              <span>Open Bookable Slots ({slots.length})</span>
            </h2>
          </div>

          {slots.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">
              All seeded slots have been reserved or booked.
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[400px] overflow-y-auto pr-1">
              {slots.map((s) => (
                <div key={s.slot_id} className="p-3 rounded-xl border border-slate-200 flex justify-between items-center bg-slate-50/50">
                  <div>
                    <div className="font-semibold text-xs text-slate-900">{s.doctor_name} ({s.specialty})</div>
                    <div className="text-xs text-teal-700 font-medium flex items-center space-x-1 mt-0.5">
                      <Clock className="h-3 w-3" />
                      <span>{s.formatted_time}</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                    OPEN
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
