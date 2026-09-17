import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, Role } from '../types';
import { api } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  switchRole: (role: Role) => Promise<void>;
  isPatient: boolean;
  isDoctor: boolean;
  isHospitalAdmin: boolean;
  isPlatformAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEMO_CREDENTIALS: Record<Role, { email: string; pass: string }> = {
  PATIENT: { email: 'patient@example.com', pass: 'Patient@123' },
  DOCTOR: { email: 'doctor.rao@example.com', pass: 'Doctor@123' },
  HOSPITAL_ADMIN: { email: 'hospital.admin@example.com', pass: 'Hospital@123' },
  PLATFORM_ADMIN: { email: 'platform.admin@example.com', pass: 'Admin@123' },
};

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function checkAuth() {
      if (token) {
        try {
          const me = await api.getMe();
          setUser(me);
          localStorage.setItem('user', JSON.stringify(me));
        } catch {
          setUser(null);
          setToken(null);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
      setIsLoading(false);
    }
    checkAuth();
  }, [token]);

  const login = async (email: string, pass: string) => {
    setIsLoading(true);
    try {
      const resp = await api.login(email, pass);
      localStorage.setItem('token', resp.access_token);
      setToken(resp.access_token);
      const me = await api.getMe();
      localStorage.setItem('user', JSON.stringify(me));
      setUser(me);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  const switchRole = async (role: Role) => {
    const creds = DEMO_CREDENTIALS[role];
    if (creds) {
      await login(creds.email, creds.pass);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        switchRole,
        isPatient: user?.role === 'PATIENT',
        isDoctor: user?.role === 'DOCTOR',
        isHospitalAdmin: user?.role === 'HOSPITAL_ADMIN',
        isPlatformAdmin: user?.role === 'PLATFORM_ADMIN',
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};
