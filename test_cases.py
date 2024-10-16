import requests

# Base URL for your FastAPI app
BASE_URL = "http://localhost:8000"

# User credentials (replace with actual user credentials)
login_data = {
    "email": "ali@gmail.com",
    "password": "123"
}

# Log in to get the token
def login():
    login_url = f"{BASE_URL}/accounts/login"
    response = requests.post(login_url, json=login_data)
    if response.status_code == 200:
        token = response.json().get("access_token")
        return token
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None

# Create a new user preference
def create_user_preference(token):
    preference_url = f"{BASE_URL}/users/preferences"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    preference_data = {
        "difficulty_level": "intermediate",
        "quiz_format": "mcqs",
        "topics": [1, 2]  # Replace with topic IDs from your `topics` table
    }

    response = requests.post(preference_url, json=preference_data, headers=headers)
    if response.status_code == 200:
        print("Preference created successfully:", response.json())
    else:
        print(f"Failed to create preference: {response.status_code} - {response.text}")

# Get the user preferences
def get_user_preferences(token):
    get_url = f"{BASE_URL}/users/preferences"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(get_url, headers=headers)
    if response.status_code == 200:
        print("User preferences:", response.json())
    else:
        print(f"Failed to get preferences: {response.status_code} - {response.text}")

# Create a new topic
def create_topic(token, topic_name):
    url = f"{BASE_URL}/users/topics"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    topic_data = {
        "name": topic_name
    }

    response = requests.post(url, json=topic_data, headers=headers)
    
    if response.status_code == 200:
        print("Topic created:", response.json())
    elif response.status_code == 400:
        print("Topic already exists:", response.json())
    else:
        print("Failed to create topic:", response.json())

# Test case: insert multiple topics
def test_create_topics(token):
    if token:
        # List of topics to be inserted
        topics = ["AI", "Machine Learning", "Data Science", "FastAPI","Computer Science","DataBases"]

        for topic in topics:
            create_topic(token, topic)
    else:
        print('token not found')        

def update_user_preference(token):
    updated_preference_data = {
        "difficulty_level": "medium",
        "quiz_format": "mcqs",
        "topics": [2, 4, 5,6 ]  # Updated topic IDs
    }
    
    response = requests.put(
        f"{BASE_URL}/users/preferences",
        json=updated_preference_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(response)

if __name__ == "__main__":
    # Step 1: Login to get the token
    token = login()
    print(token)
    if token:
        # step 1 add topics 
        test_create_topics(token)
        # Step 2: Test creating a user preference
        create_user_preference(token)

        # Step 3: Test getting the user preferences
        get_user_preferences(token)

        # step 4 
        update_user_preference(token)
