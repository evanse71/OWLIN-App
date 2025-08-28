# TypeScript Guardrails

This document ensures TypeScript errors stay at **0** permanently.

## ✅ Verification Checklist

Run this after any changes:

```bash
# 1) TypeScript check (CI safety)
npx tsc --noEmit

# 2) Next.js build (catches runtime/SSR typing gaps)
npm run build

# 3) Lint (keeps imports + unused vars tidy)
npm run lint --silent || npm run lint -- --fix

# 4) Restart VS Code TS server if Problems panel flickers
# Cmd/Ctrl-Shift-P → "TypeScript: Restart TS server"
```

## 🔒 Guardrails to Keep It Green

### tsconfig.json
- ✅ `paths` must include: `@/*`, `@/components/*`, `@/types/*`
- ✅ `exclude` must include: `tests/**`, `__tests__/**`, `**/*.test.*`, `**/*.spec.*`
- ❌ **NEVER** include `"vite/client"` types (we use Next.js)

### Icons
- ✅ Use `AlertTriangle` (not `TriangleAlert`) from `lucide-react`
- ✅ Always check exact export name in lucide-react docs

### Type Imports
- ✅ Always import from `@/types/matching` (not `@types/matching`)
- ✅ Use path aliases: `@/components/*`, `@/lib/*`, `@/hooks/*`

### API Imports
- ✅ `reprocessInvoice` comes from `@/lib/api.real`
- ✅ Other API functions from `@/lib/api`

### Invoice Type
- ✅ Must include `validation_flags?: string[]`

## 🚨 Common Error Fixes

### "Cannot find module"
```bash
# Convert relative imports to path aliases
import Component from '../../../components/Component'  # ❌
import Component from '@/components/Component'        # ✅
```

### Icon not found
```bash
# Check exact export name in lucide-react
import { TriangleAlert } from 'lucide-react'  # ❌
import { AlertTriangle } from 'lucide-react'  # ✅
```

### Tests showing in Problems panel
```json
// Confirm tsconfig.json exclude has:
"exclude": [
  "node_modules", "dist", "build", "src/**",
  "**/*.test.*", "**/*.spec.*",
  "tests/**", "__tests__/**"
]
```

### Ghost errors
```bash
# Restart TS server + clear caches
rm -rf .next/ node_modules/.cache
# Then restart VS Code TS server
```

## 🤖 Automated Protection

### Pre-commit Hooks
- `lint-staged` runs on staged files
- `tsc --noEmit` blocks commits with TS errors
- `eslint --fix` auto-fixes formatting

### CI Pipeline
- GitHub Actions runs on every push/PR
- Fails if TypeScript errors detected
- Fails if build fails
- Fails if lint fails

## 📝 Development Workflow

1. **Before committing**: Run verification checklist
2. **If errors found**: Fix using guardrails above
3. **Pre-commit hook**: Automatically catches issues
4. **CI**: Final safety net for PRs

## 🎯 Success Metrics

- ✅ TypeScript compilation: 0 errors
- ✅ Next.js build: passes
- ✅ ESLint: 0 warnings/errors
- ✅ All imports resolve correctly
- ✅ Path aliases working

**Keep this green! 🚀** 