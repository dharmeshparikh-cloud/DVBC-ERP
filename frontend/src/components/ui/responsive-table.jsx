import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';

/**
 * ResponsiveTable - Shows table on desktop, card list on mobile
 * Props:
 * - columns: [{ key, label, render?, className?, hideOnMobile? }]
 * - data: array of row objects
 * - onRowClick: (row) => void
 * - mobileCard: (row, index) => ReactNode (custom mobile card renderer)
 * - emptyMessage: string
 * - emptyIcon: ReactNode
 * - loading: boolean
 */
const ResponsiveTable = ({ columns = [], data = [], onRowClick, mobileCard, emptyMessage = 'No data found', emptyIcon, loading }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <div className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Loading...</div>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className={`flex flex-col items-center justify-center h-40 rounded-sm border ${isDark ? 'border-[#2A2A2E] bg-[#1A1A1C]' : 'border-zinc-200 bg-white'}`}>
        {emptyIcon && <div className="mb-3 text-zinc-300">{emptyIcon}</div>}
        <p className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <>
      {/* Desktop Table */}
      <div className="hidden md:block overflow-x-auto">
        <table className={`w-full text-sm border-collapse ${isDark ? 'text-zinc-200' : 'text-zinc-700'}`}>
          <thead>
            <tr className={isDark ? 'bg-[#1A1A1C] border-b border-[#2A2A2E]' : 'bg-zinc-50 border-b border-zinc-200'}>
              {columns.map(col => (
                <th key={col.key} className={`text-left px-4 py-3 text-xs uppercase tracking-wide font-medium ${isDark ? 'text-zinc-400' : 'text-zinc-500'} ${col.className || ''}`}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr
                key={row.id || i}
                onClick={() => onRowClick?.(row)}
                className={`border-b transition-colors ${onRowClick ? 'cursor-pointer' : ''} ${
                  isDark
                    ? 'border-[#2A2A2E] hover:bg-[#1A1A1C]'
                    : 'border-zinc-100 hover:bg-zinc-50'
                }`}
              >
                {columns.map(col => (
                  <td key={col.key} className={`px-4 py-3 ${col.className || ''}`}>
                    {col.render ? col.render(row, i) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card List */}
      <div className="md:hidden space-y-2">
        {data.map((row, i) => (
          <div
            key={row.id || i}
            onClick={() => onRowClick?.(row)}
            className={`p-3 rounded-sm border transition-colors ${onRowClick ? 'cursor-pointer active:scale-[0.99]' : ''} ${
              isDark
                ? 'bg-[#1A1A1C] border-[#2A2A2E] active:bg-[#222224]'
                : 'bg-white border-zinc-200 active:bg-zinc-50'
            }`}
          >
            {mobileCard ? mobileCard(row, i) : (
              <div className="space-y-1.5">
                {columns.filter(c => !c.hideOnMobile).map(col => (
                  <div key={col.key} className="flex items-center justify-between text-sm">
                    <span className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>{col.label}</span>
                    <span className={isDark ? 'text-zinc-200' : 'text-zinc-700'}>
                      {col.render ? col.render(row, i) : row[col.key]}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
};

export default ResponsiveTable;
