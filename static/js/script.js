/**
 * ASI TECH - Core JavaScript Suite
 * Features: Day/Night Theme, User Auth (Gmail/Register), Privacy Consent, ASI AI Chatbot (Gemini)
 */

document.addEventListener('DOMContentLoaded', function() {
  initThemeToggle();
  initAuthModal();
  initPrivacyConsent();
  initAsiAIChatbot();
  initScrollAnimations();
  initMobileMenu();
  initSearchModal();
  initReadingProgressBar();
  initBookmarks();
  initEmojiReactions();
  initTableOfContents();
  initEli5Toggle();
  initArticleTTS();
  initAdminEli5Helper();
  initClapButton();
  initShareTools();
  initCategoryFilters();
  initAdminEditor();
  initFAQAccordion();
  initFlashMessages();
});

/* ==========================================================================
   1. GLOBAL ASI AI CHATBOT (POWERED BY GEMINI ENGINE) ENTERPRISE SUITE
   ========================================================================== */
window.toggleAsiChat = function() {
  const chatWindow = document.getElementById('asiChatWindow');
  const chatInput = document.getElementById('asiChatInput');
  if (!chatWindow) return;

  chatWindow.classList.toggle('active');
  if (chatWindow.classList.contains('active')) {
    if (chatInput) {
      setTimeout(() => chatInput.focus(), 150);
    }
  }
};

window.copyCodeBlock = function(btn) {
  if (!btn) return;
  const container = btn.closest('.asi-code-block-container');
  if (!container) return;
  const codeEl = container.querySelector('code');
  if (!codeEl) return;
  
  const text = codeEl.innerText || codeEl.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const origHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check" style="color:#10b981;"></i> Copied!';
    setTimeout(() => {
      btn.innerHTML = origHtml;
    }, 2000);
  }).catch(() => {});
};

window.copyBotMessage = function(btn) {
  if (!btn) return;
  const msgContent = btn.closest('.asi-msg-content');
  if (!msgContent) return;
  const bubble = msgContent.querySelector('.asi-msg-bubble');
  if (!bubble) return;

  const text = bubble.innerText || bubble.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const origHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check" style="color:#10b981;"></i> <span>Copied!</span>';
    setTimeout(() => {
      btn.innerHTML = origHtml;
    }, 2000);
  }).catch(() => {});
};

function initAsiAIChatbot() {
  const chatWindow = document.getElementById('asiChatWindow');
  const clearBtn = document.getElementById('asiClearChatBtn');
  const expandBtn = document.getElementById('asiExpandChatBtn');
  const expandIcon = document.getElementById('asiExpandIcon');
  const chatForm = document.getElementById('asiChatForm');
  const chatInput = document.getElementById('asiChatInput');
  const chatMessages = document.getElementById('asiChatMessages');
  const typingIndicator = document.getElementById('asiTypingIndicator');
  const quickPrompts = document.querySelectorAll('.asi-prompt-pill');

  // Maximize / Expand Window Toggle
  if (expandBtn && chatWindow) {
    expandBtn.addEventListener('click', function() {
      chatWindow.classList.toggle('expanded');
      const isExpanded = chatWindow.classList.contains('expanded');
      if (expandIcon) {
        expandIcon.className = isExpanded ? 'fas fa-compress-alt' : 'fas fa-expand-alt';
      }
    });
  }

  // Clear Conversation Handler
  if (clearBtn && chatMessages) {
    clearBtn.addEventListener('click', function() {
      chatMessages.innerHTML = `
        <div class="asi-message bot">
          <div class="asi-msg-avatar"><i class="fas fa-brain"></i></div>
          <div class="asi-msg-content">
            <div class="asi-msg-bubble">
              <p>👋 Chat session refreshed. I am <strong>ASI</strong>, your enterprise AI assistant. What would you like to explore next?</p>
            </div>
            <div class="asi-msg-footer">
              <span class="asi-msg-time">Just now</span>
              <button type="button" class="asi-copy-msg-btn" onclick="copyBotMessage(this)" title="Copy response">
                <i class="fas fa-copy"></i> <span>Copy</span>
              </button>
            </div>
          </div>
        </div>
      `;
      try {
        sessionStorage.removeItem('asitech_chat_history');
      } catch(e) {}
      if (chatInput) chatInput.focus();
    });
  }

  // Restore Chat from SessionStorage
  try {
    const savedChat = sessionStorage.getItem('asitech_chat_history');
    if (savedChat && chatMessages) {
      chatMessages.innerHTML = savedChat;
    }
  } catch(e) {}

  // Quick Prompt Pills
  quickPrompts.forEach(pill => {
    pill.addEventListener('click', function() {
      const promptText = this.dataset.prompt;
      if (promptText && chatInput && chatForm) {
        chatInput.value = promptText;
        chatForm.dispatchEvent(new Event('submit'));
      }
    });
  });

  // Global Keyboard Shortcuts
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && chatWindow && chatWindow.classList.contains('active')) {
      toggleAsiChat();
    }
  });

  // Handle Chat Form Submit
  if (chatForm) {
    chatForm.addEventListener('submit', function(e) {
      e.preventDefault();
      const userText = (chatInput.value || '').trim();
      if (!userText) return;

      // Append User message
      appendMessage('user', userText);
      chatInput.value = '';

      // Show Typing Indicator
      if (typingIndicator) typingIndicator.style.display = 'flex';
      scrollToBottom();

      // Send Query to Backend Gemini / ASI AI API
      fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userText })
      })
      .then(res => res.json())
      .then(data => {
        if (typingIndicator) typingIndicator.style.display = 'none';
        if (data.status === 'success' && data.response) {
          appendMessage('bot', data.response);
        } else {
          appendMessage('bot', "I encountered a calculation delay. Please ask your question again!");
        }
      })
      .catch(() => {
        if (typingIndicator) typingIndicator.style.display = 'none';
        appendMessage('bot', "Unable to connect to ASI Neural Core. Please verify your connection.");
      });
    });
  }

  function appendMessage(sender, text) {
    if (!chatMessages) return;
    const msgDiv = document.createElement('div');
    msgDiv.className = `asi-message ${sender}`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'asi-msg-avatar';
    avatarDiv.innerHTML = sender === 'bot' ? '<i class="fas fa-brain"></i>' : '<i class="fas fa-user"></i>';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'asi-msg-content';

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'asi-msg-bubble';

    if (sender === 'bot') {
      bubbleDiv.innerHTML = formatBotMarkdown(text);
    } else {
      bubbleDiv.textContent = text;
    }

    contentDiv.appendChild(bubbleDiv);

    // Add footer with time and copy button for bot messages
    if (sender === 'bot') {
      const now = new Date();
      const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const footerDiv = document.createElement('div');
      footerDiv.className = 'asi-msg-footer';
      footerDiv.innerHTML = `
        <span class="asi-msg-time">${timeStr}</span>
        <button type="button" class="asi-copy-msg-btn" onclick="copyBotMessage(this)" title="Copy response">
          <i class="fas fa-copy"></i> <span>Copy</span>
        </button>
      `;
      contentDiv.appendChild(footerDiv);
    }

    msgDiv.appendChild(avatarDiv);
    msgDiv.appendChild(contentDiv);
    chatMessages.appendChild(msgDiv);
    scrollToBottom();

    // Persist in sessionStorage
    try {
      sessionStorage.setItem('asitech_chat_history', chatMessages.innerHTML);
    } catch(e) {}
  }

  function scrollToBottom() {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }

  function formatBotMarkdown(raw) {
    if (!raw) return '';
    
    // Process code blocks with ``` first
    let codeBlocks = [];
    let text = raw.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, function(match, lang, code) {
      const codeIndex = codeBlocks.length;
      lang = lang || 'code';
      const cleanCode = escapeHtml(code.trim());
      const blockHtml = `
        <div class="asi-code-block-container">
          <div class="asi-code-block-header">
            <span><i class="fas fa-terminal" style="margin-right:4px;"></i>${escapeHtml(lang)}</span>
            <button type="button" class="asi-copy-code-btn" onclick="copyCodeBlock(this)">
              <i class="fas fa-copy"></i> Copy
            </button>
          </div>
          <pre><code>${cleanCode}</code></pre>
        </div>
      `;
      codeBlocks.push(blockHtml);
      return `###CODE_BLOCK_${codeIndex}###`;
    });

    let formatted = escapeHtml(text);
    
    // Headings
    formatted = formatted.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    formatted = formatted.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    formatted = formatted.replace(/^# (.+)$/gm, '<h3>$1</h3>');

    // Bold & Italics
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*([^\*]+?)\*/g, '<em>$1</em>');
    formatted = formatted.replace(/_([^_]+?)_/g, '<em>$1</em>');

    // Inline Code
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // Blockquotes
    formatted = formatted.replace(/^>\s+(.+)$/gm, '<blockquote style="border-left:3px solid var(--accent-purple); padding-left:10px; margin:6px 0; color:var(--text-muted); font-style:italic;">$1</blockquote>');

    // Lists (Ordered & Unordered)
    formatted = formatted.replace(/^-\s+(.+)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/^\*\s+(.+)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/^([0-9]+)\.\s+(.+)$/gm, '<li><strong>$1.</strong> $2</li>');
    formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Paragraphs and breaks
    formatted = formatted.replace(/\n\n/g, '</p><p>');
    formatted = formatted.replace(/\n/g, '<br>');

    formatted = `<p>${formatted}</p>`;

    // Restore Code Blocks
    codeBlocks.forEach((block, idx) => {
      formatted = formatted.replace(`###CODE_BLOCK_${idx}###`, block);
    });

    return formatted;
  }
}

/* ==========================================================================
   2. DAY / NIGHT THEME SWITCHER
   ========================================================================== */
function initThemeToggle() {
  const themeBtn = document.getElementById('themeToggleBtn');
  if (!themeBtn) return;

  const currentTheme = localStorage.getItem('asitech_theme') || 'dark';
  if (currentTheme === 'light') {
    document.documentElement.classList.add('light-theme');
    document.body.classList.add('light-theme');
  }

  themeBtn.addEventListener('click', function() {
    const isLight = document.documentElement.classList.toggle('light-theme');
    document.body.classList.toggle('light-theme', isLight);
    localStorage.setItem('asitech_theme', isLight ? 'light' : 'dark');
    
    showToast(isLight ? '☀️ Switched to Light (Day) Mode' : '🌙 Switched to Dark (Night) Mode', 'info');
  });
}

/* ==========================================================================
   3. USER AUTHENTICATION (SIGN IN, REGISTER & GMAIL / GOOGLE)
   ========================================================================== */
function initAuthModal() {
  const modal = document.getElementById('authModalOverlay');
  const openBtn = document.getElementById('openAuthModalBtn');
  const closeBtn = document.getElementById('authModalCloseBtn');
  const tabSignIn = document.getElementById('tabSignInBtn');
  const tabRegister = document.getElementById('tabRegisterBtn');
  const signInForm = document.getElementById('signInForm');
  const registerForm = document.getElementById('registerForm');
  const feedbackMsg = document.getElementById('authFeedbackMsg');
  const btnGoogle = document.getElementById('btnGoogleAuth');
  const userMenuBtn = document.getElementById('userMenuBtn');
  const userMenuPopover = document.getElementById('userMenuPopover');

  if (userMenuBtn && userMenuPopover) {
    userMenuBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      userMenuPopover.classList.toggle('active');
    });

    document.addEventListener('click', function(e) {
      if (!userMenuPopover.contains(e.target) && !userMenuBtn.contains(e.target)) {
        userMenuPopover.classList.remove('active');
      }
    });
  }

  if (!modal) return;

  function openAuth(tab = 'signin') {
    modal.classList.add('active');
    if (tab === 'register') {
      if (tabRegister) tabRegister.click();
    } else {
      if (tabSignIn) tabSignIn.click();
    }
  }

  function closeAuth() {
    modal.classList.remove('active');
    if (feedbackMsg) {
      feedbackMsg.className = 'auth-feedback-msg';
      feedbackMsg.textContent = '';
    }
  }

  if (openBtn) openBtn.addEventListener('click', () => openAuth('signin'));
  if (closeBtn) closeBtn.addEventListener('click', closeAuth);

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeAuth();
  });

  if (tabSignIn && tabRegister) {
    tabSignIn.addEventListener('click', () => {
      tabSignIn.classList.add('active');
      tabRegister.classList.remove('active');
      if (signInForm) signInForm.style.display = 'block';
      if (registerForm) registerForm.style.display = 'none';
      if (feedbackMsg) feedbackMsg.className = 'auth-feedback-msg';
    });

    tabRegister.addEventListener('click', () => {
      tabRegister.classList.add('active');
      tabSignIn.classList.remove('active');
      if (signInForm) signInForm.style.display = 'none';
      if (registerForm) registerForm.style.display = 'block';
      if (feedbackMsg) feedbackMsg.className = 'auth-feedback-msg';
    });
  }

  // Handle Email Login
  if (signInForm) {
    signInForm.addEventListener('submit', function(e) {
      e.preventDefault();
      const email = document.getElementById('loginEmail').value.trim();
      const password = document.getElementById('loginPassword').value.trim();
      const submitBtn = document.getElementById('submitLoginBtn');

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing in...';

      fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      .then(res => res.json())
      .then(data => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-right-to-bracket"></i> Sign In';

        if (data.status === 'success') {
          showToast(data.message, 'success');
          setTimeout(() => window.location.reload(), 500);
        } else {
          feedbackMsg.className = 'auth-feedback-msg error';
          feedbackMsg.textContent = data.message || 'Login failed.';
        }
      })
      .catch(() => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-right-to-bracket"></i> Sign In';
        feedbackMsg.className = 'auth-feedback-msg error';
        feedbackMsg.textContent = 'Server connection error. Please try again.';
      });
    });
  }

  // Handle Email Registration
  if (registerForm) {
    registerForm.addEventListener('submit', function(e) {
      e.preventDefault();
      const name = document.getElementById('regName').value.trim();
      const email = document.getElementById('regEmail').value.trim();
      const password = document.getElementById('regPassword').value.trim();
      const submitBtn = document.getElementById('submitRegisterBtn');

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating account...';

      fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password })
      })
      .then(res => res.json())
      .then(data => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-user-plus"></i> Create Free Account';

        if (data.status === 'success') {
          showToast(data.message, 'success');
          setTimeout(() => window.location.reload(), 500);
        } else {
          feedbackMsg.className = 'auth-feedback-msg error';
          feedbackMsg.textContent = data.message || 'Registration failed.';
        }
      })
      .catch(() => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-user-plus"></i> Create Free Account';
        feedbackMsg.className = 'auth-feedback-msg error';
        feedbackMsg.textContent = 'Server connection error. Please try again.';
      });
    });
  }

  // Handle Google / Gmail One-Click Sign In
  if (btnGoogle) {
    btnGoogle.addEventListener('click', function() {
      btnGoogle.disabled = true;
      btnGoogle.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connecting...';

      const promptEmail = prompt('Enter your Gmail address to sign in (or click OK for demo account):', 'developer@gmail.com');
      const email = promptEmail ? promptEmail.trim() : 'developer@gmail.com';
      const name = email.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

      fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, name })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          showToast(data.message, 'success');
          setTimeout(() => window.location.reload(), 500);
        } else {
          btnGoogle.disabled = false;
          btnGoogle.innerHTML = '<span>Continue with Google / Gmail</span>';
          feedbackMsg.className = 'auth-feedback-msg error';
          feedbackMsg.textContent = data.message || 'Google authentication failed.';
        }
      })
      .catch(() => {
        btnGoogle.disabled = false;
        btnGoogle.innerHTML = '<span>Continue with Google / Gmail</span>';
        feedbackMsg.className = 'auth-feedback-msg error';
        feedbackMsg.textContent = 'Unable to connect to Google Auth service.';
      });
    });
  }
}

/* ==========================================================================
   4. PRIVACY POLICY CONSENT BANNER & MODAL
   ========================================================================== */
function initPrivacyConsent() {
  const consentBar = document.getElementById('privacyConsentBar');
  const acceptBtn = document.getElementById('btnAcceptPrivacy');

  const hasConsent = localStorage.getItem('asitech_privacy_consent');
  if (!hasConsent && consentBar) {
    setTimeout(() => {
      consentBar.classList.add('active');
    }, 1200);
  }

  if (acceptBtn && consentBar) {
    acceptBtn.addEventListener('click', function() {
      localStorage.setItem('asitech_privacy_consent', 'accepted');
      consentBar.classList.remove('active');
      showToast('🛡️ Privacy preferences saved.', 'info');
    });
  }

  window.openPrivacyModal = function() {
    const modal = document.getElementById('privacyModalOverlay');
    if (modal) modal.classList.add('active');
  };

  window.closePrivacyModal = function() {
    const modal = document.getElementById('privacyModalOverlay');
    if (modal) modal.classList.remove('active');
  };
}

/* ==========================================================================
   5. SCROLL REVEAL ANIMATIONS
   ========================================================================== */
function initScrollAnimations() {
  const animatedElements = document.querySelectorAll(
    '.blog-card-modern, .category-card-modern, .bento-main-card, .bento-mini-card, .stat-pill, .newsletter-card, .yt-spotlight-card, .contact-card-box, .contact-direct-card'
  );

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach((entry, idx) => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            entry.target.classList.add('reveal-visible');
          }, idx * 40);
          obs.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.05,
      rootMargin: '0px 0px -20px 0px'
    });

    animatedElements.forEach(el => {
      el.classList.add('reveal-init');
      observer.observe(el);
    });
  } else {
    animatedElements.forEach(el => el.classList.add('reveal-visible'));
  }
}

/* ==========================================================================
   6. MOBILE MENU TOGGLE
   ========================================================================== */
function initMobileMenu() {
  const mobileBtn = document.getElementById('mobileMenuBtn');
  const navLinks = document.getElementById('navLinks');

  if (mobileBtn && navLinks) {
    mobileBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      navLinks.classList.toggle('active');
      const icon = mobileBtn.querySelector('i');
      if (icon) {
        if (navLinks.classList.contains('active')) {
          icon.className = 'fas fa-times';
        } else {
          icon.className = 'fas fa-bars';
        }
      }
    });

    document.addEventListener('click', function(e) {
      if (!navLinks.contains(e.target) && !mobileBtn.contains(e.target)) {
        navLinks.classList.remove('active');
        const icon = mobileBtn.querySelector('i');
        if (icon) icon.className = 'fas fa-bars';
      }
    });
  }
}

/* ==========================================================================
   7. GLOBAL SEARCH MODAL & INSTANT LIVE SEARCH
   ========================================================================== */
function initSearchModal() {
  const overlay = document.getElementById('searchModalOverlay');
  const searchInput = document.getElementById('searchModalInput');
  const resultsContainer = document.getElementById('searchResultsList');
  const closeBtn = document.getElementById('searchCloseBtn');
  const triggers = document.querySelectorAll('.quick-search-trigger');

  if (!overlay || !searchInput) return;

  function openSearch() {
    overlay.classList.add('active');
    setTimeout(() => searchInput.focus(), 50);
  }

  function closeSearch() {
    overlay.classList.remove('active');
    searchInput.value = '';
    if (resultsContainer) {
      resultsContainer.innerHTML = '<div class="search-empty-hint">Type at least 2 characters to search articles...</div>';
    }
  }

  triggers.forEach(t => t.addEventListener('click', openSearch));
  if (closeBtn) closeBtn.addEventListener('click', closeSearch);

  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) closeSearch();
  });

  document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (overlay.classList.contains('active')) closeSearch();
      else openSearch();
    } else if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
      e.preventDefault();
      openSearch();
    } else if (e.key === 'Escape' && overlay.classList.contains('active')) {
      closeSearch();
    }
  });

  let searchTimer;
  searchInput.addEventListener('input', function() {
    clearTimeout(searchTimer);
    const query = this.value.trim();

    if (query.length < 2) {
      if (resultsContainer) {
        resultsContainer.innerHTML = '<div class="search-empty-hint">Type at least 2 characters to search articles...</div>';
      }
      return;
    }

    searchTimer = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          if (!resultsContainer) return;
          if (data.results && data.results.length > 0) {
            resultsContainer.innerHTML = data.results.map(r => `
              <a href="/blog/${r.slug}" class="search-result-item">
                <div class="search-res-info">
                  <h4>${escapeHtml(r.title)}</h4>
                  <p>${escapeHtml(r.snippet)}</p>
                </div>
                <span class="search-res-badge">${escapeHtml(r.category)}</span>
              </a>
            `).join('');
          } else {
            resultsContainer.innerHTML = `
              <div class="search-empty-hint">
                <i class="fas fa-search" style="font-size: 1.4rem; margin-bottom: 8px; display: block; opacity: 0.5;"></i>
                No articles matching "<strong>${escapeHtml(query)}</strong>"
              </div>
            `;
          }
        })
        .catch(() => {
          if (resultsContainer) {
            resultsContainer.innerHTML = '<div class="search-empty-hint">Unable to load search results. Please try again.</div>';
          }
        });
    }, 220);
  });
}

/* ==========================================================================
   8. READING PROGRESS BAR
   ========================================================================== */
function initReadingProgressBar() {
  // Reading progress bar disabled
}

/* ==========================================================================
   9. AUTOMATIC TABLE OF CONTENTS (TOC)
   ========================================================================== */
window.refreshTableOfContents = function(activeContainer) {
  const tocList = document.getElementById('tocList');
  const content = activeContainer || document.querySelector('.blog-prose-view.active') || document.querySelector('.blog-prose');

  if (!tocList || !content) return;

  const headings = content.querySelectorAll('h2, h3');
  const parentBox = tocList.closest('.sidebar-widget-box');
  if (headings.length === 0) {
    if (parentBox) parentBox.style.display = 'none';
    return;
  }
  if (parentBox) parentBox.style.display = 'block';

  tocList.innerHTML = '';
  headings.forEach((heading, idx) => {
    if (!heading.id) {
      heading.id = 'heading-sec-' + idx;
    }
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = '#' + heading.id;
    a.className = 'toc-link';
    if (heading.tagName.toLowerCase() === 'h3') {
      a.style.paddingLeft = '16px';
      a.style.fontSize = '0.8rem';
    }
    a.textContent = heading.textContent.trim();
    li.appendChild(a);
    tocList.appendChild(li);
  });

  const links = tocList.querySelectorAll('.toc-link');
  const onScroll = function() {
    let currentId = '';
    headings.forEach(h => {
      const top = h.getBoundingClientRect().top;
      if (top <= 150) {
        currentId = h.id;
      }
    });

    links.forEach(l => {
      if (l.getAttribute('href') === '#' + currentId) {
        l.classList.add('active');
      } else {
        l.classList.remove('active');
      }
    });
  };
  window.removeEventListener('scroll', window._tocScrollHandler);
  window._tocScrollHandler = onScroll;
  window.addEventListener('scroll', onScroll, { passive: true });
};

function initTableOfContents() {
  window.refreshTableOfContents();
}

/* ==========================================================================
   10. INTERACTIVE CLAP / LIKE BUTTON
   ========================================================================== */
function initClapButton() {
  const clapBtn = document.getElementById('clapBtn');
  if (!clapBtn) return;

  const slug = clapBtn.dataset.slug;
  const countSpan = clapBtn.querySelector('.clap-count');
  const isLiked = localStorage.getItem('liked_' + slug);

  if (isLiked) {
    clapBtn.classList.add('clapped');
  }

  clapBtn.addEventListener('click', function() {
    fetch(`/api/blog/${encodeURIComponent(slug)}/like`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          countSpan.textContent = data.likes;
          clapBtn.classList.add('clapped');
          localStorage.setItem('liked_' + slug, 'true');
          showToast('👏 Thanks for your appreciation!', 'success');
        }
      })
      .catch(() => showToast('Error sending clap', 'error'));
  });
}

/* ==========================================================================
   11. SHARE TOOLS
   ========================================================================== */
function initShareTools() {
  window.copyArticleLink = function() {
    navigator.clipboard.writeText(window.location.href).then(() => {
      showToast('📋 Article link copied to clipboard!', 'success');
    }).catch(() => {
      showToast('Could not copy link.', 'error');
    });
  };
}

/* ==========================================================================
   12. CATEGORY FILTER TABS
   ========================================================================== */
function initCategoryFilters() {
  const tabs = document.querySelectorAll('.filter-tab');
  const cards = document.querySelectorAll('.blog-card-modern[data-category]');

  if (tabs.length === 0 || cards.length === 0) return;

  tabs.forEach(tab => {
    tab.addEventListener('click', function() {
      tabs.forEach(t => t.classList.remove('active'));
      this.classList.add('active');

      const selected = this.dataset.category;

      cards.forEach(card => {
        if (selected === 'all' || card.dataset.category === selected) {
          card.style.display = 'flex';
          card.style.opacity = '0';
          card.style.transform = 'translateY(10px)';
          setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
          }, 30);
        } else {
          card.style.display = 'none';
        }
      });
    });
  });
}

/* ==========================================================================
   13. ADMIN POST EDITOR
   ========================================================================== */
function parseClientSideSyntax(content) {
  if (!content) return '<p style="color:#a1a1aa;">No content entered yet.</p>';
  
  const lines = content.split('\n');
  const output = [];
  let inCode = false;
  let inUl = false;
  let inOl = false;
  let codeLines = [];
  let isFirstP = true;

  function formatInline(text) {
    if (!text) return '';
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.+?)\*/g, '<strong>$1</strong>');
    text = text.replace(/_(.+?)_/g, '<em>$1</em>');
    text = text.replace(/\/\/(.+?)\/\//g, '<em>$1</em>');
    return text;
  }

  for (let raw of lines) {
    const stripped = raw.trim();

    if (stripped.startsWith('```')) {
      if (inCode) {
        inCode = false;
        output.push(`<pre><code>${codeLines.join('\n')}</code></pre>`);
        codeLines = [];
      } else {
        if (inUl) { output.push('</ul>'); inUl = false; }
        if (inOl) { output.push('</ol>'); inOl = false; }
        inCode = true;
      }
      continue;
    }

    if (inCode) {
      codeLines.push(escapeHtml(raw));
      continue;
    }

    const isUl = stripped.startsWith('- ') || stripped.startsWith('* ');
    const isOl = /^\d+\.\s/.test(stripped);

    if (!isUl && inUl) { output.push('</ul>'); inUl = false; }
    if (!isOl && inOl) { output.push('</ol>'); inOl = false; }

    if (!stripped) continue;

    if (stripped.startsWith('### ')) {
      output.push(`<h3>${formatInline(stripped.slice(4))}</h3>`);
    } else if (stripped.startsWith('#### ')) {
      output.push(`<h4>${formatInline(stripped.slice(5))}</h4>`);
    } else if (stripped.startsWith('## ')) {
      output.push(`<h2>${formatInline(stripped.slice(3))}</h2>`);
    } else if (stripped.startsWith('# ')) {
      output.push(`<h2>${formatInline(stripped.slice(2))}</h2>`);
    } else if (stripped.startsWith('> ')) {
      output.push(`<blockquote>${formatInline(stripped.slice(2))}</blockquote>`);
    } else if (stripped.startsWith('! ')) {
      output.push(`<div class="tech-highlight-box"><h4>💡 Key Takeaway</h4><p>${formatInline(stripped.slice(2))}</p></div>`);
    } else if (isUl) {
      if (!inUl) { output.push('<ul>'); inUl = true; }
      output.push(`<li>${formatInline(stripped.slice(2))}</li>`);
    } else if (isOl) {
      if (!inOl) { output.push('<ol>'); inOl = true; }
      output.push(`<li>${formatInline(stripped.replace(/^\d+\.\s*/, ''))}</li>`);
    } else if (stripped.startsWith('<') && stripped.endsWith('>')) {
      output.push(raw);
    } else {
      const pClass = isFirstP ? ' class="lead-paragraph"' : '';
      output.push(`<p${pClass}>${formatInline(stripped)}</p>`);
      isFirstP = false;
    }
  }

  if (inCode) output.push(`<pre><code>${codeLines.join('\n')}</code></pre>`);
  if (inUl) output.push('</ul>');
  if (inOl) output.push('</ol>');

  return output.join('\n');
}

function initAdminEditor() {
  const titleInput = document.querySelector('input[name="title"]');
  const slugInput = document.querySelector('input[name="slug"]');
  const contentTextarea = document.getElementById('articleContentInput') || document.querySelector('textarea[name="content"]');
  const previewPane = document.getElementById('editorPreviewPane');
  const editorTab = document.getElementById('tabEditorBtn');
  const previewTab = document.getElementById('tabPreviewBtn');
  const editorWrap = document.getElementById('editorInputWrap');

  if (titleInput && slugInput && !slugInput.value) {
    titleInput.addEventListener('input', function() {
      slugInput.value = this.value
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .trim();
    });
  }

  if (editorTab && previewTab && editorWrap && previewPane && contentTextarea) {
    editorTab.addEventListener('click', () => {
      editorTab.classList.add('active');
      previewTab.classList.remove('active');
      editorWrap.style.display = 'block';
      previewPane.classList.remove('active');
    });

    previewTab.addEventListener('click', () => {
      previewTab.classList.add('active');
      editorTab.classList.remove('active');
      editorWrap.style.display = 'none';
      previewPane.classList.add('active');
      previewPane.innerHTML = parseClientSideSyntax(contentTextarea.value);
    });
  }

  window.insertSyntaxTag = function(openTag, closeTag) {
    if (!contentTextarea) return;
    const start = contentTextarea.selectionStart;
    const end = contentTextarea.selectionEnd;
    const text = contentTextarea.value;
    const selected = text.substring(start, end) || (openTag.startsWith('#') ? 'Heading Title' : 'text');
    const replacement = openTag + selected + (closeTag || '');
    contentTextarea.value = text.substring(0, start) + replacement + text.substring(end);
    contentTextarea.focus();
    contentTextarea.setSelectionRange(start + openTag.length, start + openTag.length + selected.length);
  };
}

/* ==========================================================================
   14. FAQ ACCORDION
   ========================================================================== */
function initFAQAccordion() {
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const q = item.querySelector('.faq-question');
    if (q) {
      q.addEventListener('click', () => {
        const isActive = item.classList.contains('active');
        faqItems.forEach(i => i.classList.remove('active'));
        if (!isActive) item.classList.add('active');
      });
    }
  });
}

/* ==========================================================================
   15. FLASH MESSAGES & TOASTS
   ========================================================================== */
function initFlashMessages() {
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(f => {
    setTimeout(() => {
      f.style.opacity = '0';
      f.style.transform = 'translateX(50px)';
      setTimeout(() => f.remove(), 400);
    }, 4500);
  });
}

function showToast(msg, type = 'success') {
  let container = document.querySelector('.flash-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'flash-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `flash flash-${type}`;
  toast.innerHTML = `
    <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'}"></i>
    <span>${escapeHtml(msg)}</span>
    <span class="flash-close" onclick="this.parentElement.remove()">&times;</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(50px)';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/* ==========================================================================
   16. EXPLAIN LIKE I'M 5 (ELI5) IN-PLACE TOGGLE CONTROLLER
   ========================================================================== */
function initEli5Toggle() {
  const techBtn = document.getElementById('btnModeTechnical');
  const eli5Btn = document.getElementById('btnModeEli5');
  const techProse = document.getElementById('blogProseTechnical');
  const eli5Prose = document.getElementById('blogProseEli5');
  const ttsModeTag = document.getElementById('ttsModeTag');
  const ttsStatusText = document.getElementById('ttsStatusText');
  const ttsDockMeta = document.getElementById('ttsDockMeta');

  if (!techBtn || !eli5Btn || !techProse || !eli5Prose) return;

  window.switchReadingMode = function(mode) {
    if (mode === 'eli5') {
      techBtn.classList.remove('active');
      techBtn.setAttribute('aria-selected', 'false');
      eli5Btn.classList.add('active');
      eli5Btn.setAttribute('aria-selected', 'true');

      techProse.style.display = 'none';
      techProse.classList.remove('active');
      eli5Prose.style.display = 'block';
      eli5Prose.classList.add('active');

      if (ttsModeTag) {
        ttsModeTag.textContent = 'ELI5 Mode';
        ttsModeTag.style.background = 'rgba(168, 85, 247, 0.2)';
        ttsModeTag.style.color = '#c084fc';
        ttsModeTag.style.borderColor = 'rgba(168, 85, 247, 0.4)';
      }
      if (ttsStatusText) {
        ttsStatusText.textContent = 'Narrating simplified ELI5 summary with real-world analogies';
      }
      if (ttsDockMeta) {
        ttsDockMeta.textContent = 'Narrating: ELI5 Simplified Summary';
      }

      window.refreshTableOfContents(eli5Prose);

      // Notify TTS engine of mode change
      if (window._ttsEngine && window._ttsEngine.onModeSwitched) {
        window._ttsEngine.onModeSwitched('eli5');
      }
    } else {
      eli5Btn.classList.remove('active');
      eli5Btn.setAttribute('aria-selected', 'false');
      techBtn.classList.add('active');
      techBtn.setAttribute('aria-selected', 'true');

      eli5Prose.style.display = 'none';
      eli5Prose.classList.remove('active');
      techProse.style.display = 'block';
      techProse.classList.add('active');

      if (ttsModeTag) {
        ttsModeTag.textContent = 'Technical Mode';
        ttsModeTag.style.background = 'rgba(16, 185, 129, 0.16)';
        ttsModeTag.style.color = 'var(--accent-emerald-light)';
        ttsModeTag.style.borderColor = 'rgba(16, 185, 129, 0.35)';
      }
      if (ttsStatusText) {
        ttsStatusText.textContent = 'Listen to AI audio narration with live read-along tracking';
      }
      if (ttsDockMeta) {
        ttsDockMeta.textContent = 'Narrating: Technical Deep Dive';
      }

      window.refreshTableOfContents(techProse);

      // Notify TTS engine of mode change
      if (window._ttsEngine && window._ttsEngine.onModeSwitched) {
        window._ttsEngine.onModeSwitched('technical');
      }
    }
  };
}

/* ==========================================================================
   17. TEXT-TO-SPEECH (TTS) ENTERPRISE NARRATION SUITE
   ========================================================================== */
function initArticleTTS() {
  const card = document.getElementById('ttsNarrationCard');
  if (!card) return;

  const playPauseBtn = document.getElementById('ttsPlayPauseBtn');
  const playIcon = document.getElementById('ttsPlayIcon');
  const rewindBtn = document.getElementById('ttsRewindBtn');
  const forwardBtn = document.getElementById('ttsForwardBtn');
  const stopBtn = document.getElementById('ttsStopBtn');
  const voiceSelect = document.getElementById('ttsVoiceSelect');
  const speedBtns = document.querySelectorAll('.tts-speed-btn');
  const highlightToggle = document.getElementById('ttsHighlightToggle');
  const equalizer = document.getElementById('ttsEqualizer');
  const progressTrack = document.getElementById('ttsProgressTrack');
  const progressFill = document.getElementById('ttsProgressFill');
  const currentTimeEl = document.getElementById('ttsCurrentTime');
  const totalTimeEl = document.getElementById('ttsTotalTime');

  // Floating Mini Dock
  const floatingDock = document.getElementById('ttsFloatingDock');
  const dockPlayBtn = document.getElementById('ttsDockPlayBtn');
  const dockPlayIcon = document.getElementById('ttsDockPlayIcon');
  const dockProgressBar = document.getElementById('ttsDockProgressBar');
  const dockProgressWrap = document.getElementById('ttsDockProgressWrap');
  const dockCloseBtn = document.getElementById('ttsDockCloseBtn');

  if (!('speechSynthesis' in window)) {
    card.style.display = 'none';
    return;
  }

  const synth = window.speechSynthesis;
  let voices = [];
  let selectedVoice = null;
  let isPlaying = false;
  let isPaused = false;
  let currentMode = 'technical';
  let chunks = [];
  let currentChunkIdx = 0;
  let playbackRate = 1.0;
  let highlightEnabled = true;
  let timerInterval = null;
  let totalEstimatedSeconds = 180;

  // 1. Populate Natural Voices
  function loadVoices() {
    const allVoices = synth.getVoices();
    voices = allVoices.filter(v => v.lang && v.lang.startsWith('en'));
    if (voices.length === 0) {
      voices = allVoices;
    }
    if (voiceSelect) {
      voiceSelect.innerHTML = '';
      voices.forEach((v, i) => {
        const opt = document.createElement('option');
        opt.value = i;
        const isDefault = v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Neural') || v.default;
        opt.textContent = `${v.name.replace(/Microsoft|Google|Apple|Desktop/g, '').trim()} (${v.lang})`;
        if (isDefault && !selectedVoice) {
          opt.selected = true;
          selectedVoice = v;
        }
        voiceSelect.appendChild(opt);
      });
      if (!selectedVoice && voices.length > 0) {
        selectedVoice = voices[0];
      }
    }
  }

  loadVoices();
  if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = loadVoices;
  }

  if (voiceSelect) {
    voiceSelect.addEventListener('change', function() {
      const idx = parseInt(this.value, 10);
      selectedVoice = voices[idx] || null;
      if (isPlaying && !isPaused) {
        restartCurrentChunk();
      }
    });
  }

  // 2. Speed Selection
  speedBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      speedBtns.forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      playbackRate = parseFloat(this.dataset.speed) || 1.0;
      if (isPlaying && !isPaused) {
        restartCurrentChunk();
      }
    });
  });

  // 3. Highlight Toggle
  if (highlightToggle) {
    highlightEnabled = highlightToggle.checked;
    highlightToggle.addEventListener('change', function() {
      highlightEnabled = this.checked;
      if (!highlightEnabled) {
        clearHighlights();
      }
    });
  }

  // 4. Build Speech Chunks from DOM
  function buildChunks() {
    chunks = [];
    const containerId = currentMode === 'eli5' ? 'blogProseEli5' : 'blogProseTechnical';
    const container = document.getElementById(containerId);
    if (!container) return;

    // Grab readable block elements
    const elements = container.querySelectorAll('p, h2, h3, h4, li, blockquote, .tech-highlight-box');
    elements.forEach((el) => {
      let rawText = el.innerText || el.textContent || '';
      rawText = rawText.replace(/\s+/g, ' ').trim();
      if (!rawText || rawText.length < 2) return;

      // If text is very long, split on sentence boundaries
      if (rawText.length > 180) {
        const sentences = rawText.match(/[^.!?]+[.!?]+(\s+|$)|[^.!?]+$/g) || [rawText];
        sentences.forEach(s => {
          const sTrim = s.trim();
          if (sTrim.length > 0) {
            chunks.push({ text: sTrim, element: el });
          }
        });
      } else {
        chunks.push({ text: rawText, element: el });
      }
    });

    // Estimate total seconds
    const totalWords = chunks.reduce((acc, c) => acc + c.text.split(' ').length, 0);
    totalEstimatedSeconds = Math.max(30, Math.round((totalWords / 150) * 60));
    if (totalTimeEl) {
      totalTimeEl.textContent = formatTime(totalEstimatedSeconds);
    }
  }

  function formatTime(sec) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  function clearHighlights() {
    document.querySelectorAll('.tts-highlight-active').forEach(el => {
      el.classList.remove('tts-highlight-active');
    });
  }

  function highlightElement(el) {
    clearHighlights();
    if (!el || !highlightEnabled) return;
    el.classList.add('tts-highlight-active');
    
    // Auto-scroll into view smoothly
    const rect = el.getBoundingClientRect();
    if (rect.top < 100 || rect.bottom > window.innerHeight - 100) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  function updateTimeline() {
    if (chunks.length === 0) return;
    const progress = Math.min(100, Math.max(0, (currentChunkIdx / chunks.length) * 100));
    if (progressFill) progressFill.style.width = progress + '%';
    if (dockProgressBar) dockProgressBar.style.width = progress + '%';
    
    const curSec = Math.min(totalEstimatedSeconds, Math.round((currentChunkIdx / chunks.length) * totalEstimatedSeconds));
    if (currentTimeEl) currentTimeEl.textContent = formatTime(curSec);
  }

  // 5. Speech Playback Core
  function speakChunk(idx) {
    if (idx >= chunks.length) {
      stop();
      showToast('Finished audio narration!', 'success');
      return;
    }

    currentChunkIdx = idx;
    const chunk = chunks[idx];
    updateTimeline();
    highlightElement(chunk.element);

    const utterance = new SpeechSynthesisUtterance(chunk.text);
    if (selectedVoice) utterance.voice = selectedVoice;
    utterance.rate = playbackRate;
    utterance.pitch = 1.0;

    utterance.onstart = function() {
      // Speech started
    };

    utterance.onend = function() {
      if (isPlaying && !isPaused) {
        speakChunk(idx + 1);
      }
    };

    utterance.onerror = function(e) {
      if (e.error === 'interrupted' || e.error === 'canceled') return;
      if (isPlaying && !isPaused) {
        speakChunk(idx + 1);
      }
    };

    synth.speak(utterance);
  }

  function restartCurrentChunk() {
    synth.cancel();
    if (isPlaying && !isPaused) {
      speakChunk(currentChunkIdx);
    }
  }

  function play() {
    if (chunks.length === 0) {
      buildChunks();
    }
    if (chunks.length === 0) return;

    if (isPaused) {
      synth.resume();
      isPaused = false;
      isPlaying = true;
    } else {
      synth.cancel();
      isPlaying = true;
      isPaused = false;
      speakChunk(currentChunkIdx);
    }

    setPlayingUI(true);
    startTimer();
  }

  function pause() {
    if (!isPlaying) return;
    synth.pause();
    isPaused = true;
    setPlayingUI(false);
    stopTimer();
  }

  function stop() {
    synth.cancel();
    isPlaying = false;
    isPaused = false;
    currentChunkIdx = 0;
    clearHighlights();
    setPlayingUI(false);
    updateTimeline();
    stopTimer();
    if (currentTimeEl) currentTimeEl.textContent = '0:00';
    if (floatingDock) floatingDock.style.display = 'none';
  }

  function setPlayingUI(playing) {
    if (playIcon) {
      playIcon.className = playing ? 'fas fa-pause' : 'fas fa-play';
    }
    if (dockPlayIcon) {
      dockPlayIcon.className = playing ? 'fas fa-pause' : 'fas fa-play';
    }
    if (playPauseBtn) {
      if (playing) playPauseBtn.classList.add('playing');
      else playPauseBtn.classList.remove('playing');
    }
    if (equalizer) {
      if (playing) equalizer.classList.add('playing');
      else equalizer.classList.remove('playing');
    }
  }

  function startTimer() {
    stopTimer();
    timerInterval = setInterval(() => {
      // Keep browser synth alive (prevents Chrome 15s pause bug)
      if (synth.speaking && !synth.paused) {
        synth.pause();
        synth.resume();
      }
    }, 10000);
  }

  function stopTimer() {
    if (timerInterval) clearInterval(timerInterval);
  }

  // 6. Button Listeners
  if (playPauseBtn) {
    playPauseBtn.addEventListener('click', function() {
      if (isPlaying && !isPaused) {
        pause();
      } else {
        play();
      }
    });
  }

  if (dockPlayBtn) {
    dockPlayBtn.addEventListener('click', function() {
      if (isPlaying && !isPaused) {
        pause();
      } else {
        play();
      }
    });
  }

  if (stopBtn) {
    stopBtn.addEventListener('click', stop);
  }

  if (dockCloseBtn) {
    dockCloseBtn.addEventListener('click', stop);
  }

  if (rewindBtn) {
    rewindBtn.addEventListener('click', function() {
      if (chunks.length === 0) return;
      const jumpChunks = Math.max(1, Math.round(chunks.length * (10 / totalEstimatedSeconds)));
      currentChunkIdx = Math.max(0, currentChunkIdx - jumpChunks);
      restartCurrentChunk();
    });
  }

  if (forwardBtn) {
    forwardBtn.addEventListener('click', function() {
      if (chunks.length === 0) return;
      const jumpChunks = Math.max(1, Math.round(chunks.length * (10 / totalEstimatedSeconds)));
      currentChunkIdx = Math.min(chunks.length - 1, currentChunkIdx + jumpChunks);
      restartCurrentChunk();
    });
  }

  // 7. Timeline Click / Seeking
  function handleTimelineClick(e, trackEl) {
    if (chunks.length === 0) buildChunks();
    if (chunks.length === 0) return;
    const rect = trackEl.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percent = Math.max(0, Math.min(1, clickX / rect.width));
    currentChunkIdx = Math.floor(percent * chunks.length);
    if (currentChunkIdx >= chunks.length) currentChunkIdx = chunks.length - 1;
    
    if (isPlaying) {
      restartCurrentChunk();
    } else {
      updateTimeline();
      highlightElement(chunks[currentChunkIdx].element);
    }
  }

  if (progressTrack) {
    progressTrack.addEventListener('click', function(e) {
      handleTimelineClick(e, this);
    });
  }

  if (dockProgressWrap) {
    dockProgressWrap.addEventListener('click', function(e) {
      handleTimelineClick(e, this);
    });
  }

  // 8. Sticky Floating Dock Scroll Trigger
  window.addEventListener('scroll', function() {
    if (!floatingDock) return;
    const cardRect = card.getBoundingClientRect();
    if (isPlaying && cardRect.bottom < 0) {
      floatingDock.style.display = 'block';
    } else {
      floatingDock.style.display = 'none';
    }
  }, { passive: true });

  // 9. Mode Switch Notification
  window._ttsEngine = {
    onModeSwitched: function(newMode) {
      currentMode = newMode;
      const wasSpeaking = isPlaying && !isPaused;
      stop();
      buildChunks();
      if (wasSpeaking) {
        play();
      }
    }
  };

  buildChunks();
}

/* ==========================================================================
   18. ADMIN AUTO-GENERATE ELI5 HELPER
   ========================================================================== */
function initAdminEli5Helper() {
  const btn = document.getElementById('btnAutoGenerateEli5');
  const eli5Input = document.getElementById('eli5ContentInput');
  const contentInput = document.getElementById('articleContentInput');
  const titleInput = document.querySelector('input[name="title"]');

  if (!btn || !eli5Input || !contentInput) return;

  btn.addEventListener('click', async function() {
    const title = titleInput ? titleInput.value.trim() : '';
    const content = contentInput.value.trim();

    if (!content) {
      showToast('Please write the article content first before generating an ELI5 summary!', 'error');
      return;
    }

    const origHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating with AI...';
    btn.disabled = true;

    try {
      const res = await fetch('/api/ai/generate-eli5', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content })
      });
      const data = await res.json();
      if (data.status === 'success' && data.eli5_content) {
        eli5Input.value = data.eli5_content;
        showToast('✨ ELI5 summary generated successfully!', 'success');
        eli5Input.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        showToast(data.message || 'Failed to generate ELI5 summary.', 'error');
      }
    } catch (err) {
      showToast('Error connecting to AI service.', 'error');
    } finally {
      btn.innerHTML = origHtml;
      btn.disabled = false;
    }
  });
}

/* ==========================================================================
   19. MULTI-THEME ENGINE (DARK, CYBERPUNK, OLED, LIGHT)
   ========================================================================== */
function initThemeToggle() {
  const themeDropdownWrap = document.getElementById('themeDropdownWrap');
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const themeMenuPopover = document.getElementById('themeMenuPopover');
  const themeOptBtns = document.querySelectorAll('.theme-opt-btn');

  // Load saved theme or default to 'dark'
  const savedTheme = localStorage.getItem('asi_theme') || 'dark';
  applyTheme(savedTheme);

  function applyTheme(themeName) {
    document.body.classList.remove('theme-cyberpunk', 'theme-oled', 'light-theme');
    if (themeName === 'cyberpunk') {
      document.body.classList.add('theme-cyberpunk');
    } else if (themeName === 'oled') {
      document.body.classList.add('theme-oled');
    } else if (themeName === 'light') {
      document.body.classList.add('light-theme');
    }
    localStorage.setItem('asi_theme', themeName);

    // Update active button state
    themeOptBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.theme === themeName);
    });
  }

  // Toggle Popover
  if (themeToggleBtn && themeDropdownWrap) {
    themeToggleBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      themeDropdownWrap.classList.toggle('active');
    });

    document.addEventListener('click', function(e) {
      if (!themeDropdownWrap.contains(e.target)) {
        themeDropdownWrap.classList.remove('active');
      }
    });
  }

  themeOptBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const theme = this.dataset.theme;
      applyTheme(theme);
      if (themeDropdownWrap) themeDropdownWrap.classList.remove('active');
    });
  });
}

/* ==========================================================================
   20. READING PROGRESS BAR
   ========================================================================== */
function initReadingProgressBar() {
  const progressBar = document.getElementById('readingProgressBar');
  if (!progressBar) return;

  window.addEventListener('scroll', function() {
    const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
    if (totalHeight <= 0) return;
    const progress = (window.scrollY / totalHeight) * 100;
    progressBar.style.width = Math.min(100, Math.max(0, progress)) + '%';
  }, { passive: true });
}

/* ==========================================================================
   21. BOOKMARKS & READING LIST DRAWER
   ========================================================================== */
function getBookmarks() {
  try {
    return JSON.parse(localStorage.getItem('asi_bookmarks') || '[]');
  } catch (e) {
    return [];
  }
}

function saveBookmarks(bms) {
  localStorage.setItem('asi_bookmarks', JSON.stringify(bms));
  updateBookmarkBadges();
  renderBookmarksList();
}

function updateBookmarkBadges() {
  const bms = getBookmarks();
  const navBadge = document.getElementById('navBookmarkCount');
  const drawerBadge = document.getElementById('drawerBookmarkCount');
  if (navBadge) navBadge.textContent = bms.length;
  if (drawerBadge) drawerBadge.textContent = bms.length;

  // Update card buttons
  document.querySelectorAll('.card-bookmark-btn').forEach(btn => {
    const slug = btn.dataset.slug;
    const isSaved = bms.some(b => b.slug === slug);
    btn.classList.toggle('active', isSaved);
    const icon = btn.querySelector('i');
    if (icon) {
      icon.className = isSaved ? 'fas fa-bookmark' : 'far fa-bookmark';
    }
  });

  // Update article header button
  const articleBmBtn = document.getElementById('articleBookmarkBtn');
  if (articleBmBtn) {
    const slug = articleBmBtn.dataset.slug;
    const isSaved = bms.some(b => b.slug === slug);
    articleBmBtn.classList.toggle('active', isSaved);
    const icon = articleBmBtn.querySelector('i');
    const span = articleBmBtn.querySelector('span');
    if (icon) icon.className = isSaved ? 'fas fa-bookmark' : 'far fa-bookmark';
    if (span) span.textContent = isSaved ? 'Saved' : 'Save';
  }
}

function renderBookmarksList() {
  const container = document.getElementById('bookmarksListContainer');
  if (!container) return;
  const bms = getBookmarks();

  if (bms.length === 0) {
    container.innerHTML = `
      <div class="drawer-empty-state">
        <i class="far fa-bookmark"></i>
        <p>No saved articles yet.<br>Click the <i class="fas fa-bookmark"></i> bookmark icon on any article or card to save it for later!</p>
      </div>
    `;
    return;
  }

  container.innerHTML = bms.map(item => `
    <div class="drawer-bookmark-item">
      <div class="drawer-bm-info">
        <a href="/blog/${encodeURIComponent(item.slug)}">${item.title}</a>
        <div class="drawer-bm-meta">
          <span><i class="fas fa-layer-group"></i> ${item.category || 'Tech'}</span>
          <span><i class="fas fa-clock"></i> ${item.readtime || 4} min read</span>
        </div>
      </div>
      <button type="button" class="drawer-bm-del-btn" title="Remove from list" onclick="removeBookmark('${item.slug}')">
        <i class="fas fa-trash-can"></i>
      </button>
    </div>
  `).join('');
}

window.removeBookmark = function(slug) {
  let bms = getBookmarks();
  bms = bms.filter(b => b.slug !== slug);
  saveBookmarks(bms);
};

window.toggleCardBookmark = function(e, btn) {
  if (e) e.preventDefault();
  if (e) e.stopPropagation();
  const slug = btn.dataset.slug;
  const title = btn.dataset.title;
  const readtime = btn.dataset.readtime;
  const category = btn.dataset.category;

  let bms = getBookmarks();
  const idx = bms.findIndex(b => b.slug === slug);
  if (idx > -1) {
    bms.splice(idx, 1);
  } else {
    bms.unshift({ slug, title, readtime, category, timestamp: Date.now() });
  }
  saveBookmarks(bms);
};

function initBookmarks() {
  const drawerBtn = document.getElementById('bookmarkDrawerBtn');
  const drawer = document.getElementById('bookmarksDrawer');
  const overlay = document.getElementById('bookmarksOverlay');
  const closeBtn = document.getElementById('closeBookmarksBtn');
  const clearBtn = document.getElementById('clearBookmarksBtn');
  const articleBmBtn = document.getElementById('articleBookmarkBtn');

  function openDrawer() {
    if (drawer) drawer.classList.add('open');
    if (overlay) overlay.classList.add('active');
    renderBookmarksList();
  }

  function closeDrawer() {
    if (drawer) drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
  }

  if (drawerBtn) drawerBtn.addEventListener('click', openDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (overlay) overlay.addEventListener('click', closeDrawer);

  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      saveBookmarks([]);
    });
  }

  if (articleBmBtn) {
    articleBmBtn.addEventListener('click', function() {
      const slug = this.dataset.slug;
      const title = this.dataset.title;
      const readtime = this.dataset.readtime;
      const category = this.dataset.category;

      let bms = getBookmarks();
      const idx = bms.findIndex(b => b.slug === slug);
      if (idx > -1) {
        bms.splice(idx, 1);
      } else {
        bms.unshift({ slug, title, readtime, category, timestamp: Date.now() });
      }
      saveBookmarks(bms);
    });
  }

  updateBookmarkBadges();
  renderBookmarksList();
}

/* ==========================================================================
   22. EMOJI MICRO-REACTIONS CONTROLLER
   ========================================================================== */
function initEmojiReactions() {
  const buttons = document.querySelectorAll('.reaction-pill-btn');
  if (buttons.length === 0) return;

  buttons.forEach(btn => {
    const slug = btn.dataset.slug;
    const reaction = btn.dataset.reaction;

    // Check if user already reacted
    if (localStorage.getItem(`asi_react_${slug}_${reaction}`)) {
      btn.classList.add('user-reacted');
    }

    btn.addEventListener('click', async function() {
      const counterEl = document.getElementById(`reactCount-${reaction}`);
      const curVal = parseInt(counterEl ? counterEl.textContent : '0') || 0;
      
      // Optimistic UI update
      if (counterEl) counterEl.textContent = curVal + 1;
      btn.classList.add('user-reacted');
      btn.style.transform = 'scale(1.18)';
      setTimeout(() => btn.style.transform = '', 250);

      localStorage.setItem(`asi_react_${slug}_${reaction}`, 'true');

      try {
        const res = await fetch(`/api/blog/${encodeURIComponent(slug)}/react`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reaction: reaction })
        });
        const data = await res.json();
        if (data.status === 'success' && data.reactions) {
          Object.keys(data.reactions).forEach(rKey => {
            const countSpan = document.getElementById(`reactCount-${rKey}`);
            if (countSpan) countSpan.textContent = data.reactions[rKey];
          });
        }
      } catch (err) {
        console.error('Reaction sync error:', err);
      }
    });
  });
}

/* ==========================================================================
   23. INTERACTIVE ARTICLE COMPREHENSION QUIZ ENGINE
   ========================================================================== */
let userQuizScore = 0;
let answeredCount = 0;

window.selectQuizOption = function(btn, qIndex, optIndex, correctIndex) {
  const parentQuestion = btn.closest('.quiz-question-item');
  if (!parentQuestion) return;

  const allBtns = parentQuestion.querySelectorAll('.quiz-option-btn');
  allBtns.forEach(b => b.disabled = true);

  const isCorrect = (optIndex === correctIndex);
  if (isCorrect) {
    btn.classList.add('correct');
    userQuizScore++;
  } else {
    btn.classList.add('wrong');
    // Highlight correct answer
    if (allBtns[correctIndex]) {
      allBtns[correctIndex].classList.add('correct');
    }
  }

  // Show explanation
  const expl = document.getElementById(`quizExpl-${qIndex}`);
  if (expl) expl.style.display = 'flex';

  answeredCount++;

  const totalQuestions = document.querySelectorAll('.quiz-question-item').length;
  if (answeredCount >= totalQuestions) {
    showQuizResults(userQuizScore, totalQuestions);
  }
};

function showQuizResults(score, total) {
  const summaryBox = document.getElementById('quizScoreSummary');
  const percentEl = document.getElementById('quizScorePercentage');
  const titleEl = document.getElementById('quizScoreTitle');
  const descEl = document.getElementById('quizScoreDesc');

  if (!summaryBox || !percentEl) return;

  const percent = Math.round((score / total) * 100);
  percentEl.textContent = `${percent}%`;

  if (percent === 100) {
    titleEl.textContent = 'Flawless Architectural Mastery! 🏆';
    descEl.textContent = 'You nailed every single question. Outstanding engineering comprehension!';
    triggerConfetti();
  } else if (percent >= 66) {
    titleEl.textContent = 'Great Technical Intuition! 🚀';
    descEl.textContent = 'Strong understanding of the core takeaways and architectural trade-offs.';
    triggerConfetti();
  } else {
    titleEl.textContent = 'Good Effort! 💡';
    descEl.textContent = 'Review the deep-dive explanations above to master the material.';
  }

  summaryBox.style.display = 'flex';
  summaryBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

window.resetQuiz = function() {
  userQuizScore = 0;
  answeredCount = 0;

  document.querySelectorAll('.quiz-question-item').forEach(q => {
    const btns = q.querySelectorAll('.quiz-option-btn');
    btns.forEach(b => {
      b.disabled = false;
      b.classList.remove('correct', 'wrong');
    });
  });

  document.querySelectorAll('.quiz-explanation-box').forEach(el => {
    el.style.display = 'none';
  });

  const summaryBox = document.getElementById('quizScoreSummary');
  if (summaryBox) summaryBox.style.display = 'none';
};

window.triggerConfetti = function() {
  const canvas = document.createElement('canvas');
  canvas.style.position = 'fixed';
  canvas.style.top = '0';
  canvas.style.left = '0';
  canvas.style.width = '100vw';
  canvas.style.height = '100vh';
  canvas.style.zIndex = '9999';
  canvas.style.pointerEvents = 'none';
  document.body.appendChild(canvas);

  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const particles = [];
  const colors = ['#a855f7', '#ec4899', '#38bdf8', '#10b981', '#fbbf24', '#fb923c'];

  for (let i = 0; i < 90; i++) {
    particles.push({
      x: canvas.width / 2,
      y: canvas.height / 2,
      vx: (Math.random() - 0.5) * 16,
      vy: (Math.random() - 0.7) * 18,
      size: Math.random() * 8 + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      alpha: 1,
      rotation: Math.random() * 360,
      rotSpeed: (Math.random() - 0.5) * 10
    });
  }

  let startTime = Date.now();
  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let alive = false;

    particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.4; // gravity
      p.rotation += p.rotSpeed;
      p.alpha -= 0.012;

      if (p.alpha > 0) {
        alive = true;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rotation * Math.PI) / 180);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
        ctx.restore();
      }
    });

    if (alive && Date.now() - startTime < 3500) {
      requestAnimationFrame(animate);
    } else {
      canvas.remove();
    }
  }
  requestAnimationFrame(animate);
};

