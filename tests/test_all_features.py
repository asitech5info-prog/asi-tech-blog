import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

import app

def run_tests():
    print("=== STARTING FULL COMPREHENSIVE TEST SUITE ===")
    
    with app.app.app_context():
        app.init_db()
        db = app.get_db()
        
        # 1. Verify Database & Articles
        count = db.execute("SELECT COUNT(*) FROM blogs").fetchone()[0]
        print(f"✓ Total Blogs in Database: {count}")
        assert count >= 12, "Should have at least 12 blogs seeded"
        
        client = app.app.test_client()

        # 2. Verify Public Navbar does NOT contain "Admin Suite" or "nav-asi-bot-btn"
        resp_home = client.get('/')
        assert resp_home.status_code == 200
        html_home = resp_home.data.decode('utf-8')
        
        # Check navLinks does not have Admin Suite
        assert '<nav class="nav-links" id="navLinks">' in html_home
        nav_links_block = html_home.split('<nav class="nav-links" id="navLinks">')[1].split('</nav>')[0]
        assert "Admin Suite" not in nav_links_block, "Admin Suite link MUST NOT appear in public navigation links!"
        
        # Check header nav-right does NOT have nav-asi-bot-btn (removed as requested)
        assert "nav-asi-bot-btn" not in html_home, "nav-asi-bot-btn MUST NOT be in header"
        print("✓ Public Header Verified: Header is clean, well-spaced, and 'Ask ASI' button removed from top header!")

        # 3. Verify Privacy Policy Banner & Dialog in HTML
        assert "privacy-consent-bar" in html_home
        assert "privacy-modal-overlay" in html_home
        print("✓ Privacy Policy Consent Popup & Dialog Verified!")

        # 4. Verify Professional ASI AI Chatbot Widget in HTML
        assert "asi-ai-launcher" in html_home
        assert "asi-chat-window" in html_home
        assert "asiExpandChatBtn" in html_home
        assert "asiClearChatBtn" in html_home
        assert "asiCloseChatBtn" in html_home
        assert "ASI Intelligence" in html_home
        print("✓ Professional ASI AI Chatbot (Gemini Engine) Suite Verified in HTML!")

        # 5. Test ASI AI Chatbot API endpoints
        chat_resp = client.post('/api/ai/chat', json={'prompt': 'Who are you?'})
        assert chat_resp.status_code == 200
        chat_data = chat_resp.get_json()
        assert chat_data['status'] == 'success'
        assert chat_data['bot_name'] == 'ASI'
        assert 'ASI' in chat_data['response']
        print(f"✓ AI Chatbot Response (/api/ai/chat): \"{chat_data['response'][:60]}...\"")

        chat_resp2 = client.post('/api/ai/chat', json={'prompt': 'Explain DeepSeek-R1'})
        assert chat_resp2.status_code == 200
        chat_data2 = chat_resp2.get_json()
        assert 'DeepSeek' in chat_data2['response'] or 'Reasoning' in chat_data2['response']
        print(f"✓ AI Chatbot Knowledge (/api/ai/chat): \"{chat_data2['response'][:60]}...\"")

        chat_resp3 = client.post('/api/ai/chat', json={'prompt': 'Compare Rust vs Zig vs Mojo'})
        assert chat_resp3.status_code == 200
        chat_data3 = chat_resp3.get_json()
        assert 'Rust' in chat_data3['response']
        print(f"✓ AI Chatbot Systems Knowledge: \"{chat_data3['response'][:60]}...\"")

        # 6. Test User Registration (/api/auth/register)
        test_email = f"test_{os.getpid()}@gmail.com"
        reg_resp = client.post('/api/auth/register', json={
            'name': 'Sarah Connor',
            'email': test_email,
            'password': 'securepassword123'
        })
        assert reg_resp.status_code == 200
        reg_data = reg_resp.get_json()
        assert reg_data['status'] == 'success'
        assert reg_data['user']['name'] == 'Sarah Connor'
        print(f"✓ User Registration API Verified: {test_email}")

        # 7. Test User Login (/api/auth/login)
        login_resp = client.post('/api/auth/login', json={
            'email': test_email,
            'password': 'securepassword123'
        })
        assert login_resp.status_code == 200
        login_data = login_resp.get_json()
        assert login_data['status'] == 'success'
        print(f"✓ User Email Login Verified: {login_data['user']['name']}")

        # 8. Test Google / Gmail One-Click Sign In (/api/auth/google)
        google_email = f"google_dev_{os.getpid()}@gmail.com"
        google_resp = client.post('/api/auth/google', json={
            'name': 'Alex Google Dev',
            'email': google_email
        })
        assert google_resp.status_code == 200
        google_data = google_resp.get_json()
        assert google_data['status'] == 'success'
        assert google_data['user']['email'] == google_email
        print(f"✓ Google / Gmail OAuth Sign-In Verified: {google_email}")

        # 9. Test Blog Detail & Search
        resp_blog = client.get('/blog/deepseek-r1-claude-3-7-reasoning-llms-frontier')
        assert resp_blog.status_code == 200
        print("✓ Blog Detail Route: 200 OK")

        resp_search = client.get('/api/search?q=quantum')
        assert resp_search.status_code == 200
        print("✓ Search API: 200 OK")

    print("\n🎉 ALL TESTS PASSED WITH 100% SUCCESS! 🎉")

if __name__ == '__main__':
    run_tests()
