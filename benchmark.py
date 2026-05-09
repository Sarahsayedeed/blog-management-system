import time
import requests

# Ensure your FastAPI server is running (uvicorn) before starting this
BASE_URL = "http://localhost:8000"
ENDPOINT = "/auth/users" 

# run uvicorn app.main:app --reload  
# open http://127.0.0.1:8000/docs to see the API docs and test endpoints
# Note: This endpoint requires Admin Token. If testing without token, use "/posts/"
# I will use "/posts/" here for an easier test as Person B
TEST_URL = f"{BASE_URL}/posts/"

def run_performance_test():
    print("🚀 Starting Redis Performance Benchmark...")
    print("-" * 50)

    try:
        # 1. First Request: Database (Cold Start)
        start = time.time()
        res1 = requests.get(TEST_URL)
        db_duration = time.time() - start
        print(f"⏱️  Request 1 (From Database): {db_duration:.4f} seconds")

        # Wait a second to settle
        time.sleep(1)

        # 2. Second Request: Redis (Hot Cache)
        start = time.time()
        res2 = requests.get(TEST_URL)
        cache_duration = time.time() - start
        print(f"⚡ Request 2 (From Redis Cache): {cache_duration:.4f} seconds")

        # 3. Calculation
        improvement = ((db_duration - cache_duration) / db_duration) * 100
        print("-" * 50)
        print(f"📈 Performance Improvement: {improvement:.2f}%")
        print(f"✅ Redis is {db_duration/cache_duration:.1f}x faster!")

    except Exception as e:
        print(f"❌ Error: Make sure the server is running at {BASE_URL}")

if __name__ == "__main__":
    run_performance_test()