'use client';

import { useMemo } from 'react';

interface PasswordStrengthProps {
  password: string;
}

interface StrengthResult {
  score: number;       // 0–4
  label: string;
  color: string;
  barColor: string;
  suggestions: string[];
}

function evaluateStrength(password: string): StrengthResult {
  if (!password) {
    return { score: 0, label: '', color: 'text-white/30', barColor: 'bg-white/10', suggestions: [] };
  }

  let score = 0;
  const suggestions: string[] = [];

  if (password.length >= 8)  score++; else suggestions.push('At least 8 characters');
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password)) score++; else suggestions.push('Add an uppercase letter');
  if (/[0-9]/.test(password)) score++; else suggestions.push('Add a number');
  if (/[^A-Za-z0-9]/.test(password)) score++; else suggestions.push('Add a special character (!@#...)');

  // Clamp to 4
  score = Math.min(score, 4);

  const levels = [
    { score: 0, label: '',           color: 'text-white/30',  barColor: 'bg-white/10' },
    { score: 1, label: 'Weak',       color: 'text-red-400',   barColor: 'bg-red-500' },
    { score: 2, label: 'Fair',       color: 'text-amber-400', barColor: 'bg-amber-500' },
    { score: 3, label: 'Good',       color: 'text-blue-400',  barColor: 'bg-blue-500' },
    { score: 4, label: 'Strong',     color: 'text-emerald-400', barColor: 'bg-emerald-500' },
  ];

  return { ...levels[score], suggestions };
}

export function PasswordStrength({ password }: PasswordStrengthProps) {
  const strength = useMemo(() => evaluateStrength(password), [password]);

  if (!password) return null;

  return (
    <div className="mt-2 space-y-2">
      {/* Segmented strength bars */}
      <div className="flex items-center gap-1.5">
        {[1, 2, 3, 4].map((level) => (
          <div
            key={level}
            className="h-1 flex-1 rounded-full transition-all duration-500"
            style={{
              background: level <= strength.score
                ? (strength.barColor.replace('bg-', '').includes('red') ? '#EF4444'
                  : strength.barColor.replace('bg-', '').includes('amber') ? '#F59E0B'
                  : strength.barColor.replace('bg-', '').includes('blue') ? '#3B82F6'
                  : '#10B981')
                : 'rgba(255,255,255,0.08)',
            }}
          />
        ))}
        <span className={`text-[10px] font-semibold font-inter ml-1 w-12 text-right ${strength.color}`}>
          {strength.label}
        </span>
      </div>

      {/* Suggestions */}
      {strength.suggestions.length > 0 && strength.score < 4 && (
        <ul className="space-y-0.5">
          {strength.suggestions.slice(0, 2).map((s) => (
            <li key={s} className="flex items-center gap-1.5 text-[10px] text-white/35 font-inter">
              <span className="w-1 h-1 rounded-full bg-white/25 shrink-0" />
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
