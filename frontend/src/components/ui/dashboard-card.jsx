import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { Card, CardContent } from './card';

/**
 * DashboardCard - Standardized KPI card for dashboards
 * Props:
 * - icon: LucideIcon
 * - label: string
 * - value: string|number
 * - trend: string (optional, e.g., "+5%")
 * - trendUp: boolean
 * - color: 'emerald'|'red'|'blue'|'amber'|'violet'|'default'
 * - onClick: () => void
 */
const COLOR_MAP = {
  emerald: { light: 'bg-emerald-50 text-emerald-600', dark: 'bg-emerald-950/30 text-emerald-400', icon: 'bg-emerald-100 dark:bg-emerald-900/40' },
  red: { light: 'bg-red-50 text-red-600', dark: 'bg-red-950/30 text-red-400', icon: 'bg-red-100 dark:bg-red-900/40' },
  blue: { light: 'bg-blue-50 text-blue-600', dark: 'bg-blue-950/30 text-blue-400', icon: 'bg-blue-100 dark:bg-blue-900/40' },
  amber: { light: 'bg-amber-50 text-amber-600', dark: 'bg-amber-950/30 text-amber-400', icon: 'bg-amber-100 dark:bg-amber-900/40' },
  violet: { light: 'bg-violet-50 text-violet-600', dark: 'bg-violet-950/30 text-violet-400', icon: 'bg-violet-100 dark:bg-violet-900/40' },
  default: { light: 'bg-zinc-50 text-zinc-600', dark: 'bg-zinc-800 text-zinc-300', icon: 'bg-zinc-100 dark:bg-zinc-800' },
};

const DashboardCard = ({ icon: Icon, label, value, trend, trendUp, color = 'default', onClick }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const c = COLOR_MAP[color] || COLOR_MAP.default;

  return (
    <Card
      className={`shadow-none rounded-sm border transition-colors cursor-default ${
        isDark ? 'bg-[#1A1A1C] border-[#2A2A2E]' : 'bg-white border-zinc-200'
      } ${onClick ? 'cursor-pointer hover:shadow-sm' : ''}`}
      onClick={onClick}
    >
      <CardContent className="p-3 sm:p-4 flex items-center gap-3">
        {Icon && (
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${c.icon}`}>
            <Icon className={`w-4 h-4 ${isDark ? c.dark.split(' ')[1] : c.light.split(' ')[1]}`} />
          </div>
        )}
        <div className="min-w-0">
          <div className={`text-[10px] uppercase tracking-wide truncate ${isDark ? 'text-[#B0B0B0]' : 'text-zinc-500'}`}>{label}</div>
          <div className="flex items-baseline gap-1.5">
            <span className={`text-lg font-semibold tabular-nums ${isDark ? 'text-white' : 'text-zinc-900'}`}>{value ?? 0}</span>
            {trend && (
              <span className={`text-xs font-medium ${trendUp ? 'text-emerald-500' : 'text-red-500'}`}>{trend}</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default DashboardCard;
