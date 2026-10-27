"use client";

import { useEffect, useState } from "react";
import { supabase } from "../lib/supabaseClient";
import { getLocalScan } from "../lib/localScans";
import type { Scan } from "../types/scan";

interface UseScanRealtimeResult {
  scan: Scan | null;
  loading: boolean;
  error: string | null;
}

interface ScanState extends UseScanRealtimeResult {
  scanId: string;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof error.message === "string"
  ) {
    return error.message;
  }

  return "An unexpected error occurred while loading the scan.";
}

export function useScanRealtime(scanId: string): UseScanRealtimeResult {
  const [state, setState] = useState<ScanState>({
    scanId,
    scan: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let isActive = true;
    let receivedRealtimeUpdate = false;

    const channel = supabase
      ? supabase
          .channel(`scan-${scanId}`)
          .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "scans",
          filter: `id=eq.${scanId}`,
        },
        (payload) => {
          if (isActive) {
            receivedRealtimeUpdate = true;
            setState({
              scanId,
              scan: payload.new as Scan,
              loading: false,
              error: null,
            });
          }
        },
          )
          .subscribe((status) => {
        if (isActive && (status === "CHANNEL_ERROR" || status === "TIMED_OUT")) {
          setState((current) => ({
            ...(current.scanId === scanId
              ? current
              : { scanId, scan: null, loading: true, error: null }),
            error: `Realtime subscription failed: ${status}.`,
          }));
        }
          })
      : null;

    const fetchScan = async () => {
      if (!supabase) {
        const localScan = getLocalScan(scanId);
        if (isActive) {
          setState({
            scanId,
            scan: localScan,
            loading: false,
            error: null,
          });
        }
        return;
      }

      try {
        const { data, error: fetchError } = await supabase
          .from("scans")
          .select("*")
          .eq("id", scanId)
          .maybeSingle();

        if (fetchError) {
          throw fetchError;
        }

        if (isActive) {
          setState((current) => ({
            scanId,
            scan: receivedRealtimeUpdate
              ? current.scanId === scanId
                ? current.scan
                : null
              : (data as Scan | null),
            loading: false,
            error: current.scanId === scanId ? current.error : null,
          }));
        }
      } catch (fetchError: unknown) {
        if (isActive) {
          setState((current) => ({
            scanId,
            scan: current.scanId === scanId ? current.scan : null,
            loading: false,
            error: getErrorMessage(fetchError),
          }));
        }
      }
    };

    void fetchScan();

    const localUpdate = () => {
      if (!supabase && isActive) {
        setState((current) => ({
          ...current,
          scan: getLocalScan(scanId),
          loading: false,
        }));
      }
    };
    window.addEventListener("traceguard:scan-updated", localUpdate);

    return () => {
      isActive = false;
      window.removeEventListener("traceguard:scan-updated", localUpdate);
      if (supabase && channel) {
        void supabase.removeChannel(channel);
      }
    };
  }, [scanId]);

  if (state.scanId !== scanId) {
    return { scan: null, loading: true, error: null };
  }

  return { scan: state.scan, loading: state.loading, error: state.error };
}
