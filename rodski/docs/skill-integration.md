# Skill Integration Specification

## Overview

RodSki skills are reusable Python scripts that extend the keyword engine with custom automation capabilities.

## Skill Definition Structure

Skills are Python modules located in the `fun/` directory of a test module:

```
module_dir/
├── case/
├── model/
├── data/
├── fun/
│   ├── custom_login.py
│   └── data_processor.py
└── result/
```

## Writing Custom Skills

### Basic Skill Template

```python
"""Custom skill description"""

def execute(driver, params):
    """Main entry point for skill execution

    Args:
        driver: WebDriver instance
        params: Dict with 'model' and 'data' keys

    Returns:
        Any value to be stored in return variables
    """
    model = params.get('model', '')
    data = params.get('data', '')

    # Your custom logic here

    return result
```

### Skill Parameters

- `driver`: Browser driver instance (Playwright/Selenium)
- `params['model']`: Model reference from test step
- `params['data']`: Data value from test step

### Return Values

Skills can return values that are accessible via `#Return#` syntax in subsequent steps.

## Skill Usage in Test Cases

```xml
<test_step action="custom_login" model="LoginPage" data="admin_user"/>
<test_step action="data_processor" model="" data="#Return#"/>
```

## Best Practices

1. Keep skills focused on single responsibilities
2. Use descriptive function and parameter names
3. Handle errors gracefully with try/except
4. Return meaningful values for chaining operations
5. Document expected model/data formats

## Example: Custom Login Skill

```python
def execute(driver, params):
    """Custom login with 2FA support"""
    model = params.get('model', '')
    data = params.get('data', '')

    # Parse credentials
    username, password, token = data.split('|')

    # Perform login
    driver.fill(f"{model}.username", username)
    driver.fill(f"{model}.password", password)
    driver.fill(f"{model}.token", token)
    driver.click(f"{model}.submit")

    return {"logged_in": True, "user": username}
```
