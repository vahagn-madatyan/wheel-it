'use client';

import React from 'react';

/* ── Shared types ── */

export interface ProviderStatus {
  provider: string;
  connected: boolean;
  is_paper: boolean | null;
  key_names: string[];
}

export interface KeyStatusResponse {
  providers: ProviderStatus[];
}

export interface VerifyResponse {
  provider: string;
  valid: boolean;
  error?: string;
}

export interface ProviderFormState {
  loading: boolean;
  error: string | null;
  verifyResult: VerifyResponse | null;
}

export const INITIAL_FORM: ProviderFormState = {
  loading: false,
  error: null,
  verifyResult: null,
};

export interface FormField {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}

export interface ProviderCardProps {
  name: string;
  status: ProviderStatus | undefined;
  formState: ProviderFormState;
  fields: FormField[];
  onSave: (e: React.FormEvent<HTMLFormElement>) => void;
  onVerify: () => void;
  onDelete: () => void;
  /** Extra form content rendered after the fields, before the submit button (e.g. paper toggle) */
  extraFormContent?: React.ReactNode;
}

/* ── Badge components ── */

function ConnectedBadge() {
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
      Connected
    </span>
  );
}

function DisconnectedBadge() {
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
      Not connected
    </span>
  );
}

function PaperBadge({ isPaper }: { isPaper: boolean | null }) {
  if (isPaper === null) return null;
  return isPaper ? (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
      Paper
    </span>
  ) : (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
      Live
    </span>
  );
}

/* ── Provider Card ── */

export function ProviderCard({
  name,
  status,
  formState,
  fields,
  onSave,
  onVerify,
  onDelete,
  extraFormContent,
}: ProviderCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">{name}</h2>
        <div className="flex items-center gap-2">
          {status?.connected ? <ConnectedBadge /> : <DisconnectedBadge />}
          {status?.connected && <PaperBadge isPaper={status.is_paper} />}
        </div>
      </div>

      {/* Verify result */}
      {formState.verifyResult && (
        <div
          className={`mb-4 p-3 rounded-md text-sm ${
            formState.verifyResult.valid
              ? 'bg-green-50 border border-green-200 text-green-700'
              : 'bg-red-50 border border-red-200 text-red-700'
          }`}
          role="alert"
        >
          {formState.verifyResult.valid
            ? `✓ ${name} keys verified — connection is working`
            : `✗ Verification failed: ${formState.verifyResult.error ?? 'Unknown error'}`}
        </div>
      )}

      {/* Error */}
      {formState.error && (
        <div
          className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm"
          role="alert"
        >
          {formState.error}
        </div>
      )}

      {status?.connected ? (
        /* Connected state — show stored keys + actions */
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            Stored keys:{' '}
            <span className="font-medium text-gray-900">{status.key_names.join(', ')}</span>
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onVerify}
              disabled={formState.loading}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {formState.loading ? 'Verifying…' : 'Verify'}
            </button>
            <button
              type="button"
              onClick={onDelete}
              disabled={formState.loading}
              className="px-4 py-2 bg-red-50 text-red-700 text-sm rounded-md font-medium hover:bg-red-100 border border-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {formState.loading ? 'Deleting…' : 'Delete'}
            </button>
          </div>
        </div>
      ) : (
        /* Disconnected state — show key entry form */
        <form onSubmit={onSave} className="space-y-4">
          {fields.map((field) => (
            <div key={field.id}>
              <label
                htmlFor={field.id}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                {field.label}
              </label>
              <input
                id={field.id}
                type="password"
                required
                value={field.value}
                onChange={(e) => field.onChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900"
                placeholder={field.placeholder}
                disabled={formState.loading}
              />
            </div>
          ))}

          {extraFormContent}

          <button
            type="submit"
            disabled={formState.loading}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {formState.loading ? 'Saving…' : 'Save & Verify'}
          </button>
        </form>
      )}
    </div>
  );
}
