from app import create_app
app = create_app()
with app.test_client() as client:
    print("Testing /health...")
    response = client.get('/health')
    print(f"Status: {response.status_code}")
    print(f"Body: {response.get_data(as_text=True)}")

    print("\nTesting /api/detections (stub)...")
    response = client.get('/api/detections')
    print(f"Status: {response.status_code}")
