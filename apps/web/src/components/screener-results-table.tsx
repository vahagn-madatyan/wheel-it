'use client';

import { useState, useMemo } from 'react';

/* ── Types ── */

export interface ColumnDef {
  key: string;
  label: string;
  sortable?: boolean;
  /** Custom formatter for cell values. Falls back to String(value). */
  format?: (v: unknown) => string;
}

interface ScreenerResultsTableProps {
  columns: ColumnDef[];
  data: Record<string, unknown>[];
}

/* ── Component ── */

export function ScreenerResultsTable({ columns, data }: ScreenerResultsTableProps) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  function handleSort(key: string) {
    if (sortKey === key) {
      if (sortDir === 'asc') {
        setSortDir('desc');
      } else {
        // Third click — reset
        setSortKey(null);
        setSortDir('asc');
      }
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  const sortedData = useMemo(() => {
    if (!sortKey) return data;

    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];

      // Handle nulls — push to end
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      let cmp = 0;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        cmp = aVal - bVal;
      } else {
        cmp = String(aVal).localeCompare(String(bVal));
      }

      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  function formatCell(col: ColumnDef, value: unknown): string {
    if (col.format) return col.format(value);
    if (value == null) return '—';
    return String(value);
  }

  function sortIndicator(key: string): string {
    if (sortKey !== key) return '';
    return sortDir === 'asc' ? ' ▲' : ' ▼';
  }

  /* ── Empty state ── */

  if (data.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No results found
      </div>
    );
  }

  /* ── Table ── */

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap${
                  col.sortable ? ' cursor-pointer select-none hover:text-gray-900' : ''
                }`}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
              >
                {col.label}
                {col.sortable && (
                  <span className="ml-1 text-blue-600">{sortIndicator(col.key)}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, idx) => (
            <tr
              key={idx}
              className="border-b border-gray-100 even:bg-gray-50 hover:bg-blue-50 transition-colors"
            >
              {columns.map((col) => (
                <td key={col.key} className="px-4 py-3 whitespace-nowrap text-gray-900">
                  {formatCell(col, row[col.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
