
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from agents.agent_3_strategist.notifications import generate_email_html

def test_template():
    print("Testing with empty lists...")
    try:
        html = generate_email_html("Test User", [], [], [])
        print("✅ Success: Template generated for empty lists.")
    except Exception as e:
        print(f"❌ Failed for empty lists: {e}")

    print("\nTesting with populated lists...")
    try:
        jobs = [{'title': 'Dev', 'company': 'Corp', 'score': 0.9}]
        hacks = [{'title': 'Hack', 'company': 'Org'}]
        news = [{'title': 'Article'}]
        html = generate_email_html("Test User", jobs, hacks, news)
        print("✅ Success: Template generated for populated lists.")
    except Exception as e:
        print(f"❌ Failed for populated lists: {e}")

if __name__ == "__main__":
    test_template()
