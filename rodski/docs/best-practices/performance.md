# Performance Best Practices

Optimize RodSki test execution for speed and stability.

## Browser Recycling

Prevent memory leaks with automatic browser recycling:

```yaml
execution:
  browser_restart_interval: 50
```

The browser restarts every 50 steps, maintaining the current URL.

## Memory Monitoring

RodSki monitors memory usage and triggers garbage collection:

```python
# Automatic memory check every 10 steps
# GC triggered when memory increases by 100MB
```

## Element Locators

Use efficient locator strategies:

**Good:**
```xml
<element id="login_btn" type="id" value="loginButton"/>
<element id="username" type="name" value="username"/>
```

**Avoid:**
```xml
<element id="slow" type="xpath" value="//div[@class='container']//span[contains(text(),'Login')]"/>
```

## Wait Times

Configure appropriate wait times:

```yaml
# Global wait time in globalvalue.xml
<DefaultValue>
  <WaitTime>500</WaitTime>
</DefaultValue>

# Case-level wait time
<testcase step_wait="300">
```

## Parallel Execution

Run independent test cases in parallel using multiple processes.

## Resource Cleanup

Always use post_process for cleanup:

```xml
<post_process>
  <test_step action="close" model="" data=""/>
</post_process>
```

## Best Practices

1. Set browser_restart_interval based on test complexity
2. Use ID/name locators over XPath when possible
3. Minimize wait times while maintaining stability
4. Clean up resources in post_process
5. Monitor memory usage in long-running suites
