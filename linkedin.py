from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, jsonify
import requests
import json
import re
from datetime import datetime
import os
from dotenv import load_dotenv


app = Flask(__name__)
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN")
CHAR_LIMIT = int(os.getenv("CHAR_LIMIT"))
GEMINI_URL = os.getenv("GEMINI_URL")

def generate_content():
    headers = {
        'Content-Type': 'application/json'
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "ReactJS coding tip or joke, limited to 280 characters. Keep it concise, fun, and relevant to ReactJS concepts. Include emojis if appropriate."
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Parse content
        return data['candidates'][0]['content']['parts'][0]['text']

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None


def sanitize_content(content):
    content = re.sub(r'\s+', ' ', content).strip().replace("\n", " ")
    return content


def truncate_content(content):
    if len(content) > CHAR_LIMIT:
        content = content[:CHAR_LIMIT - 3] + "..."
    return content

POSTS_DB = 'post_history.json'

def save_post_metadata(content, post_urn):
    post_data = {
        "urn": post_urn,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }

    if os.path.exists(POSTS_DB):
        with open(POSTS_DB) as f:
            posts = json.load(f)
    else:
        posts = []

    posts.append(post_data)
    with open(POSTS_DB, 'w') as f:
        json.dump(posts, f, indent=2)


def post_to_linkedin(content):
    headers = {
        'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
    }

    payload = {
        "author": LINKEDIN_PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    try:
        response = requests.post(
            'https://api.linkedin.com/v2/ugcPosts',
            headers=headers,
            json=payload
        )

        if response.status_code == 201:
            post_urn = response.json().get('id')
            save_post_metadata(content, post_urn)
            return True, post_urn
        return False, response.text
    except Exception as e:
        return False, str(e)
    
def schedule_posting():
    content = generate_content()
    if content:
        content = truncate_content(sanitize_content(content))
        success, result = post_to_linkedin(content)
        if success:
            print(f"[{datetime.now()}] ✅ Auto-posted to LinkedIn")
        else:
            print(f"[{datetime.now()}] ❌ Failed to auto-post: {result}")

def get_post_engagement(post_urn):
    social_action_url = f"https://api.linkedin.com/v2/socialActions/{post_urn}"
    headers = {
        'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    clean_urn = post_urn.replace('urn:li:share:', '').replace('urn:li:ugcPost:', '')
    endpoints_to_try = [
        f"https://api.linkedin.com/v2/shares/{clean_urn}",
        f"https://api.linkedin.com/v2/ugcPosts/{clean_urn}",
        f"https://api.linkedin.com/v2/socialMetadata/{clean_urn}"
    ]
    for endpoint in endpoints_to_try:
     try:
        response = requests.get(endpoint, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully retrieved engagement data from: {endpoint}")
            return parse_engagement_data(data)
        elif response.status_code == 403:
            print(f"❌ 403 Forbidden for endpoint: {endpoint}")
            print(f"Response: {response.text}")
            continue
        else:
            print(f"⚠️ Status {response.status_code} for endpoint: {endpoint}")
            continue
            
     except Exception as e:
        print(f"❌ Error with endpoint {endpoint}: {e}")
        continue

    print("❌ All endpoints failed. Check your LinkedIn app permissions.")
    return None

def parse_engagement_data(data):
    """
    Parse engagement data from LinkedIn API response
    Handle different response formats
    """
    engagement = {
        'likes': 0,
        'comments': 0,
        'shares': 0,
        'views': 0
    }
    
    # Handle different response formats
    if 'socialDetail' in data:
        social_detail = data['socialDetail']
        engagement['likes'] = social_detail.get('totalSocialActivityCounts', {}).get('numLikes', 0)
        engagement['comments'] = social_detail.get('totalSocialActivityCounts', {}).get('numComments', 0)
        engagement['shares'] = social_detail.get('totalSocialActivityCounts', {}).get('numShares', 0)
    
    elif 'likesSummary' in data:
        engagement['likes'] = data.get('likesSummary', {}).get('totalLikes', 0)
        engagement['comments'] = data.get('commentsSummary', {}).get('totalFirstLevelComments', 0)
        engagement['shares'] = data.get('shareStatistics', {}).get('shareCount', 0)
    
    return engagement


@app.route("/generate", methods=["GET"])
def api_generate():
    content = generate_content()
    if content:
        return jsonify({"content": sanitize_content(content)})
    return jsonify({"error": "Content generation failed"}), 500


@app.route("/post", methods=["POST"])
def api_post():
    data = request.get_json()
    content = data.get("content")
    if not content:
        return jsonify({"error": "Missing 'content' in request"}), 400

    content = truncate_content(sanitize_content(content))
    success, result = post_to_linkedin(content)

    if success:
        return jsonify({"message": "Successfully posted to LinkedIn", "content": content})
    else:
        return jsonify({"error": "Failed to post", "details": result}), 500


@app.route("/generate-and-post", methods=["POST"])
def api_generate_and_post():
    content = generate_content()
    if not content:
        return jsonify({"error": "Failed to generate content"}), 500

    content = truncate_content(sanitize_content(content))
    success, result = post_to_linkedin(content)

    if success:
        return jsonify({"message": "Content posted", "content": content})
    else:
        return jsonify({"error": "Failed to post", "details": result}), 500
    
@app.route("/analytics", methods=["GET"])
def analytics():
    if not os.path.exists(POSTS_DB):
        return jsonify({"error": "No posts found"}), 404

    with open(POSTS_DB) as f:
        posts = json.load(f)

    results = []
    failed_posts = []
    
    for post in posts:
        engagement = get_post_engagement(post['urn'])
        if engagement:
            post_result = {
                "content": post['content'],
                "timestamp": post['timestamp'],
                "urn": post['urn'],
                "likes": engagement.get('likes', 0),
                "comments": engagement.get('comments', 0),
                "shares": engagement.get('shares', 0),
                "views": engagement.get('views', 0)
            }
            results.append(post_result)
        else:
            failed_posts.append({
                "urn": post['urn'],
                "content": post['content'][:50] + "...",
                "timestamp": post['timestamp']
            })

    response_data = {
        "successful_posts": results,
        "failed_posts": failed_posts,
        "total_posts": len(posts),
        "successful_count": len(results),
        "failed_count": len(failed_posts)
    }
    
    return jsonify(response_data)


if __name__ == "__main__":
    print(f"API Server starting at {datetime.now()}")
    # Start scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(schedule_posting, 'interval', minutes=1)  # 🔁 every 1 minute
    scheduler.start()

    app.run(debug=True, port=5000)
