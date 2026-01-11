import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Apple-inspired color palette
        apple: {
          blue: '#007AFF',
          purple: '#5856D6',
          green: '#34C759',
          orange: '#FF9500',
          red: '#FF3B30',
          pink: '#FF2D55',
          yellow: '#FFCC00',
          teal: '#5AC8FA',
          indigo: '#5856D6',
        },
        // Light mode
        background: '#FFFFFF',
        surface: '#F5F5F7',
        'surface-elevated': '#FFFFFF',
        // Dark mode
        'dark-background': '#000000',
        'dark-surface': '#1C1C1E',
        'dark-surface-elevated': '#2C2C2E',
        // Text
        'text-primary': '#000000',
        'text-secondary': '#86868B',
        'text-tertiary': '#C7C7CC',
        'dark-text-primary': '#FFFFFF',
        'dark-text-secondary': '#98989D',
        'dark-text-tertiary': '#48484A',
      },
      fontFamily: {
        sans: [
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Display"',
          '"Segoe UI"',
          'Roboto',
          'Oxygen',
          'Ubuntu',
          'Cantarell',
          'sans-serif',
        ],
      },
      borderRadius: {
        'apple-sm': '8px',
        'apple-md': '12px',
        'apple-lg': '16px',
        'apple-xl': '20px',
      },
      boxShadow: {
        'apple-sm': '0 1px 3px rgba(0, 0, 0, 0.1)',
        'apple-md': '0 4px 12px rgba(0, 0, 0, 0.08)',
        'apple-lg': '0 8px 24px rgba(0, 0, 0, 0.12)',
        'apple-xl': '0 16px 48px rgba(0, 0, 0, 0.16)',
      },
      transitionDuration: {
        'apple': '300ms',
      },
      transitionTimingFunction: {
        'apple': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [],
  darkMode: 'class',
};

export default config;

