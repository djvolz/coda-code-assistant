# Debug Examples

This directory contains debug and example scripts organized by component type.

## Structure

### web/
Streamlit web UI debug scripts:

- `streamlit_navigation_test.py` - Minimal app to test Streamlit radio navigation functionality
- `streamlit_components_demo.py` - Demo app showcasing various Streamlit components (charts, forms, etc.)

## Usage

Run these scripts directly with Streamlit:

```bash
# Test navigation functionality
streamlit run examples/debug/web/streamlit_navigation_test.py

# Demo all component types
streamlit run examples/debug/web/streamlit_components_demo.py
```

These scripts are useful for:
- Debugging Streamlit-specific issues
- Testing new features in isolation
- Demonstrating component capabilities
- Verifying framework behavior