# Error Handling Best Practices

Best practices for handling errors in RodSki test automation.

## Exception Hierarchy

RodSki uses a structured exception hierarchy:

- `RodskiException`: Base exception
  - `ElementNotFoundException`: Element not found
  - `TimeoutException`: Operation timeout
  - `ValidationException`: Validation failure
  - `DriverStoppedError`: Browser closed unexpectedly

## Retry Strategy

Configure retries in `config/default_config.yaml`:

```yaml
execution:
  max_retries: 3
  recovery_enabled: true
  recovery_max_attempts: 2
```

## Recovery Actions

Use recovery actions for common failures:

```xml
<test_step action="click" model="login_button" data=""
           recovery="refresh_page,wait_2s,retry"/>
```

## Conditional Execution

Skip steps based on conditions:

```xml
<test_step action="click" model="optional_button" data=""
           condition="${button_visible} == true"/>
```

## Error Context

Enable failure context capture:

```yaml
result:
  capture_failure_context: true
```

This captures:
- Page source
- Console logs
- Variable snapshot
- Screenshots

## Best Practices

1. Use specific exceptions for different error types
2. Enable AI diagnosis for complex failures
3. Implement recovery actions for transient errors
4. Capture context for debugging
5. Use conditions to handle optional elements
