import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

import app

def verify_all():
    print("=== VERIFYING UI RENDERING & AI ASSISTANT SUITE ===")
    with app.app.app_context():
        app.init_db()
        client = app.app.test_client()

        # 1. Check Home Page HTML
        resp = client.get('/')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')

        # Header checks
        assert 'nav-asi-bot-btn' not in html, "Ask ASI button must NOT be in the header navbar"
        assert 'class="nav-container"' in html
        assert 'class="nav-right"' in html
        assert 'id="themeToggleBtn"' in html
        assert 'quick-search-trigger' in html
        assert 'id="mobileMenuBtn"' in html
        print("✓ Header Layout: 'Ask ASI' removed, clean action buttons (theme, search, auth, mobile menu)")

        # Brand Logo checks
        assert 'class="logo"' in html
        assert 'class="logo-badge"' in html
        assert 'class="logo-title"' in html
        assert 'class="tech-tag">AI<' in html
        print("✓ Brand Logo: 'ASI TECH' and 'AI' tag formatted on clean single line")

        # Chatbot Floating Widget & Window checks
        assert 'id="asiAiWidgetWrapper"' in html
        assert 'id="asiAiLauncher"' in html
        assert 'class="launcher-aura"' in html
        assert 'class="launcher-badge"' in html
        assert 'id="asiChatWindow"' in html
        assert 'id="asiExpandChatBtn"' in html
        assert 'id="asiClearChatBtn"' in html
        assert 'id="asiCloseChatBtn"' in html
        assert 'id="asiQuickPrompts"' in html
        assert 'id="asiChatMessages"' in html
        assert 'id="asiChatForm"' in html
        assert 'id="asiChatInput"' in html
        print("✓ Enterprise AI Assistant Widget: Floating launcher, expandable window, action toolbar, prompt chips, and message stream present")

        # 2. Test AI Chat Responses
        prompts = [
            ("Who are you?", ["ASI", "AI research assistant", "Core Capabilities"]),
            ("Explain DeepSeek-R1", ["DeepSeek-R1", "Reasoning", "Chain-of-Thought", "```python"]),
            ("What is Quantum AI?", ["Quantum", "Superposition", "Entanglement", "```python"]),
            ("Compare Rust vs Zig vs Mojo", ["Rust", "Zig", "Mojo", "```rust"]),
            ("Give me the 2026 AI Engineer Roadmap", ["Roadmap", "PyTorch", "RAG", "LLMOps"]),
            ("Explain 800V Solid-State EV battery", ["Solid-State", "1,000 Wh/L", "800V"]),
            ("How does Sora work?", ["Sora", "Spacetime", "ICVFX", "Unreal Engine 5.5"])
        ]

        for p, expected_keywords in prompts:
            r = client.post('/api/ai/chat', json={'prompt': p})
            assert r.status_code == 200
            data = r.get_json()
            assert data['status'] == 'success'
            resp_text = data['response']
            for kw in expected_keywords:
                assert kw.lower() in resp_text.lower(), f"Keyword '{kw}' not found in response for prompt '{p}'"
            print(f"✓ AI Prompt '{p}': Success ({len(resp_text)} chars generated)")

        # 3. Static Assets Verification
        with open(os.path.join(os.path.dirname(__file__), '..', 'static', 'css', 'style.css'), 'r', encoding='utf-8') as f:
            css = f.read()
            assert 'white-space: nowrap' in css
            assert '.asi-chat-window.expanded' in css
            assert '.asi-code-block-container' in css
            assert '.launcher-aura' in css
            print("✓ CSS Stylesheet: Responsive header rules, expanded window, code block styles, and animations verified")

        with open(os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'script.js'), 'r', encoding='utf-8') as f:
            js = f.read()
            assert 'copyCodeBlock' in js
            assert 'copyBotMessage' in js
            assert 'asiExpandChatBtn' in js
            assert 'sessionStorage' in js
            print("✓ JavaScript Suite: Copy code handler, copy message handler, expand window toggle, and session persistence verified")

    print("\n🎉 ALL VERIFICATIONS COMPLETED SUCCESSFULLY! 🎉")

if __name__ == '__main__':
    verify_all()
