// ASI TECH - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Mobile Menu Toggle
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navLinks = document.getElementById('navLinks');

    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', function() {
            navLinks.classList.toggle('active');
            const icon = mobileMenuBtn.querySelector('i');
            if (navLinks.classList.contains('active')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    }

    // Dropdown toggle for mobile
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('.dropdown-toggle');
        if (toggle) {
            toggle.addEventListener('click', function(e) {
                if (window.innerWidth <= 768) {
                    e.preventDefault();
                    dropdown.classList.toggle('active');
                }
            });
        }
    });

    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateX(100%)';
            setTimeout(() => flash.remove(), 400);
        }, 5000);
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId !== '#') {
                const target = document.querySelector(targetId);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });

    // Add animation on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe blog cards and category cards
    document.querySelectorAll('.blog-card, .category-card, .stat-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });

    // Search input focus effect
    const searchInputs = document.querySelectorAll('.search-form input, .search-big input');
    searchInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.style.transform = 'scale(1.02)';
        });
        input.addEventListener('blur', function() {
            this.parentElement.style.transform = 'scale(1)';
        });
    });

    // Logo hover effect
    const logo = document.querySelector('.logo');
    if (logo) {
        logo.addEventListener('mouseenter', function() {
            this.querySelector('.logo-icon').style.boxShadow = '0 0 30px rgba(16, 185, 129, 0.6)';
        });
        logo.addEventListener('mouseleave', function() {
            this.querySelector('.logo-icon').style.boxShadow = '0 0 20px rgba(16, 185, 129, 0.4)';
        });
    }

    // Review form character counter
    const reviewTextarea = document.querySelector('.review-form textarea[name="comment"]');
    if (reviewTextarea) {
        const maxLength = 1000;
        const counter = document.createElement('div');
        counter.style.cssText = 'text-align:right;color:#6ee7b7;font-size:12px;margin-top:5px;';
        counter.textContent = '0 / ' + maxLength + ' characters';
        reviewTextarea.parentElement.appendChild(counter);

        reviewTextarea.addEventListener('input', function() {
            const current = this.value.length;
            counter.textContent = current + ' / ' + maxLength + ' characters';
            if (current > maxLength) {
                counter.style.color = '#ef4444';
            } else {
                counter.style.color = '#6ee7b7';
            }
        });
    }

    // Admin form - Auto-generate slug from title
    const titleInput = document.querySelector('input[name="title"]');
    const slugInput = document.querySelector('input[name="slug"]');

    if (titleInput && slugInput && !slugInput.value) {
        titleInput.addEventListener('input', function() {
            const slug = this.value
                .toLowerCase()
                .replace(/[^a-z0-9\s-]/g, '')
                .replace(/\s+/g, '-')
                .replace(/-+/g, '-')
                .trim();
            slugInput.value = slug;
        });
    }

    // Image preview for admin form
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const fileName = this.files[0].name;
                const label = document.createElement('span');
                label.style.cssText = 'color:#34d399;font-size:12px;margin-left:10px;';
                label.textContent = '✓ ' + fileName;

                // Remove existing label
                const existing = this.parentElement.querySelector('span');
                if (existing) existing.remove();

                this.parentElement.appendChild(label);
            }
        });
    });

    // Parallax effect for hero
    const hero = document.querySelector('.hero');
    if (hero) {
        window.addEventListener('scroll', function() {
            const scrolled = window.pageYOffset;
            const heroContent = hero.querySelector('.hero-content');
            if (heroContent && scrolled < 600) {
                heroContent.style.transform = 'translateY(' + (scrolled * 0.3) + 'px)';
                heroContent.style.opacity = 1 - (scrolled / 600);
            }
        });
    }

    // Active nav link highlighting based on scroll
    const sections = document.querySelectorAll('section[id]');
    if (sections.length > 0) {
        window.addEventListener('scroll', function() {
            let current = '';
            sections.forEach(section => {
                const sectionTop = section.offsetTop;
                if (scrollY >= sectionTop - 200) {
                    current = section.getAttribute('id');
                }
            });
        });
    }

    console.log('🚀 ASI TECH website loaded successfully!');
});
