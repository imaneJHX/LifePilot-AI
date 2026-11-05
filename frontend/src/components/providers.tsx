"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api, ApiError, errorMessage } from "@/lib/api";
import type { Profile, ProfileInput } from "@/lib/types";

interface ProfileContextValue {
  profile: Profile | null;
  loading: boolean;
  error: string | null;
  save: (input: ProfileInput) => Promise<Profile>;
  forget: () => void;
  retry: () => void;
}
const ProfileContext = createContext<ProfileContextValue | null>(null);
const STORAGE_KEY = "lifepilot.profile-id";

export function Providers({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const restore = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const id = localStorage.getItem(STORAGE_KEY);
      if (id) setProfile(await api.getProfile(id));
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        localStorage.removeItem(STORAGE_KEY);
        setProfile(null);
      } else setError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    // Restore browser-only persistence after mount; cancel if the provider is removed.
    const timer = setTimeout(() => void restore(), 0);
    return () => clearTimeout(timer);
  }, [restore]);
  const save = async (input: ProfileInput) => {
    const next = await api.createProfile(input);
    setProfile(next);
    setError(null);
    try {
      localStorage.setItem(STORAGE_KEY, next.id);
    } catch {
      /* Session still works without browser storage. */
    }
    return next;
  };
  const forget = () => {
    setProfile(null);
    setError(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* Browser storage may be disabled. */
    }
  };
  return (
    <ProfileContext.Provider
      value={{
        profile,
        loading,
        error,
        save,
        forget,
        retry: () => void restore(),
      }}
    >
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile() {
  const context = useContext(ProfileContext);
  if (!context) throw new Error("useProfile must be used within Providers");
  return context;
}
