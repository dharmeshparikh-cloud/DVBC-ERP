import js from '@eslint/js';
import globals from 'globals';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';

/**
 * NETRA ERP - ESLint Configuration
 * 
 * SALES MODULE GOVERNANCE:
 * All sales-related pages MUST use SalesDataTable component instead of manual tables.
 * See /app/frontend/src/components/sales/SalesDataTable.jsx for the governed component.
 * 
 * Approved Sales Tables:
 * - LeadsTable.jsx
 * - MeetingsTable.jsx
 * - FollowUpsTable.jsx
 * - QuotationsTable.jsx
 * - AgreementsTable.jsx
 * - SOWTable.jsx
 * - ProformaInvoiceTable.jsx
 */

export default [
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.es2021,
        process: 'readonly',
      },
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      react: reactPlugin,
      'react-hooks': reactHooksPlugin,
    },
    rules: {
      // React rules
      'react/jsx-uses-react': 'off',
      'react/react-in-jsx-scope': 'off',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      
      // General rules
      'no-unused-vars': ['warn', { 
        varsIgnorePattern: '^_',
        argsIgnorePattern: '^_',
        ignoreRestSiblings: true 
      }],
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
  },
  {
    ignores: [
      'node_modules/**',
      'build/**',
      'public/**',
      '*.config.js',
      '*.config.mjs',
    ],
  },
];
