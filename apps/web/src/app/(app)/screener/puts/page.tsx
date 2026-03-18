'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import { apiFetch } from '@/lib/api-client';
import {
  ScreenerResultsTable,
  type ColumnDef,
} from '@/components/screener-results-table';
import type {
  ProviderStatus,
  KeyStatusResponse,
} from '@/components/provider-card';

/* ── Column definitions for put screener results ── */

const PUT_COLUMNS: ColumnDef[] = [
  { key: 'symbol', label: 'Symbol', sortable: true },
  { key: 'underlying', label: 'Underlying', sortable: true },
  {
    key: 'strike',
    label: 'Strike',
    sortable: true,
    format: (v) => (v != null ? `$${Number(v).toFixed(2)}` : '—'),
  },
  { key: 'dte', label: 'DTE', sortable: true },
  {
    key: 'premium',
    label: 'Premium',
    sortable: true,
    format: (v) => (v != null ? `$${Number(v).toFixed(2)}` : '—'),
  },
  {
    key: 'delta',
    label: 'Delta',
    sortable: true,
    format: (v) => (v != null ? Number(v).toFixed(2) : '—'),
  },
  {
    key: 'oi',
    label: 'OI',
    sortable: true,
    format: (v) => (v != null ? Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 }) : '—'),
  },
  {
    key: 'spread',
    label: 'Spread',
    sortable: true,
    format: (v) => (v != null ? Number(v).toFixed(2) : '—'),
  },
  {
    key: 'annualized_return',
    label: 'Ann. Return',
    sortable: true,
    format: (v) => (v != null ? `${Number(v).toFixed(2)}%` : '—'),
  },
];

/* ── Types for poll response ── */

interface PutResult {
  symbol: string;
  underlying: string;
  strike: number;
  dte: number;
  premium: number;
  delta: number | null;
  oi: number;
  spread: number;
  annualized_return: number;
}

interface RunStatusResponse {
  run_id: string;
  status: string;
  run_type: string;
  results: PutResult[] | null;
  error: string | null;
}

/* ── Page ── */

export default function PutScreenerPage() {
  /* Key connectivity */
  const [alpacaConnected, setAlpacaConnected] = useState<boolean | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);

  /* Form inputs */
  const [preset, setPreset] = useState('moderate');
  const [symbolsText, setSymbolsText] = useState('');
  const [buyingPower, setBuyingPower] = useState('');

  /* Screening state */
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<PutResult[] | null>(null);

  /* Polling ref */
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* ── Key status check on mount ── */

  const fetchKeyStatus = useCallback(async () => {
    try {
      setStatusLoading(true);
      setStatusError(null);
      const res = await apiFetch('/api/keys/status');
      if (!res.ok) {
        throw new Error(`Failed to load key status (${res.status})`);
      }
      const data: KeyStatusResponse = await res.json();
      const alpaca = data.providers.find(
        (p: ProviderStatus) => p.provider === 'alpaca'
      );
      setAlpacaConnected(alpaca?.connected ?? false);
    } catch (err) {
      setStatusError(
        err instanceof Error ? err.message : 'Failed to check key status'
      );
      setAlpacaConnected(false);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKeyStatus();
  }, [fetchKeyStatus]);

  /* ── Cleanup polling on unmount ── */

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  /* ── Polling logic ── */

  function startPolling(runId: string) {
    intervalRef.current = setInterval(async () => {
      try {
        const res = await apiFetch(`/api/screen/runs/${runId}`);
        if (!res.ok) {
          throw new Error(`Poll failed (${res.status})`);
        }
        const data: RunStatusResponse = await res.json();

        if (data.status === 'completed') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          intervalRef.current = null;
          setResults(data.results ?? []);
          setLoading(false);
        } else if (data.status === 'failed') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          intervalRef.current = null;
          setError(data.error ?? 'Screening failed');
          setLoading(false);
        }
        // "pending" or "running" → continue polling
      } catch (err) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        intervalRef.current = null;
        setError(
          err instanceof Error ? err.message : 'Polling error'
        );
        setLoading(false);
      }
    }, 2000);
  }

  /* ── Submit handler ── */

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setResults(null);

    // Parse symbols
    const symbols = symbolsText
      .split(/[\s,]+/)
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);

    if (symbols.length === 0) {
      setError('Enter at least one symbol');
      return;
    }

    const bp = parseFloat(buyingPower);
    if (!bp || bp <= 0) {
      setError('Buying power must be greater than 0');
      return;
    }

    setLoading(true);

    try {
      const res = await apiFetch('/api/screen/puts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols,
          buying_power: bp,
          preset,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(
          body?.detail ?? `Screening request failed (${res.status})`
        );
      }

      const data: { run_id: string; status: string } = await res.json();
      startPolling(data.run_id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to start screening'
      );
      setLoading(false);
    }
  }

  /* ── Render: Loading key status ── */

  if (statusLoading) {
    return (
      <div className="max-w-4xl">
        <h1 className="text-2xl font-bold text-gray-900">Put Screener</h1>
        <p className="mt-4 text-gray-500">Checking API key status…</p>
      </div>
    );
  }

  /* ── Render: Key status error ── */

  if (statusError) {
    return (
      <div className="max-w-4xl">
        <h1 className="text-2xl font-bold text-gray-900">Put Screener</h1>
        <div className="mt-4 p-4 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm" role="alert">
          {statusError}
        </div>
      </div>
    );
  }

  /* ── Render: Alpaca not connected ── */

  if (!alpacaConnected) {
    return (
      <div className="max-w-4xl">
        <h1 className="text-2xl font-bold text-gray-900">Put Screener</h1>
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
          <p className="text-gray-600">
            Connect your Alpaca API keys to use the screener.
          </p>
          <Link
            href="/settings"
            className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white text-sm rounded-md font-medium hover:bg-blue-700 transition-colors"
          >
            Go to Settings
          </Link>
        </div>
      </div>
    );
  }

  /* ── Render: Main screener UI ── */

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-900">Put Screener</h1>
      <p className="mt-2 text-gray-600">
        Screen for cash-secured puts across your selected symbols.
      </p>

      {/* Form */}
      <form onSubmit={handleSubmit} className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
        {/* Preset */}
        <div>
          <label htmlFor="preset" className="block text-sm font-medium text-gray-700 mb-1">
            Preset
          </label>
          <select
            id="preset"
            value={preset}
            onChange={(e) => setPreset(e.target.value)}
            disabled={loading}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
          >
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="aggressive">Aggressive</option>
          </select>
        </div>

        {/* Symbols */}
        <div>
          <label htmlFor="symbols" className="block text-sm font-medium text-gray-700 mb-1">
            Symbols
          </label>
          <textarea
            id="symbols"
            value={symbolsText}
            onChange={(e) => setSymbolsText(e.target.value)}
            placeholder={'AAPL\nMSFT\nGOOG'}
            rows={4}
            disabled={loading}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900"
          />
          <p className="mt-1 text-xs text-gray-500">
            One symbol per line, or separated by commas/spaces
          </p>
        </div>

        {/* Buying Power */}
        <div>
          <label htmlFor="buying-power" className="block text-sm font-medium text-gray-700 mb-1">
            Buying Power
          </label>
          <input
            id="buying-power"
            type="number"
            step="100"
            min="1000"
            value={buyingPower}
            onChange={(e) => setBuyingPower(e.target.value)}
            placeholder="50000"
            required
            disabled={loading}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900"
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 px-4 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Screening…' : 'Run Screener'}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div
          className="mt-4 p-4 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Progress indicator */}
      {loading && (
        <div className="mt-8 flex flex-col items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="mt-4 text-gray-600">Screening in progress…</p>
        </div>
      )}

      {/* Results */}
      {results && !loading && (
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Results ({results.length})
            </h2>
          </div>
          <ScreenerResultsTable
            columns={PUT_COLUMNS}
            data={results as unknown as Record<string, unknown>[]}
          />
        </div>
      )}
    </div>
  );
}
