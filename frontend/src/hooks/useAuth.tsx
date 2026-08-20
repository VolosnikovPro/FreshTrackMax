import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, UserRole } from '../types';
import { authApi } from '../api';

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (...roles: UserRole[]) => boolean;
}

declare global {
  interface Window {
    WebApp: any
  }
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('ft_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem('ft_token')
  );
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!user) {
      if (window.WebApp?.initData) {
        setLoading(true);
        const foo = async () => {
          const res = await authApi.loginMax(window.WebApp.initData);
          const { access_token, user: u } = res.data;
          localStorage.setItem('ft_token', access_token);
          localStorage.setItem('ft_user', JSON.stringify(u));
          setToken(access_token);
          setUser(u);
          setLoading(false);
        };
        foo();
      }
    }
  }, []);

  const login = async (username: string, password: string) => {
    const res = await authApi.login(username, password);
    const { access_token, user: u } = res.data;
    localStorage.setItem('ft_token', access_token);
    localStorage.setItem('ft_user', JSON.stringify(u));
    setToken(access_token);
    setUser(u);
  };

  const logout = () => {
    localStorage.removeItem('ft_token');
    localStorage.removeItem('ft_user');
    setToken(null);
    setUser(null);
  };

  const hasRole = (...roles: UserRole[]) =>
    user ? roles.includes(user.role) : false;

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
