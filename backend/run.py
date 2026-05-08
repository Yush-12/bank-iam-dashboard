"""Phase 1 runtime entry point for the IAM Flask backend."""

# IMPORTANT RENDER FREE TIER NOTE:
# Render's free tier web services spin down after 15 minutes of inactivity.
# The first request after a cold start takes ~30 seconds (Render spinning up the instance).
# The frontend polls the /api/health endpoint on load to "wake up" this backend.

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
