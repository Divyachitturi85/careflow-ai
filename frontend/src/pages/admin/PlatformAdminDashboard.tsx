import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { 
  Sliders, 
  Activity, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw, 
  ShieldAlert,
  Server,
  Zap
} from 'lucide-react';
import { IntegrationOperation, ReconciliationRecord } from '../../types';

export const PlatformAdminDashboard: React.FC = () => {
  const [currentMode, setCurrentMode] = useState<string>('NORMAL');
  const [operations, setOperations] = useState<IntegrationOperation[]>([]);
  const [reconciliations, setReconciliations] = useState<ReconciliationRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [switching, setSwitching] = useState<boolean>(false);
  const [statusNote, setStatusNote] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [modeRes, opsRes, recRes] = await Promise.all([
        api.getSimulationMode(),
        api.getOperations(25),
        api.getReconciliations(),
      ]);
      setCurrentMode(modeRes.mode);
      setOperations(opsRes.operations);
      setReconciliations(recRes.records);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleModeChange = async (mode: 'NORMAL' | 'TIMEOUT' | 'FAILURE' | 'UNKNOWN_OUTCOME') => {
    setSwitching(true);
    setStatusNote(null);
    try {
      const res = await api.setSimulationMode(mode);
      setCurrentMode(res.mode);
      setStatusNote(`Mock EHR simulation mode updated to: ${res.mode}`);
      await loadData();
    } catch (err: any) {
      alert(`Failed to set mode: ${err.message}`);
    } finally {
      setSwitching(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center space-x-4">
          <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-rose-600 to-orange-600 text-white flex items-center justify-center shadow-md">
            <Sliders className="h-7 w-7" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-slate-900">Platform Operations & EHR Simulation</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
                PLATFORM ADMIN
              </span>
            </div>
            <p className="text-sm text-slate-600">
              Mock healthcare connector fault-injection, observability, and reconciliation controls
            </p>
          </div>
        </div>

        <button
          onClick={loadData}
          title="Refresh"
          className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-600 hover:text-slate-900 transition-colors shadow-2xs"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {statusNote && (
        <div className="mb-6 p-4 rounded-xl bg-teal-50 border border-teal-200 text-teal-900 text-sm flex items-center space-x-2">
          <CheckCircle2 className="h-5 w-5 text-teal-600" />
          <span>{statusNote}</span>
        </div>
      )}

      {/* Control Panel: Simulation Mode Switcher */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs mb-8">
        <div className="flex items-center space-x-2 mb-2">
          <Zap className="h-5 w-5 text-amber-500" />
          <h2 className="text-base font-bold text-slate-900">Mock EHR Fault Injection Control</h2>
        </div>
        <p className="text-xs text-slate-500 mb-5">
          Select a simulation mode to test the autonomous failure recovery, query-before-retry, and reconciliation behavior of the booking pipeline.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Mode: NORMAL */}
          <div
            onClick={() => handleModeChange('NORMAL')}
            className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
              currentMode === 'NORMAL'
                ? 'border-emerald-500 bg-emerald-50/50 shadow-sm'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-emerald-900">1. NORMAL</span>
              {currentMode === 'NORMAL' && <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />}
            </div>
            <p className="text-xs text-slate-600 mt-2">
              Clean EHR booking & immediate synchronization to <code className="text-emerald-700 font-semibold">CONFIRMED</code>.
            </p>
          </div>

          {/* Mode: TIMEOUT */}
          <div
            onClick={() => handleModeChange('TIMEOUT')}
            className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
              currentMode === 'TIMEOUT'
                ? 'border-amber-500 bg-amber-50/50 shadow-sm'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-amber-900">2. TIMEOUT</span>
              {currentMode === 'TIMEOUT' && <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />}
            </div>
            <p className="text-xs text-slate-600 mt-2">
              External request times out. System queries EHR, finds nothing, creates <code className="text-amber-700 font-semibold">RECONCILIATION_REQUIRED</code>.
            </p>
          </div>

          {/* Mode: FAILURE */}
          <div
            onClick={() => handleModeChange('FAILURE')}
            className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
              currentMode === 'FAILURE'
                ? 'border-rose-500 bg-rose-50/50 shadow-sm'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-rose-900">3. FAILURE</span>
              {currentMode === 'FAILURE' && <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />}
            </div>
            <p className="text-xs text-slate-600 mt-2">
              EHR rejects with 500. Internal slot is released back to available, appointment marked <code className="text-rose-700 font-semibold">FAILED</code>.
            </p>
          </div>

          {/* Mode: UNKNOWN_OUTCOME */}
          <div
            onClick={() => handleModeChange('UNKNOWN_OUTCOME')}
            className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
              currentMode === 'UNKNOWN_OUTCOME'
                ? 'border-indigo-500 bg-indigo-50/50 shadow-sm'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm text-indigo-900">4. UNKNOWN OUTCOME</span>
              {currentMode === 'UNKNOWN_OUTCOME' && <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />}
            </div>
            <p className="text-xs text-slate-600 mt-2">
              EHR creates appointment but response drops. Recovery queries EHR, recovers ID, synchronizes to <code className="text-indigo-700 font-semibold">CONFIRMED</code>!
            </p>
          </div>
        </div>
      </div>

      {/* Grid: Reconciliation Queue & Integration Operations Log */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Reconciliation Queue */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              <span>Reconciliation Queue ({reconciliations.length})</span>
            </h2>
          </div>

          {reconciliations.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">
              No outstanding reconciliations. All external transactions are fully synchronized.
            </div>
          ) : (
            <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
              {reconciliations.map((rec) => (
                <div key={rec.id} className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/30">
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-mono font-bold text-amber-900">
                      Appt: {rec.appointment_id.slice(0, 8)}...
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
                      {rec.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-700 mt-1">{rec.reason}</div>
                  <div className="text-[10px] text-slate-400 font-mono mt-1">
                    Correlation: {rec.correlation_id}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Integration Operations Log */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Activity className="h-5 w-5 text-blue-600" />
              <span>External Connector Operations Log ({operations.length})</span>
            </h2>
          </div>

          {operations.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">
              No recent connector operations recorded.
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {operations.map((op) => (
                <div key={op.id} className="p-3 rounded-xl border border-slate-200 bg-slate-50/50 flex justify-between items-center text-xs">
                  <div>
                    <div className="font-semibold text-slate-900">{op.operation_type}</div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                      {op.correlation_id}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      op.status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-800' :
                      op.status === 'TIMEOUT' ? 'bg-amber-100 text-amber-800' :
                      op.status === 'UNKNOWN_OUTCOME' ? 'bg-indigo-100 text-indigo-800' :
                      'bg-rose-100 text-rose-800'
                    }`}>
                      {op.status}
                    </span>
                    <div className="text-[11px] text-slate-400 mt-0.5 font-mono">{op.latency_ms}ms</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
