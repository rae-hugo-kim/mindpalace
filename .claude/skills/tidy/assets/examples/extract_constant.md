# Extract Constant Example

**Level**: 2 (Low Risk)

## Before

```javascript
function calculateTimeout(retryCount) {
  return Math.min(retryCount * 1000, 30000);
}

function isSessionExpired(lastActivity) {
  return Date.now() - lastActivity > 1800000;
}

function formatBytes(bytes) {
  if (bytes > 1073741824) {
    return (bytes / 1073741824).toFixed(2) + ' GB';
  }
  return bytes + ' bytes';
}
```

**Problems**:
- Magic numbers: 1000, 30000, 1800000, 1073741824
- Intent unclear without context
- Easy to use wrong value

## After

```javascript
const RETRY_DELAY_MS = 1000;
const MAX_TIMEOUT_MS = 30000;
const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const BYTES_PER_GB = 1024 ** 3;

function calculateTimeout(retryCount) {
  return Math.min(retryCount * RETRY_DELAY_MS, MAX_TIMEOUT_MS);
}

function isSessionExpired(lastActivity) {
  return Date.now() - lastActivity > SESSION_TIMEOUT_MS;
}

function formatBytes(bytes) {
  if (bytes > BYTES_PER_GB) {
    return (bytes / BYTES_PER_GB).toFixed(2) + ' GB';
  }
  return bytes + ' bytes';
}
```

**Benefits**:
- Self-documenting names
- Single source of truth
- Easy to find and update

## When to Apply

- Numbers that have meaning (thresholds, limits, conversions)
- Strings used as identifiers or keys
- Values used in multiple places

## When NOT to Apply

- Obvious numbers (0, 1, -1 in loops)
- One-time literals that are self-explanatory
- Values that vary by context
