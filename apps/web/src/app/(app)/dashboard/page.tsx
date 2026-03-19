'use client';

import { useState, useEffect, useCallback } from 'react';
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

/* ── Types matching API response shapes ── */

interface AccountData {
  buying_power: string;
  portfolio_value: string;
  cash: string;
  capital_at_risk: number;
}

interface Position {
  symbol: string;
  qty: string;
  avg_entry_price: string;
  market_value: string | null;
  asset_class: string;
  side: string | null;
}

interface WheelStateEntry {
  type: string;
  price: number | null;
  qty: number | null;
}

interface PositionsData {
  positions: Position[];
  wheel_state: Record<string, WheelStateEntry>;
}

/* ── Column definitions for positions table ── */

const POSITION_COLUMNS: ColumnDef[] = [
  { key: 'symbol', label: 'Symbol', sortable: true },
  { key: 'qty', label: 'Qty', sortable: true },
  {
    key: 'avg_entry_price',
    label: 'Avg Entry',
    sortable: true,
    format: (v) => (v != null ? `$${Number(v).toFixed(2)}` : '—'),
  },
  {
    key: 'market_value',
    label: 'Market Value',
    sortable: true,
    format: (v) => (v != null ? `$${Number(v).toFixed(2)}` : '—'),
  },
  { key: 'asset_class', label: 'Asset Class', sortable: true },
  { key: 'side', label: 'Side', sortable: true },
];

/* ── Formatting helpers ── */

function formatCurrency(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';
  return num.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const WHEEL_BADGE_STYLES: Record<string, string> = {
  short_put: 'bg-blue-100 text-blue-800',
  long_shares: 'bg-green-100 text-green-800',
  short_call: 'bg-orange-100 text-orange-800',
};

const WHEEL_LABELS: Record<string, string> = {
  short_put: 'Short Put',
  long_shares: 'Long Shares',
  short_call: 'Short Call',
};

/* ── Page ── */

export default function DashboardPage() {
  /* Key connectivity */
  const [alpacaConnected, setAlpacaConnected] = useState<boolean | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);

  /* Data state */
  const [account, setAccount] = useState<AccountData | null>(null);
  const [positionsData, setPositionsData] = useState<PositionsData | null>(null);
  const [dataLoading, setDataLoading] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);

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

  /* ── Fetch account + positions once keys are connected ── */

  const fetchDashboardData = useCallback(async () => {
    setDataLoading(true);
    setDataError(null);
    try {
      const [accountRes, positionsRes] = await Promise.all([
        apiFetch('/api/account'),
        apiFetch('/api/positions'),
      ]);

      if (!accountRes.ok) {
        throw new Error(`Failed to load account data (${accountRes.status})`);
      }
      if (!positionsRes.ok) {
        throw new Error(`Failed to load positions (${positionsRes.status})`);
      }

      const [accountJson, positionsJson] = await Promise.all([
        accountRes.json() as Promise<AccountData>,
        positionsRes.json() as Promise<PositionsData>,
      ]);

      setAccount(accountJson);
      setPositionsData(positionsJson);
    } catch (err) {
      setDataError(
        err instanceof Error ? err.message : 'Failed to load dashboard data'
      );
    } finally {
      setDataLoading(false);
    }
  }, []);

  useEffect(() => {
    if (alpacaConnected) {
      fetchDashboardData();
    }
  }, [alpacaConnected, fetchDashboardData]);

  /* ── Render: Loading key status ── */

  if (statusLoading) {
    return (
      <div className="max-w-5xl">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-4 text-gray-500">Checking API key status…</p>
      </div>
    );
  }

  /* ── Render: Key status error ── */

  if (statusError) {
    return (
      <div className="max-w-5xl">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div
          className="mt-4 p-4 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm"
          role="alert"
        >
          {statusError}
        </div>
      </div>
    );
  }

  /* ── Render: Alpaca not connected ── */

  if (!alpacaConnected) {
    return (
      <div className="max-w-5xl">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
          <p className="text-gray-600">
            Connect your Alpaca API keys to view positions.
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

  /* ── Render: Loading dashboard data ── */

  if (dataLoading) {
    return (
      <div className="max-w-5xl">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className="mt-8 flex flex-col items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="mt-4 text-gray-600">Loading dashboard…</p>
        </div>
      </div>
    );
  }

  /* ── Render: Data fetch error ── */

  if (dataError) {
    return (
      <div className="max-w-5xl">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div
          className="mt-4 p-4 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm"
          role="alert"
        >
          {dataError}
        </div>
      </div>
    );
  }

  /* ── Derived data ── */

  const wheelEntries = positionsData
    ? Object.entries(positionsData.wheel_state)
    : [];

  /* ── Render: Dashboard ── */

  return (
    <div className="max-w-5xl">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
      <p className="mt-2 text-gray-600">
        Account overview and current positions.
      </p>

      {/* Account summary card */}
      {account && (
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900">Account Summary</h2>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                Buying Power
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {formatCurrency(account.buying_power)}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                Portfolio Value
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {formatCurrency(account.portfolio_value)}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cash
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {formatCurrency(account.cash)}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                Capital at Risk
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {formatCurrency(account.capital_at_risk)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Wheel state badges */}
      {wheelEntries.length > 0 && (
        <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900">Wheel State</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {wheelEntries.map(([symbol, entry]) => (
              <span
                key={symbol}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${
                  WHEEL_BADGE_STYLES[entry.type] ?? 'bg-gray-100 text-gray-800'
                }`}
              >
                <span className="font-semibold">{symbol}</span>
                <span className="text-xs opacity-75">
                  {WHEEL_LABELS[entry.type] ?? entry.type}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Positions table */}
      <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Positions
            {positionsData && (
              <span className="ml-2 text-sm font-normal text-gray-500">
                ({positionsData.positions.length})
              </span>
            )}
          </h2>
        </div>
        {positionsData && positionsData.positions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No open positions
          </div>
        ) : (
          <ScreenerResultsTable
            columns={POSITION_COLUMNS}
            data={
              (positionsData?.positions ?? []) as unknown as Record<
                string,
                unknown
              >[]
            }
          />
        )}
      </div>
    </div>
  );
}
