import React, { createContext, useContext, useState, useEffect } from 'react';
import { Site } from '../types';
import { sitesApi } from '../api';

interface SiteContextValue {
  sites: Site[];
  currentSiteId: number | null;
  currentSite: Site | null;
  setCurrentSiteId: (id: number) => void;
  loading: boolean;
}

const SiteContext = createContext<SiteContextValue | null>(null);

const STORAGE_KEY = 'ft_site_id';

export function SiteProvider({ children }: { children: React.ReactNode }) {
  const [sites, setSites] = useState<Site[]>([]);
  const [currentSiteId, setCurrentSiteIdState] = useState<number | null>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? Number(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    sitesApi
      .list(false)
      .then((r) => {
        const list = r.data as Site[];
        setSites(list);
        // Restore selection if still valid, else default to first
        setCurrentSiteIdState((prev) => {
          if (prev && list.some((s) => s.id === prev)) return prev;
          return list.length ? list[0].id : null;
        });
      })
      .catch(() => setSites([]))
      .finally(() => setLoading(false));
  }, []);

  const setCurrentSiteId = (id: number) => {
    localStorage.setItem(STORAGE_KEY, String(id));
    setCurrentSiteIdState(id);
  };

  const currentSite = sites.find((s) => s.id === currentSiteId) || null;

  return (
    <SiteContext.Provider value={{ sites, currentSiteId, currentSite, setCurrentSiteId, loading }}>
      {children}
    </SiteContext.Provider>
  );
}

export function useSite() {
  const ctx = useContext(SiteContext);
  if (!ctx) throw new Error('useSite must be used inside SiteProvider');
  return ctx;
}
