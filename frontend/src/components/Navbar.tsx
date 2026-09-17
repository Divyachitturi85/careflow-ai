import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { 
  Bot, 
  Calendar, 
  FileText, 
  Activity, 
  ShieldAlert, 
  LogOut, 
  UserCheck, 
  Hospital as HospitalIcon, 
  Stethoscope, 
  Sliders
} from 'lucide-react';
import { Role } from '../types';

export const Navbar: React.FC = () => {
  const { user, logout, switchRole } = useAuth();
  const location = useLocation();
  const [currentSimMode, setCurrentSimMode] = useState<string>('NORMAL');

  useEffect(() => {
    async function fetchMode() {
      if (user) {
        try {
          const res = await api.getSimulationMode();
          setCurrentSimMode(res.mode);
        } catch {
          // ignore if unauthorized or failed
        }
      }
    }
    fetchMode();
  }, [user, location.pathname]);

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <Link to="/" className="flex items-center space-x-2">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-teal-600 to-emerald-500 flex items-center justify-center text-white shadow-md">
                <Bot className="h-6 w-6" />
              </div>
              <div>
                <span className="font-bold text-xl tracking-tight text-slate-900">CareFlow<span className="text-teal-600">AI</span></span>
                <span className="hidden sm:inline-block ml-2 text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium">v2.0</span>
              </div>
            </Link>

            {/* Mock EHR status indicator */}
            <div className="hidden md:flex items-center space-x-1.5 ml-4 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
              <span className={`h-2 w-2 rounded-full ${currentSimMode === 'NORMAL' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500 animate-ping'}`} />
              <span>EHR: <span className="font-semibold text-slate-900">{currentSimMode}</span></span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {user?.role === 'PATIENT' && (
              <>
                <Link
                  to="/"
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                    isActive('/') ? 'bg-teal-50 text-teal-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Bot className="h-4 w-4" />
                  <span>Voice AI Assistant</span>
                </Link>
                <Link
                  to="/appointments"
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                    isActive('/appointments') ? 'bg-teal-50 text-teal-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Calendar className="h-4 w-4" />
                  <span>Appointments</span>
                </Link>
              </>
            )}

            {user?.role === 'DOCTOR' && (
              <>
                <Link
                  to="/doctor"
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                    isActive('/doctor') ? 'bg-teal-50 text-teal-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Stethoscope className="h-4 w-4" />
                  <span>Doctor Consultation Schedule</span>
                </Link>
              </>
            )}

            {user?.role === 'HOSPITAL_ADMIN' && (
              <>
                <Link
                  to="/hospital"
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                    isActive('/hospital') ? 'bg-teal-50 text-teal-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <HospitalIcon className="h-4 w-4" />
                  <span>CityCare Admin</span>
                </Link>
              </>
            )}

            {user?.role === 'PLATFORM_ADMIN' && (
              <>
                <Link
                  to="/admin"
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-1.5 ${
                    isActive('/admin') ? 'bg-teal-50 text-teal-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Sliders className="h-4 w-4" />
                  <span>Platform Operations & EHR Simulation</span>
                </Link>
              </>
            )}
          </nav>

          {/* Role switcher & User Profile */}
          <div className="flex items-center space-x-2">
            {/* Quick Demo Role Switcher */}
            <div className="hidden lg:flex items-center space-x-1 bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs">
              <span className="px-2 text-slate-500 font-medium">Demo As:</span>
              <button
                onClick={() => switchRole('PATIENT')}
                className={`px-2 py-1 rounded-lg transition-all font-medium ${
                  user?.role === 'PATIENT' ? 'bg-white shadow text-teal-700' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Patient
              </button>
              <button
                onClick={() => switchRole('DOCTOR')}
                className={`px-2 py-1 rounded-lg transition-all font-medium ${
                  user?.role === 'DOCTOR' ? 'bg-white shadow text-blue-700' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Dr. Rao
              </button>
              <button
                onClick={() => switchRole('HOSPITAL_ADMIN')}
                className={`px-2 py-1 rounded-lg transition-all font-medium ${
                  user?.role === 'HOSPITAL_ADMIN' ? 'bg-white shadow text-purple-700' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Hosp Admin
              </button>
              <button
                onClick={() => switchRole('PLATFORM_ADMIN')}
                className={`px-2 py-1 rounded-lg transition-all font-medium ${
                  user?.role === 'PLATFORM_ADMIN' ? 'bg-white shadow text-rose-700' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Platform Admin
              </button>
            </div>

            {/* User Badge & Logout */}
            {user ? (
              <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
                <div className="text-right hidden sm:block">
                  <div className="text-xs font-semibold text-slate-900">{user.first_name} {user.last_name}</div>
                  <div className="text-[10px] text-slate-500 font-mono tracking-wider">{user.role}</div>
                </div>
                <button
                  onClick={logout}
                  title="Logout"
                  className="p-2 text-slate-500 hover:text-rose-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="px-4 py-2 rounded-lg bg-teal-600 text-white font-medium text-sm hover:bg-teal-700 transition-colors shadow-sm"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
