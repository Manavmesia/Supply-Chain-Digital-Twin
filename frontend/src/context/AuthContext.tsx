import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../services/api';

export interface AuthUser {
  username: string;
  role: string;
}

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  loading: true,
  login: async () => false,
  logout: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const token = localStorage.getItem('access_token');
      const savedUser = localStorage.getItem('user_info');
      if (token && savedUser) {
        setUser(JSON.parse(savedUser));
      } else if (token) {
        // Try decoding JWT payload
        const parts = token.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1]));
          const parsedUser = {
            username: payload.sub || 'user',
            role: payload.role || 'operator',
          };
          setUser(parsedUser);
          localStorage.setItem('user_info', JSON.stringify(parsedUser));
        }
      }
    } catch (e) {
      console.warn('Failed to restore auth session:', e);
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
    } finally {
      setLoading(false);
    }
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const data = await authApi.login(username, password);
      if (data && data.access_token) {
        let role = 'operator';
        try {
          const parts = data.access_token.split('.');
          if (parts.length === 3) {
            const payload = JSON.parse(atob(parts[1]));
            if (payload.role) role = payload.role;
          }
        } catch {
          // fallback role
        }
        const authUser: AuthUser = { username, role };
        setUser(authUser);
        localStorage.setItem('user_info', JSON.stringify(authUser));
        return true;
      }
      return false;
    } catch (err) {
      console.error('Login failed:', err);
      return false;
    }
  };

  const logout = () => {
    authApi.logout();
    localStorage.removeItem('user_info');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
