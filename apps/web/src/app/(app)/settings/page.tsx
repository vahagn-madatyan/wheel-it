'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/api-client';
import {
  ProviderCard,
  INITIAL_FORM,
  type ProviderStatus,
  type ProviderFormState,
  type VerifyResponse,
  type KeyStatusResponse,
} from '@/components/provider-card';

/* ── Main page ── */

export default function SettingsPage() {
  /* Provider status from backend */
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [statusError, setStatusError] = useState<string | null>(null);

  /* Per-provider form state */
  const [alpacaForm, setAlpacaForm] = useState<ProviderFormState>(INITIAL_FORM);
  const [finnhubForm, setFinnhubForm] = useState<ProviderFormState>(INITIAL_FORM);

  /* Alpaca form inputs */
  const [alpacaApiKey, setAlpacaApiKey] = useState('');
  const [alpacaSecretKey, setAlpacaSecretKey] = useState('');
  const [isPaper, setIsPaper] = useState(true);

  /* Finnhub form inputs */
  const [finnhubApiKey, setFinnhubApiKey] = useState('');

  /* ── Fetch status ── */

  const fetchStatus = useCallback(async () => {
    try {
      setStatusError(null);
      const res = await apiFetch('/api/keys/status');
      if (!res.ok) {
        throw new Error(`Status fetch failed (${res.status})`);
      }
      const data: KeyStatusResponse = await res.json();
      setProviders(data.providers);
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : 'Failed to load key status');
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  /* ── Helpers ── */

  function getProvider(name: string): ProviderStatus | undefined {
    return providers.find((p) => p.provider === name);
  }

  /* ── Alpaca handlers ── */

  async function handleAlpacaSave(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setAlpacaForm({ loading: true, error: null, verifyResult: null });

    try {
      const res1 = await apiFetch('/api/keys/alpaca', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_value: alpacaApiKey, key_name: 'api_key', is_paper: isPaper }),
      });
      if (!res1.ok) {
        const body = await res1.json().catch(() => null);
        throw new Error(body?.detail ?? `Failed to store API key (${res1.status})`);
      }

      const res2 = await apiFetch('/api/keys/alpaca', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_value: alpacaSecretKey, key_name: 'secret_key', is_paper: isPaper }),
      });
      if (!res2.ok) {
        throw new Error('Failed to store secret key — please retry');
      }

      const verifyRes = await apiFetch('/api/keys/alpaca/verify', { method: 'POST' });
      const verifyData: VerifyResponse = await verifyRes.json();

      setAlpacaForm({ loading: false, error: null, verifyResult: verifyData });
      setAlpacaApiKey('');
      setAlpacaSecretKey('');
    } catch (err) {
      setAlpacaForm({
        loading: false,
        error: err instanceof Error ? err.message : 'An unexpected error occurred',
        verifyResult: null,
      });
    }

    await fetchStatus();
  }

  async function handleAlpacaVerify() {
    setAlpacaForm((prev) => ({ ...prev, loading: true, error: null, verifyResult: null }));
    try {
      const res = await apiFetch('/api/keys/alpaca/verify', { method: 'POST' });
      const data: VerifyResponse = await res.json();
      setAlpacaForm({ loading: false, error: null, verifyResult: data });
    } catch (err) {
      setAlpacaForm({
        loading: false,
        error: err instanceof Error ? err.message : 'Verification failed',
        verifyResult: null,
      });
    }
  }

  async function handleAlpacaDelete() {
    if (!window.confirm('Delete all stored keys for Alpaca? This cannot be undone.')) return;
    setAlpacaForm({ loading: true, error: null, verifyResult: null });
    try {
      const res = await apiFetch('/api/keys/alpaca', { method: 'DELETE' });
      if (!res.ok) throw new Error(`Delete failed (${res.status})`);
    } catch (err) {
      setAlpacaForm({
        loading: false,
        error: err instanceof Error ? err.message : 'Delete failed',
        verifyResult: null,
      });
    }
    setAlpacaForm((prev) => ({ ...prev, loading: false }));
    await fetchStatus();
  }

  /* ── Finnhub handlers ── */

  async function handleFinnhubSave(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFinnhubForm({ loading: true, error: null, verifyResult: null });

    try {
      const res = await apiFetch('/api/keys/finnhub', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_value: finnhubApiKey, key_name: 'api_key' }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? `Failed to store key (${res.status})`);
      }

      const verifyRes = await apiFetch('/api/keys/finnhub/verify', { method: 'POST' });
      const verifyData: VerifyResponse = await verifyRes.json();

      setFinnhubForm({ loading: false, error: null, verifyResult: verifyData });
      setFinnhubApiKey('');
    } catch (err) {
      setFinnhubForm({
        loading: false,
        error: err instanceof Error ? err.message : 'An unexpected error occurred',
        verifyResult: null,
      });
    }

    await fetchStatus();
  }

  async function handleFinnhubVerify() {
    setFinnhubForm((prev) => ({ ...prev, loading: true, error: null, verifyResult: null }));
    try {
      const res = await apiFetch('/api/keys/finnhub/verify', { method: 'POST' });
      const data: VerifyResponse = await res.json();
      setFinnhubForm({ loading: false, error: null, verifyResult: data });
    } catch (err) {
      setFinnhubForm({
        loading: false,
        error: err instanceof Error ? err.message : 'Verification failed',
        verifyResult: null,
      });
    }
  }

  async function handleFinnhubDelete() {
    if (!window.confirm('Delete all stored keys for Finnhub? This cannot be undone.')) return;
    setFinnhubForm({ loading: true, error: null, verifyResult: null });
    try {
      const res = await apiFetch('/api/keys/finnhub', { method: 'DELETE' });
      if (!res.ok) throw new Error(`Delete failed (${res.status})`);
    } catch (err) {
      setFinnhubForm({
        loading: false,
        error: err instanceof Error ? err.message : 'Delete failed',
        verifyResult: null,
      });
    }
    setFinnhubForm((prev) => ({ ...prev, loading: false }));
    await fetchStatus();
  }

  /* ── Render ── */

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
      <p className="mt-2 text-gray-600">
        Manage your API keys for Alpaca and Finnhub. Keys are encrypted at rest.
      </p>

      {statusError && (
        <div
          className="mt-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm"
          role="alert"
        >
          {statusError}
        </div>
      )}

      <div className="mt-6 space-y-6">
        <ProviderCard
          name="Alpaca"
          status={getProvider('alpaca')}
          formState={alpacaForm}
          fields={[
            {
              id: 'alpaca-api-key',
              label: 'API Key',
              placeholder: 'ALPACA_API_KEY',
              value: alpacaApiKey,
              onChange: setAlpacaApiKey,
            },
            {
              id: 'alpaca-secret-key',
              label: 'Secret Key',
              placeholder: 'ALPACA_SECRET_KEY',
              value: alpacaSecretKey,
              onChange: setAlpacaSecretKey,
            },
          ]}
          onSave={handleAlpacaSave}
          onVerify={handleAlpacaVerify}
          onDelete={handleAlpacaDelete}
          extraFormContent={
            <div className="flex items-center gap-3">
              <label htmlFor="alpaca-paper" className="relative inline-flex items-center cursor-pointer">
                <input
                  id="alpaca-paper"
                  type="checkbox"
                  checked={isPaper}
                  onChange={(e) => setIsPaper(e.target.checked)}
                  disabled={alpacaForm.loading}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600" />
              </label>
              <span className="text-sm text-gray-700">
                {isPaper ? 'Paper trading' : 'Live trading'}
              </span>
            </div>
          }
        />

        <ProviderCard
          name="Finnhub"
          status={getProvider('finnhub')}
          formState={finnhubForm}
          fields={[
            {
              id: 'finnhub-api-key',
              label: 'API Key',
              placeholder: 'FINNHUB_API_KEY',
              value: finnhubApiKey,
              onChange: setFinnhubApiKey,
            },
          ]}
          onSave={handleFinnhubSave}
          onVerify={handleFinnhubVerify}
          onDelete={handleFinnhubDelete}
        />
      </div>
    </div>
  );
}
