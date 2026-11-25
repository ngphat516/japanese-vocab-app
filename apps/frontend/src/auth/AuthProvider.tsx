import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useSyncExternalStore, type ReactNode } from 'react';
import { tokenStore } from '@/api/client';
import { auth } from '@/api/endpoints';
import type { Profile } from '@/api/types';

interface AuthValue {
  user: Profile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

const subscribe = (cb: () => void) => tokenStore.subscribe(cb);
const snapshot = () => (tokenStore.access ? 'a' : '') + (tokenStore.refresh ? 'r' : '');

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const tokens = useSyncExternalStore(subscribe, snapshot);
  const hasSession = tokens.length > 0;

  const me = useQuery({ queryKey: ['me'], queryFn: auth.me, enabled: hasSession, retry: false, staleTime: 5 * 60_000 });

  // Session ended elsewhere (refresh failed): drop cached user data, then refetch what is
  // on screen as a guest. Only on a true -> false transition: running this on a guest's
  // first render would remove (and abort) the guest's own in-flight queries.
  const hadSession = useRef(hasSession);
  useEffect(() => {
    const was = hadSession.current;
    hadSession.current = hasSession;
    if (was && !hasSession) {
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'public' });
      void qc.refetchQueries({ type: 'active' });
    }
  }, [hasSession, qc]);

  const login = useCallback(
    async (email: string, password: string) => {
      const t = await auth.login(email, password);
      tokenStore.set(t.access_token, t.refresh_token);
      await qc.invalidateQueries();
    },
    [qc],
  );

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      await auth.register(email, password, displayName);
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    const r = tokenStore.refresh;
    tokenStore.clear();
    qc.clear();
    if (r) await auth.logout(r).catch(() => undefined);
  }, [qc]);

  const value = useMemo<AuthValue>(
    () => ({
      user: hasSession ? (me.data ?? null) : null,
      loading: hasSession && me.isPending,
      login,
      register,
      logout,
    }),
    [hasSession, me.data, me.isPending, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
