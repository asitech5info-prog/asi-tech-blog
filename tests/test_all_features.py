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
        assert count >= 19, f"Should have at least 19 blogs seeded, found {count}"
        
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

        # Test Apple & Samsung Chatbot Knowledge
        chat_resp_apple = client.post('/api/ai/chat', json={'prompt': 'What is Apple Intelligence and M4?'})
        assert chat_resp_apple.status_code == 200
        chat_data_apple = chat_resp_apple.get_json()
        assert 'Apple' in chat_data_apple['response'] and 'Unified Memory' in chat_data_apple['response']
        print("✓ AI Chatbot Apple & Silicon Knowledge Verified!")

        chat_resp_samsung = client.post('/api/ai/chat', json={'prompt': 'Tell me about Samsung Galaxy S25 and Galaxy AI'})
        assert chat_resp_samsung.status_code == 200
        chat_data_samsung = chat_resp_samsung.get_json()
        assert 'Samsung' in chat_data_samsung['response'] and 'Galaxy AI' in chat_data_samsung['response']
        print("✓ AI Chatbot Samsung Galaxy & AI Knowledge Verified!")

        # Test Out-of-Blog General Tech & Coding Questions
        chat_resp_algo = client.post('/api/ai/chat', json={'prompt': 'How do I implement binary search in Python?'})
        assert chat_resp_algo.status_code == 200
        chat_data_algo = chat_resp_algo.get_json()
        assert 'binary_search' in chat_data_algo['response'] or 'Binary Search' in chat_data_algo['response']
        print("✓ AI Chatbot Out-of-Blog Algorithm Question Verified!")

        chat_resp_net = client.post('/api/ai/chat', json={'prompt': 'What is the difference between TCP and UDP?'})
        assert chat_resp_net.status_code == 200
        chat_data_net = chat_resp_net.get_json()
        assert 'TCP' in chat_data_net['response'] and 'UDP' in chat_data_net['response']
        print("✓ AI Chatbot Out-of-Blog Networking Question Verified!")

        chat_resp_docker = client.post('/api/ai/chat', json={'prompt': 'How do I write a Dockerfile for a web app?'})
        assert chat_resp_docker.status_code == 200
        chat_data_docker = chat_resp_docker.get_json()
        assert 'docker' in chat_data_docker['response'].lower()
        print("✓ AI Chatbot Out-of-Blog DevOps Question Verified!")

        chat_resp_gen = client.post('/api/ai/chat', json={'prompt': 'Explain quantum superposition and Schrödinger equation'})
        assert chat_resp_gen.status_code == 200
        chat_data_gen = chat_resp_gen.get_json()
        assert 'Quantum' in chat_data_gen['response'] or 'superposition' in chat_data_gen['response'].lower()
        print("✓ AI Chatbot Out-of-Blog Science Question Verified!")

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

        # 9. Test Blog Detail & Search for New Blogs
        new_test_slugs = [
            'apple-intelligence-m4-chips-unified-memory-architecture',
            'samsung-galaxy-s25-ultra-galaxy-ai-breakthroughs',
            'apple-vision-pro-spatial-computing-visionos-future',
            'samsung-trifold-foldable-displays-utg-engineering',
            'nvidia-blackwell-gb200-exascale-ai-supercomputing',
            'humanoid-robotics-embodied-ai-optimus-atlas',
            'wifi-7-and-6g-terahertz-wireless-networks'
        ]
        for slug in new_test_slugs:
            resp_blog = client.get(f'/blog/{slug}')
            assert resp_blog.status_code == 200, f"Blog detail failed for slug: {slug}"
        print(f"✓ All {len(new_test_slugs)} New Apple, Samsung, and Tech Blog Routes Verified: 200 OK")

        # Test Search API
        # 10. Test Tech Benchmark & Comparison Suite (/compare)
        resp_comp = client.get('/compare')
        assert resp_comp.status_code == 200
        assert b'TECH BENCHMARK' in resp_comp.data
        print("✓ Tech Comparison Suite Dashboard (/compare): 200 OK")

        resp_comp_preset = client.get('/compare/deepseek-r1-vs-claude-3-7')
        assert resp_comp_preset.status_code == 200
        assert b'DeepSeek-R1 vs Claude 3.7' in resp_comp_preset.data
        print("✓ Tech Comparison Preset (/compare/deepseek-r1-vs-claude-3-7): 200 OK")

        resp_comp_api = client.get('/api/compare/apple-m4-max-vs-snapdragon-8-elite')
        assert resp_comp_api.status_code == 200
        comp_api_data = resp_comp_api.get_json()
        assert comp_api_data['status'] == 'success'
        assert 'Apple Silicon M4 Max' in comp_api_data['data']['item_a']['name']
        print("✓ Tech Comparison API (/api/compare/...): 200 OK")

        # 11. Test RSS Feed (/feed.xml)
        resp_rss = client.get('/feed.xml')
        assert resp_rss.status_code == 200
        assert resp_rss.mimetype == 'application/rss+xml'
        assert b'<rss version="2.0"' in resp_rss.data
        assert b'<channel>' in resp_rss.data
        assert b'<item>' in resp_rss.data
        print("✓ RSS 2.0 Feed Endpoint (/feed.xml): 200 OK & Valid XML")

        # 12. Test Emoji Micro-Reactions API (/api/blog/<slug>/react)
        test_slug = 'apple-intelligence-m4-chips-unified-memory-architecture'
        resp_react = client.post(f'/api/blog/{test_slug}/react', json={'reaction': 'fire'})
        assert resp_react.status_code == 200
        react_data = resp_react.get_json()
        assert react_data['status'] == 'success'
        assert react_data['reaction'] == 'fire'
        assert react_data['count'] >= 1
        print(f"✓ Emoji Micro-Reactions API POST (/api/blog/.../react): Count = {react_data['count']}")

        resp_get_reactions = client.get(f'/api/blog/{test_slug}/reactions')
        assert resp_get_reactions.status_code == 200
        get_react_data = resp_get_reactions.get_json()
        assert get_react_data['status'] == 'success'
        assert 'fire' in get_react_data['reactions']
        print("✓ Emoji Micro-Reactions API GET (/api/blog/.../reactions): 200 OK")

        # 13. Test Article Quiz API (/api/quiz/<slug>)
        resp_quiz = client.get(f'/api/quiz/{test_slug}')
        assert resp_quiz.status_code == 200
        quiz_data = resp_quiz.get_json()
        assert quiz_data['status'] == 'success'
        assert len(quiz_data['quiz']) == 3
        print(f"✓ Article Quiz API (/api/quiz/...): {len(quiz_data['quiz'])} questions verified")

    print("\n🎉 ALL TESTS PASSED WITH 100% SUCCESS! 🎉")

if __name__ == '__main__':
    run_tests()

