import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api } from "./api";

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const epoch = useRef(0);
  const clearSession = useCallback(() => {
    epoch.current += 1;
    setUser(false);
    try { sessionStorage.removeItem("usp-live-edit"); } catch { /* restricted storage */ }
  }, []);
  const refresh = useCallback(async () => {
    const requestEpoch = epoch.current;
    try {
      let result;
      try { result = await api.get("/auth/me"); }
      catch (error) {
        if (error.response?.status !== 401) throw error;
        await api.post("/auth/refresh");
        result = await api.get("/auth/me");
      }
      if (epoch.current === requestEpoch) setUser(result.data);
    } catch (error) {
      if (epoch.current === requestEpoch && error.response?.status === 401) clearSession();
    }
  }, [clearSession]);
  useEffect(() => {
    refresh();
    const focus = () => { if (document.visibilityState === "visible") refresh(); };
    const storage = (event) => { if (event.key === "usp-auth-event") { if (event.newValue?.startsWith("logout:")) clearSession(); else refresh(); } };
    window.addEventListener("focus", focus);
    window.addEventListener("storage", storage);
    window.addEventListener("usp-session-expired", clearSession);
    return () => { window.removeEventListener("focus", focus); window.removeEventListener("storage", storage); window.removeEventListener("usp-session-expired", clearSession); };
  }, [refresh, clearSession]);
  const logout = async () => {
    await api.post("/auth/logout");
    clearSession();
    try { localStorage.setItem("usp-auth-event", `logout:${Date.now()}`); } catch { /* restricted storage */ }
  };
  const can = (p) => !!user && user.permissions?.includes(p);
  const setSession = (value) => {
    epoch.current += 1;
    setUser(value);
    try { localStorage.setItem("usp-auth-event", `login:${Date.now()}`); } catch { /* restricted storage */ }
  };
  return <AuthCtx.Provider value={{ user, setUser: setSession, logout, can, refresh }}>{children}</AuthCtx.Provider>;
}

export function RequireAuth({ children }) {
  const { user } = useAuth();
  const loc = useLocation();
  if (user === null) return <div className="admin p-10" data-testid="auth-loading">Checking your session…</div>;
  if (!user) return <Navigate to={`/admin/login?next=${encodeURIComponent(loc.pathname)}`} replace />;
  return children;
}
