'use client';

import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: LucideIcon;
  color?: 'violet' | 'cyan' | 'emerald' | 'amber' | 'red';
  trend?: { value: number; label: string };
  delay?: number;
}

const colorMap = {
  violet: {
    bg: 'rgba(124,58,237,0.08)',
    border: 'rgba(124,58,237,0.2)',
    icon_bg: 'rgba(124,58,237,0.15)',
    icon_text: '#9D6EFF',
    value_text: '#C4B5FD',
    glow: '0 0 24px rgba(124,58,237,0.15)',
  },
  cyan: {
    bg: 'rgba(6,182,212,0.06)',
    border: 'rgba(6,182,212,0.2)',
    icon_bg: 'rgba(6,182,212,0.12)',
    icon_text: '#22D3EE',
    value_text: '#A5F3FC',
    glow: '0 0 24px rgba(6,182,212,0.12)',
  },
  emerald: {
    bg: 'rgba(16,185,129,0.06)',
    border: 'rgba(16,185,129,0.2)',
    icon_bg: 'rgba(16,185,129,0.12)',
    icon_text: '#34D399',
    value_text: '#A7F3D0',
    glow: '0 0 24px rgba(16,185,129,0.12)',
  },
  amber: {
    bg: 'rgba(245,158,11,0.06)',
    border: 'rgba(245,158,11,0.2)',
    icon_bg: 'rgba(245,158,11,0.12)',
    icon_text: '#FCD34D',
    value_text: '#FDE68A',
    glow: '0 0 24px rgba(245,158,11,0.1)',
  },
  red: {
    bg: 'rgba(239,68,68,0.06)',
    border: 'rgba(239,68,68,0.2)',
    icon_bg: 'rgba(239,68,68,0.12)',
    icon_text: '#F87171',
    value_text: '#FCA5A5',
    glow: '0 0 24px rgba(239,68,68,0.1)',
  },
};

export function StatsCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'violet',
  trend,
  delay = 0,
}: StatsCardProps) {
  const c = colorMap[color];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="relative rounded-2xl p-5 cursor-default"
      style={{
        background: c.bg,
        border: `1px solid ${c.border}`,
        backdropFilter: 'blur(20px)',
        boxShadow: c.glow,
      }}
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-6 right-6 h-px rounded-full opacity-60"
        style={{ background: `linear-gradient(90deg, transparent, ${c.icon_text}, transparent)` }}
      />

      <div className="flex items-start justify-between mb-3">
        {/* Icon */}
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: c.icon_bg }}
        >
          <Icon className="w-5 h-5" style={{ color: c.icon_text }} />
        </div>

        {/* Trend badge */}
        {trend && (
          <div
            className={`flex items-center gap-1 text-xs font-medium font-inter px-2 py-0.5 rounded-full ${
              trend.value >= 0
                ? 'text-emerald-400 bg-emerald-500/10'
                : 'text-red-400 bg-red-500/10'
            }`}
          >
            {trend.value >= 0 ? '↑' : '↓'} {Math.abs(trend.value)}%
          </div>
        )}
      </div>

      {/* Value */}
      <div className="mb-1">
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.2 }}
          className="text-3xl font-bold font-outfit"
          style={{ color: c.value_text }}
        >
          {value}
        </motion.span>
      </div>

      {/* Title */}
      <p className="text-sm font-medium text-white/70 font-inter">{title}</p>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs text-white/35 font-inter mt-0.5">{subtitle}</p>
      )}

      {/* Trend label */}
      {trend && (
        <p className="text-xs text-white/30 font-inter mt-1">{trend.label}</p>
      )}
    </motion.div>
  );
}
