# Guard Clause Example

**Level**: 2 (Low Risk)

## Before

```javascript
function processUser(user) {
  if (user) {
    if (user.isActive) {
      if (user.hasPermission) {
        return doWork(user);
      }
    }
  }
  return null;
}
```

**Problems**:
- 3 levels of nesting
- Hard to follow the "happy path"
- Easy to miss edge cases

## After

```javascript
function processUser(user) {
  if (!user) return null;
  if (!user.isActive) return null;
  if (!user.hasPermission) return null;

  return doWork(user);
}
```

**Benefits**:
- Flat structure (0 nesting)
- Early exits handle edge cases
- Happy path is clear at the end

## When to Apply

- Nested conditionals ≥ 2 levels deep
- Multiple null/undefined checks
- Permission/validation chains

## When NOT to Apply

- Single simple condition
- When early return would obscure intent
- In expressions (can't early return)
