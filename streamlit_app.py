"""
streamlit_app.py — Entrypoint for Streamlit Community Cloud
Executes dashboard.py directly.
"""
import runpy

if __name__ == "__main__":
    runpy.run_module("dashboard", run_name="__main__")
else:
    # When imported by Streamlit runner
    import dashboard
