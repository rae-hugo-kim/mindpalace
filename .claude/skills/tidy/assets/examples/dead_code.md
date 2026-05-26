# Dead Code Removal Example

**Level**: 1 (Safe)

## Before

```javascript
import { useState, useEffect, useCallback, useMemo } from 'react';
import lodash from 'lodash';
import moment from 'moment';

const LEGACY_API_URL = 'https://old-api.example.com';
const DEBUG_MODE = false;

function UserProfile({ userId }) {
  const [user, setUser] = useState(null);

  // Old implementation - kept for reference
  // function fetchUserLegacy() {
  //   return fetch(LEGACY_API_URL + '/users/' + userId);
  // }

  useEffect(() => {
    fetchUser(userId).then(setUser);
  }, [userId]);

  function unusedHelper() {
    console.log('This is never called');
  }

  return <div>{user?.name}</div>;
}
```

**Dead code identified**:
- `useCallback`, `useMemo` — imported but unused
- `lodash`, `moment` — imported but unused
- `LEGACY_API_URL`, `DEBUG_MODE` — declared but unused
- Commented code block — should be in git history, not comments
- `unusedHelper` — declared but never called

## After

```javascript
import { useState, useEffect } from 'react';

function UserProfile({ userId }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetchUser(userId).then(setUser);
  }, [userId]);

  return <div>{user?.name}</div>;
}
```

**Benefits**:
- Cleaner imports (smaller bundle)
- Less cognitive load
- No misleading "reference" code

## When to Apply

- Unused imports (linter usually catches)
- Unused variables and functions
- Commented-out code blocks
- Unreachable code after return/throw

## When NOT to Apply

- Code used conditionally (feature flags)
- Exports used by other modules
- Test utilities that appear unused locally

## Detection Tools

```bash
# JavaScript/TypeScript
eslint --rule 'no-unused-vars: error'
npx ts-prune

# Python
pylint --disable=all --enable=unused-import,unused-variable

# Go
go vet ./...
```
