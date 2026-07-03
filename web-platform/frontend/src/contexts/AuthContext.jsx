import { createContext, useContext, useEffect, useState } from 'react';
import * as authApi from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('auth_user');
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) return;
    const token = localStorage.getItem('auth_token');
    if (!token) return;
    setLoading(true);
    authApi
      .fetchMe()
      .then((res) => {
        if (res?.success) {
          setUser(res.data.user);
          localStorage.setItem('auth_user', JSON.stringify(res.data.user));
        }
      })
      .finally(() => setLoading(false));
  }, [user]);

  const login = async (username, password) => {
    const res = await authApi.login(username, password);
    if (!res?.success) throw new Error(res?.error?.message || 'Login failed');
    localStorage.setItem('auth_token', res.data.token);
    localStorage.setItem('auth_user', JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data.user;
  };

  const register = async (payload) => {
    const res = await authApi.register(payload);
    if (!res?.success) throw new Error(res?.error?.message || 'Registration failed');
    localStorage.setItem('auth_token', res.data.token);
    localStorage.setItem('auth_user', JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data.user;
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (_) {}
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
