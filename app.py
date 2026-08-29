import os
import re
import sqlite3
import json
import urllib.request
import urllib.error
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'asi_tech_secret_key_2024_secure'

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "vape1098")
ADMIN_URL = "/admin-portal-secret"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))

DATABASE = os.path.join(BASE_DIR, 'blog.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def calculate_read_time(content):
    if not content:
        return 1
    text = re.sub(r'<[^>]+>', ' ', content)
    words = len(re.findall(r'\w+', text))
    return max(1, round(words / 180))

# ==============================================================================
# EASY BLOG WRITING SYNTAX PARSER
# ==============================================================================
def format_inline_styles(text):
    if not text:
        return ""
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<strong>\1</strong>', text)
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
    text = re.sub(r'\/\/(.+?)\/\/', r'<em>\1</em>', text)
    return text

def parse_content_syntax(content):
    if not content:
        return ""
    
    lines = content.split('\n')
    output = []
    in_code_block = False
    in_ul = False
    in_ol = False
    code_lines = []
    is_first_p = True

    for raw_line in lines:
        stripped = raw_line.strip()

        if stripped.startswith('```'):
            if in_code_block:
                in_code_block = False
                output.append(f'<pre><code>{"\n".join(code_lines)}</code></pre>')
                code_lines = []
            else:
                if in_ul:
                    output.append('</ul>')
                    in_ul = False
                if in_ol:
                    output.append('</ol>')
                    in_ol = False
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(raw_line)
            continue

        is_ul_item = stripped.startswith(('- ', '* '))
        is_ol_item = bool(re.match(r'^\d+\.\s', stripped))

        if not is_ul_item and in_ul:
            output.append('</ul>')
            in_ul = False
        if not is_ol_item and in_ol:
            output.append('</ol>')
            in_ol = False

        if not stripped:
            continue

        if stripped.startswith('### '):
            text = format_inline_styles(stripped[4:])
            output.append(f'<h3>{text}</h3>')
        elif stripped.startswith('#### '):
            text = format_inline_styles(stripped[5:])
            output.append(f'<h4>{text}</h4>')
        elif stripped.startswith('## '):
            text = format_inline_styles(stripped[3:])
            output.append(f'<h2>{text}</h2>')
        elif stripped.startswith('# '):
            text = format_inline_styles(stripped[2:])
            output.append(f'<h2>{text}</h2>')
        elif stripped.startswith('> '):
            text = format_inline_styles(stripped[2:])
            output.append(f'<blockquote>{text}</blockquote>')
        elif stripped.startswith('! '):
            text = format_inline_styles(stripped[2:])
            output.append(f'<div class="tech-highlight-box"><h4>💡 Key Takeaway</h4><p>{text}</p></div>')
        elif is_ul_item:
            if not in_ul:
                output.append('<ul>')
                in_ul = True
            text = format_inline_styles(stripped[2:])
            output.append(f'<li>{text}</li>')
        elif is_ol_item:
            if not in_ol:
                output.append('<ol>')
                in_ol = True
            item_text = re.sub(r'^\d+\.\s*', '', stripped)
            text = format_inline_styles(item_text)
            output.append(f'<li>{text}</li>')
        elif stripped.startswith('<') and stripped.endswith('>'):
            output.append(raw_line)
        else:
            text = format_inline_styles(stripped)
            if is_first_p:
                output.append(f'<p class="lead-paragraph">{text}</p>')
                is_first_p = False
            else:
                output.append(f'<p>{text}</p>')

    if in_code_block:
        output.append(f'<pre><code>{"\n".join(code_lines)}</code></pre>')
    if in_ul:
        output.append('</ul>')
    if in_ol:
        output.append('</ol>')

    return '\n'.join(output)

@app.template_filter('parse_content')
def parse_content_filter(content):
    return parse_content_syntax(content)

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS blogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                title_image TEXT,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                author TEXT DEFAULT 'ASI TECH',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                views INTEGER DEFAULT 0,
                tags TEXT DEFAULT '',
                read_time INTEGER DEFAULT 3,
                is_featured INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blog_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                rating INTEGER DEFAULT 5,
                comment TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (blog_id) REFERENCES blogs (id)
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS newsletter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                provider TEXT DEFAULT 'email',
                avatar TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS blog_reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blog_id INTEGER NOT NULL,
                reaction_type TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                UNIQUE(blog_id, reaction_type),
                FOREIGN KEY (blog_id) REFERENCES blogs (id)
            );
        """)
        
        cursor = db.cursor()
        existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(blogs)").fetchall()]
        if 'tags' not in existing_cols:
            cursor.execute("ALTER TABLE blogs ADD COLUMN tags TEXT DEFAULT ''")
        if 'read_time' not in existing_cols:
            cursor.execute("ALTER TABLE blogs ADD COLUMN read_time INTEGER DEFAULT 3")
        if 'is_featured' not in existing_cols:
            cursor.execute("ALTER TABLE blogs ADD COLUMN is_featured INTEGER DEFAULT 0")
        if 'likes' not in existing_cols:
            cursor.execute("ALTER TABLE blogs ADD COLUMN likes INTEGER DEFAULT 0")
        if 'eli5_content' not in existing_cols:
            cursor.execute("ALTER TABLE blogs ADD COLUMN eli5_content TEXT DEFAULT ''")

        cursor.execute("UPDATE blogs SET title_image = 'cover_deepseek_reasoning.svg' WHERE title_image = 'cover_ai_deepseek.svg' OR slug LIKE '%deepseek%'")
        cursor.execute("UPDATE blogs SET slug = 'deepseek-r1-claude-3-7-reasoning-llms-frontier' WHERE slug = 'deepseek-r1-claude-37-reasoning-llms-frontier'")
        db.commit()
        
        count = cursor.execute("SELECT COUNT(*) FROM blogs").fetchone()[0]
        has_empty_eli5 = cursor.execute("SELECT COUNT(*) FROM blogs WHERE eli5_content IS NULL OR eli5_content = ''").fetchone()[0]
        if count < 19 or has_empty_eli5 > 0:
            seed_rich_blogs(db)

def generate_eli5_fallback(title, content):
    """Dynamic fallback simplifier if an article lacks custom ELI5 content"""
    # Simple, high-level structured simplification
    text = re.sub(r'<[^>]+>', ' ', content)
    sentences = [s.strip() for s in re.split(r'[.!?]\s+', text) if len(s.strip()) > 20]
    lead = sentences[0] if sentences else "This technology is changing how we interact with modern science and computers."
    
    return f"""# 👶 Explain Like I'm 5: {title}

### 🎈 The Big Idea (In Simple Words)
{lead}

### 💡 3 Key Things to Remember
- **1. What is happening:** Engineers are solving really hard puzzles to make computers, gadgets, and scientific tools faster and safer.
- **2. Why it feels like magic:** Things that used to take days or whole teams can now happen automatically in the blink of an eye.
- **3. What changes for you:** Future apps, games, medicines, and gadgets will be dramatically smarter and more reliable.

> "Even the most complex rocket science can be understood when broken down into simple stepping stones!"

! **ELI5 Takeaway:** You don't need to be a math genius to appreciate this breakthrough — it's all about making the future easier and brighter for everyone."""

def seed_rich_blogs(db):
    db.execute("DELETE FROM blogs")
    db.execute("DELETE FROM reviews")

    blogs_data = [
        {
            "title": "DeepSeek-R1, Claude 3.7 Sonnet & Reasoning LLMs: The Cognitive Frontier",
            "slug": "deepseek-r1-claude-3-7-reasoning-llms-frontier",
            "title_image": "cover_deepseek_reasoning.svg",
            "category": "Artificial Intelligence",
            "author": "ASI TECH",
            "tags": "DeepSeek, Claude, Reasoning, Reinforcement Learning, LLMs",
            "read_time": 5,
            "is_featured": 1,
            "likes": 84,
            "views": 540,
            "content": """The artificial intelligence landscape has reached an inflection point with the emergence of reasoning models like DeepSeek-R1, OpenAI o3, and Claude 3.7 Sonnet.

# 1. The Power of Test-Time Compute & Long Chain-of-Thought
Traditional autoregressive transformers predict tokens in a single forward pass without thinking steps. Reasoning models introduce extensive reinforcement learning (RL) exploration:

- **Self-Correction:** The model detects logical fallacies mid-generation and backtracks dynamically.
- **Test-Time Compute Scaling:** Allocating more compute during inference exponentially improves complex mathematical and programming proofs.
- **Pure RL Emergence:** DeepSeek-R1 proved that reasoning capabilities can emerge directly from pure rule-based reinforcement learning without heavy supervised fine-tuning.

> "Reasoning models don't just calculate probabilities; they deliberate, verify hypotheses, and formulate structured solutions."

# 2. What this Means for Software Engineers & Researchers
Developers can now automate end-to-end system design, complex kernel optimization, and multi-file code refactoring with human-grade rigor.

! Mastering prompt chains, verification loops, and agentic tool invocation is the core differentiator for modern AI engineers.""",
            "eli5_content": """# 👶 Explain Like I'm 5: DeepSeek-R1 & AI Reasoning

### 🎈 The Kid-Friendly Analogy: The "Scratch Paper" Difference
Imagine an AI taking a difficult math test:
- **Old AI (Regular ChatGPT):** Like a student who shouts out the first guess that pops into their head in 1 second. Sometimes they get lucky, but for tough riddles, they make silly mistakes!
- **New Reasoning AI (DeepSeek-R1 & Claude 3.7):** Like a smart student who pulls out a piece of **scratch paper**. They write down step 1, notice they made an error, erase it, try a second route, double-check the work, and ONLY THEN give you the correct final answer.

---

### 💡 3 Key Things to Understand
- **1. It Can Change Its Mind:** If the AI realizes half-way through an answer that its math doesn't add up, it stops itself and backtracks to fix it.
- **2. Thinking Time Makes It Smarter:** Giving the AI 10 extra seconds to "think" in private turns it from a simple autocomplete toy into a genuine problem solver.
- **3. Learning by Practice (Pure RL):** DeepSeek-R1 taught itself how to solve math puzzles simply by playing against the rules over and over until it got really good!

---

### 🚀 Why This Matters to You
Instead of just writing poems and emails, AI can now write entire computer programs, help discover new medicine formulas, and solve college-level math puzzles with human-grade accuracy!

> "Old AI answered instantly and guessed. Reasoning AI stops, thinks on scratch paper, fixes its mistakes, and solves hard puzzles!" """
        },
        {
            "title": "The Rise of Quantum Computing & Next-Gen Neural Architectures",
            "slug": "rise-of-quantum-computing-and-next-gen-ai",
            "title_image": "cover_quantum_ai.svg",
            "category": "Artificial Intelligence",
            "author": "ASI TECH",
            "tags": "Quantum AI, Superposition, Qubits, Neural Networks",
            "read_time": 5,
            "is_featured": 1,
            "likes": 65,
            "views": 420,
            "content": """Quantum computing is no longer purely experimental. Today researchers are merging quantum entanglement with deep neural architectures to achieve logarithmic optimization speedups.

# 1. Why Quantum AI is Radically Faster
Standard silicon chips process binary bits (0 or 1). Quantum computers leverage **Qubits** capable of superposition:

- **Hilbert Space Mapping:** Mapping massive high-dimensional data vectors into complex quantum state distributions.
- **Parameterized Quantum Circuits (PQC):** Acting as variational layers optimized using quantum parameter-shift gradients.
- **Quadratic & Exponential Speedups:** Solving NP-hard combinatorial problems in fractions of a second.

> "Hybrid Quantum-Classical systems are already cracking molecular simulation and battery chemistry models."

# 2. Real-World Applications in 2026
From real-time cryptographic defense to global grid balancing and drug design, Quantum AI is reshaping computation fundamentals.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Quantum Computing & AI

### 🎈 The Kid-Friendly Analogy: The Spinning Coin
Think about normal computers vs Quantum computers:
- **Your Regular Computer (Bits):** Like a coin resting flat on a table. It is strictly **Heads (1)** or **Tails (0)**. To search a giant maze, it walks down path #1, hits a wall, comes back, and tries path #2 one by one.
- **A Quantum Computer (Qubits):** Like a coin **spinning at super-speed in mid-air**! While it's spinning, it is Heads AND Tails at the very same time (this is called *Superposition*). This lets the computer explore ALL paths in the maze simultaneously!

---

### 💡 3 Key Things to Understand
- **1. Qubits are Super-Particles:** They can be linked together like invisible walkie-talkies (called *Entanglement*), so changing one instantly affects the other.
- **2. Millions of Guesses in 1 Second:** It can solve problems in seconds that would take normal supercomputers thousands of years to calculate.
- **3. Hybrid Power:** Modern labs connect normal computers with quantum chips so each handles what it's best at.

---

### 🚀 Why This Matters to You
Quantum AI is helping scientists invent clean energy batteries that don't degrade, create brand new medical drugs that cure illnesses, and forecast weather patterns before natural disasters strike!

> "A regular computer tries one key in the door at a time. A quantum computer tries all one million keys at the exact same millisecond!" """
        },
        {
            "title": "Solid-State Batteries & 800V EV Architectures: The Energy Revolution",
            "slug": "solid-state-batteries-800v-ev-revolution",
            "title_image": "cover_solid_state_battery.svg",
            "category": "Technology",
            "author": "ASI TECH",
            "tags": "EV, Solid State, Batteries, Clean Energy, Engineering",
            "read_time": 4,
            "is_featured": 1,
            "likes": 52,
            "views": 390,
            "content": """The global transition to sustainable transportation hinges on one critical breakthrough: solid-state lithium-metal batteries and ultra-high voltage powertrains.

# The End of Range Anxiety: 1000km on a 10-Minute Charge
Traditional lithium-ion cells use volatile liquid electrolytes that degrade and pose thermal runaway risks. Solid-state technology replaces liquid electrolytes with ceramic or sulfide solid conductors:

- **1000 Wh/L Volumetric Energy Density:** Doubling the energy storage capacity in the exact same footprint.
- **800V & 900V Charging Rails:** Pumping 350kW to 480kW charging power safely with zero overheating.
- **Zero Dendrite Degradation:** Preserving over 90% battery capacity after 2,000+ continuous fast-charge cycles.

> "Solid-state cells mark the permanent tipping point where electric vehicles decisively surpass internal combustion in range, cost, and longevity."

! Silicon Valley and automotive giants in Germany and Japan are rolling out pilot commercial production lines this year.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Solid-State Batteries

### 🎈 The Kid-Friendly Analogy: Sloshing Juice vs. Solid Ice
- **Old Phone & Car Batteries:** Filled with a liquid chemical soup (like a squishy bag of juice). If it gets punctured or overheats, the liquid can leak or catch fire. Plus, it wears out after a couple of years.
- **Solid-State Batteries:** Replace all that liquid with a rock-solid piece of ceramic or glass (like an ice cube). Nothing leaks, nothing catches fire, and you can pack twice as much energy into the exact same space!

---

### 💡 3 Key Things to Understand
- **1. Double the Miles:** An electric car can travel 600 to 700 miles on one charge instead of 300 miles.
- **2. 10-Minute Lightning Charging:** Because solid batteries don't overheat easily, 800V chargers can fill them up in the time it takes to grab a cup of hot chocolate.
- **3. Fireproof Safety:** Even if you hammer a nail straight through the battery, it stays completely cool and safe.

---

### 🚀 Why This Matters to You
No more waiting hours to charge your phone or electric car, and no more batteries dying after 2 years of use!

> "Solid-state turns squishy liquid batteries into solid, fireproof powerhouses that charge in 10 minutes and last for decades." """
        },
        {
            "title": "Brain-Computer Interfaces: Human Clinical Trials & Neural Telemetry",
            "slug": "brain-computer-interfaces-neural-telemetry",
            "title_image": "cover_neural_bci.svg",
            "category": "Science",
            "author": "ASI TECH",
            "tags": "BCI, Neurotech, Neuralink, Biology, Medicine",
            "read_time": 5,
            "is_featured": 0,
            "likes": 71,
            "views": 480,
            "content": """Direct cortical communication between the human brain and external computers has crossed the threshold from science fiction to active clinical human trials.

# 1. How High-Density Neural Implants Function
Modern BCI devices like Neuralink's N1 utilize 1,024 ultra-flexible micro-threads distributed across 64 recording channels:

- **Action Potential Spike Sorting:** Dedicated on-chip ASICs detect and filter microvolt-level neural firing in real-time.
- **Wireless Inductive Telemetry:** Streaming bidirectional data and power through the scalp with zero transcutaneous wires.
- **Motor Cortex Intent Decoding:** Transforming motor thoughts into digital cursor movements, robotic limb control, and speech synthesis.

> "Patients with spinal cord injuries are now operating computers and typing messages at speeds comparable to able-bodied users."

# 2. Ethical Horizons and Future Augmentation
As electrode channel counts scale to 10,000+, BCIs will open doors to sensory restoration and cognitive co-processing.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Brain-Computer Interfaces (BCI)

### 🎈 The Kid-Friendly Analogy: A Tiny Microphone for Brain Whispers
Your brain is made of billions of tiny cells (neurons) that flash little electrical sparks whenever you think about moving your hand, singing a song, or playing a game.
- A **Brain-Computer Interface** is like placing a cluster of microscopic, hair-thin microphones next to those brain cells.
- When you just *imagine* moving your hand to the right, the computer hears the electric spark and moves your video game joystick or mouse cursor to the right—without you touching anything!

---

### 💡 3 Key Things to Understand
- **1. Invisible Wireless Telemetry:** The chip sits under the scalp and sends data via Bluetooth radio, so there are no wires hanging out of the head.
- **2. Restoring Freedom:** People who cannot walk or use their hands can now play video games, browse the web, and talk with loved ones using just their thoughts.
- **3. Robotic Limbs:** In the future, this will let bionic prosthetic arms move naturally as if they were real biological limbs.

---

### 🚀 Why This Matters to You
It is giving back mobility and voice to millions of people with paralyzed limbs or neurological conditions.

> "You think: 'Move cursor left.' The micro-chip hears the electrical whisper and moves the cursor instantly!" """
        },
        {
            "title": "Rust vs Zig vs Mojo: The Battle for High-Performance Systems & AI Workloads",
            "slug": "rust-vs-zig-vs-mojo-high-performance-systems",
            "title_image": "cover_rust_systems.svg",
            "category": "Technology",
            "author": "ASI TECH",
            "tags": "Rust, Zig, Mojo, Systems Programming, Performance",
            "read_time": 6,
            "is_featured": 0,
            "likes": 64,
            "views": 380,
            "content": """As AI models and microservices demand extreme efficiency, the programming language landscape is seeing intense competition between Rust, Zig, and Mojo.

# 1. The Contenders Broken Down

### Rust: The Champion of Memory Safety
- Compile-time borrow checker guarantees zero data races and zero memory leaks without a garbage collector.
- The standard choice for operating system kernels (Linux, Windows) and high-throughput networking proxies.

### Zig: Simplicity & Direct C Interop
- Zero hidden control flow, no macros, and compile-time execution with `comptime`.
- Instant drop-in replacement C/C++ compiler with incredible build performance.

### Mojo: Python Syntax with C++ Speed
- Built on top of MLIR (Multi-Level Intermediate Representation) designed specifically for AI hardware parallelism.
- Allows AI engineers to write high-level Python code that compiles directly to vector SIMD instructions.

! The future of backend and AI engineering belongs to developers who understand hardware memory models.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Rust vs Zig vs Mojo

### 🎈 The Kid-Friendly Analogy: 3 Kinds of Supercars
Programming languages are the tools humans use to tell computers what to do. Here is how the top 3 modern languages compare:
- 🦀 **Rust (The Armored Tank):** Comes with a built-in strict teacher (the *Borrow Checker*). If there is even the tiniest chance your code might crash or leak memory, Rust refuses to start until you fix it. It is virtually uncrashable!
- ⚡ **Zig (The Lightweight Go-Kart):** Has no hidden tricks, no secret gears. Every single screw is visible and simple. It builds in 1 second and never surprises you.
- 🔥 **Mojo (The AI Rocket):** Looks as friendly and easy to write as Python (the language kids learn in school), but underneath it runs as fast as supercomputer C++ to crunch AI graphics!

---

### 💡 3 Key Things to Understand
- **1. No More Blue Screen of Death:** Rust stops 70% of all computer security bugs before the program even runs.
- **2. Clean & Simple:** Zig replaces messy 40-year-old code with crystal-clear commands.
- **3. AI at Warp Speed:** Mojo lets AI creators write simple code that uses all the cores of high-tech graphics cards automatically.

---

### 🚀 Why This Matters to You
Faster apps, websites that never crash, and AI tools that run directly on your laptop without lagging!

> "Rust gives you unbreakable safety, Zig gives you pure simplicity, and Mojo gives Python supersonic AI speed." """
        },
        {
            "title": "Generative Video & Real-Time CGI: Inside OpenAI Sora & DiT Neural Rendering",
            "slug": "generative-video-sora-dit-cinema-revolution",
            "title_image": "cover_sora_cinema.svg",
            "category": "Movies",
            "author": "ASI TECH",
            "tags": "Sora, Generative AI, Cinema, VFX, Video Generation",
            "read_time": 5,
            "is_featured": 0,
            "likes": 58,
            "views": 440,
            "content": """The launch of high-fidelity generative video systems like OpenAI Sora and Runway Gen-3 has revolutionized filmmaking, pre-visualization, and virtual production.

# How Spatio-Temporal Diffusion Transformers (DiT) Work
Rather than processing individual 2D image frames sequentially, Sora treats videos as collections of 3D spacetime patches:

- **Spacetime Patch Tokenization:** Compressing videos into low-dimensional latent patches that act like words in an LLM.
- **Diffusion Transformer Scaling:** Predictor transformers denoise clean video patches conditioned on text prompts and camera trajectories.
- **Physics World Modeling:** The neural network implicitly learns 3D consistency, reflections, and fluid dynamics from massive video training corpuses.

> "Directors can now generate complex photorealistic establishing shots and lighting simulations in minutes instead of months."

# The Convergence with Unreal Engine 5.5
Studios are combining generative video backdrops with real-time in-camera LED volumes for hybrid filmmaking.""",
            "eli5_content": """# 👶 Explain Like I'm 5: OpenAI Sora & AI Movie Making

### 🎈 The Kid-Friendly Analogy: Dreaming Up a 3D World
- **Old Animation:** An artist had to draw 24 separate pictures for every single second of cartoon video, making sure the character was in the right place.
- **OpenAI Sora:** Like an AI that builds a complete, living, 3D toy world inside its imagination. It understands that when a car drives in rain, water must splash on the wheels, and headlights must reflect on wet puddles. Then it points a virtual camera at it and films high-definition video!

---

### 💡 3 Key Things to Understand
- **1. 3D Lego Patches:** It breaks video into tiny spacetime cubes (like digital Lego blocks) and arranges them smoothly.
- **2. Learns Real Physics:** The AI learned by watching millions of videos, so it naturally knows how gravity pulls balls down and how cloth waves in the wind.
- **3. Hollywood in Your Bedroom:** An indie filmmaker can describe a scene ("A golden retriever astronaut on Mars") and have a movie-ready clip in 60 seconds.

---

### 🚀 Why This Matters to You
Soon, anyone with a great imagination will be able to create their own full-length animated movies and video games with zero budget!

> "Instead of drawing frame-by-frame, Sora imagines a living 3D world with real physics and records it on demand." """
        },
        {
            "title": "Post-Quantum Cryptography: Protecting Global Networks from Quantum Decryption",
            "slug": "post-quantum-cryptography-protecting-networks",
            "title_image": "cover_post_quantum_crypto.svg",
            "category": "Science",
            "author": "ASI TECH",
            "tags": "Cryptography, Security, Quantum, NIST, Cybersecurity",
            "read_time": 5,
            "is_featured": 0,
            "likes": 49,
            "views": 310,
            "content": """When fault-tolerant quantum computers arrive, Shor's algorithm will break RSA and Elliptic Curve Cryptography (ECC) in seconds. The transition to Post-Quantum Cryptography (PQC) is urgent.

# The New NIST Post-Quantum Standards

### 1. ML-KEM (Formerly CRYSTALS-Kyber)
- Based on Module Learning with Errors (MLWE) over structured polynomial lattices.
- Fast key encapsulation mechanism for HTTPS, TLS 1.3, and VPN encryption.

### 2. ML-DSA (Formerly CRYSTALS-Dilithium)
- Lattice-based digital signature algorithm guaranteeing document and code signing integrity.

### 3. SLH-DSA (SPHINCS+)
- Stateless hash-based signatures providing a fail-safe backup against lattice cryptanalysis.

! Every enterprise and cloud provider is currently migrating TLS cipher suites to hybrid classical-PQC algorithms.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Post-Quantum Cryptography

### 🎈 The Kid-Friendly Analogy: Upgrading the World's Door Locks
- **Current Internet Security (RSA Locks):** Imagine the password on your bank or email is locked inside a math puzzle based on multiplying two giant prime numbers. A normal computer would take 10,000 years to guess the answer.
- **The Quantum Problem:** A future Quantum computer could crack that lock in 3 seconds flat (like having a magic master key).
- **Post-Quantum Cryptography:** Replacing those prime number locks with crazy 500-dimensional geometrical crystal mazes (*Lattices*) that even super-quantum computers cannot solve!

---

### 💡 3 Key Things to Understand
- **1. Preparing in Advance:** Even though giant quantum hacker computers aren't here yet, we are upgrading the locks today so past secrets stay safe forever.
- **2. New Global Standards:** Scientists tested hundreds of unbreakable math puzzles and chose the best ones (ML-KEM and ML-DSA).
- **3. Invisible Shield:** Your browser updates in the background automatically so you stay 100% protected without doing any work.

---

### 🚀 Why This Matters to You
It guarantees that your bank accounts, hospital medical records, and private chat messages remain permanently safe from future quantum hackers!

> "We are changing the internet's math locks to multi-dimensional crystal puzzles that quantum computers cannot crack." """
        },
        {
            "title": "The Complete 2026 Full-Stack AI Engineer Roadmap",
            "slug": "complete-2026-full-stack-ai-engineer-roadmap",
            "title_image": "cover_education_code.svg",
            "category": "Education",
            "author": "ASI TECH",
            "tags": "Roadmap, AI Engineering, FullStack, Career, PyTorch",
            "read_time": 6,
            "is_featured": 0,
            "likes": 77,
            "views": 590,
            "content": """The role of software developers is transforming into Full-Stack AI Engineering. Here is the step-by-step roadmap to master modern AI application development.

# 1. Foundation: Python, Vector Math & PyTorch
- Grasp tensor manipulations, broadcasting, and GPU CUDA memory allocation.
- Build transformer attention blocks from scratch to deeply understand Q, K, V matrix projections.

# 2. Modern Agentic Architectures
- Orchestrate multi-agent workflows with tool use, function calling, and structured JSON outputs.
- Implement advanced retrieval strategies: Hybrid sparse/dense search, ColBERT, and Graph RAG.

# 3. Production Deployment & LLMOps
- Master vLLM, TensorRT-LLM, and quantization techniques (AWQ, FP8, Int4).
- Setup automated evaluations, prompt regression testing, and semantic caching.

> "The best AI engineers don't just prompt models; they build robust, resilient distributed software around them." """,
            "eli5_content": """# 👶 Explain Like I'm 5: The 2026 AI Engineer Roadmap

### 🎈 The Kid-Friendly Analogy: From Chatting to Robot Team Captain
- In 2023, people thought being an AI engineer was just asking ChatGPT good questions.
- In 2026, an AI Engineer is like the **Captain and General Contractor of a team of super-smart robots**. You teach them how to search your company's private library, give them tools (like calculators, web browsers, and terminal consoles), and verify their work before it ships!

---

### 💡 4 Easy Steps on the Roadmap
- **Step 1 (Math & Code):** Learn Python and understand how numbers are arranged into grids (tensors) that GPUs love.
- **Step 2 (RAG & Memory):** Connect the AI to custom databases so it never forgets your documents.
- **Step 3 (Agent Teams):** Make multiple AI bots collaborate (one writes, one checks, one deploys).
- **Step 4 (Speed & Efficiency):** Squeeze giant AI models into lightweight files that run super-fast and cheaply.

---

### 🚀 Why This Matters to You
AI engineering is the highest-demand career skill in the world right now—turning ideas into working software faster than ever before.

> "An AI engineer doesn't just chat with AI—they build the entire electrical grid and software team around it!" """
        },
        {
            "title": "Next-Gen Web Architecture: Edge SSR, Island Architecture & Microfrontends",
            "slug": "next-gen-web-architecture-edge-ssr-islands",
            "title_image": "cover_web_tech.svg",
            "category": "Technology",
            "author": "ASI TECH",
            "tags": "WebDev, Edge Computing, Performance, Architecture",
            "read_time": 4,
            "is_featured": 0,
            "likes": 44,
            "views": 330,
            "content": """Building high-speed web apps requires balancing client interactivity with instant First Contentful Paint. Island architectures are replacing monolithic JS bundles.

# The 3 Pillars of Edge-Native Web:
- **Zero-JS by Default:** Render pages as static HTML and only hydrate interactive widgets ("islands").
- **Global Edge Compute:** Run serverless workers across 300+ global points of presence.
- **Streaming SSR:** Stream HTML chunks using HTTP/2 chunked transfer encoding.

> "Performance is not just a metric; it directly drives user retention and search rankings." """,
            "eli5_content": """# 👶 Explain Like I'm 5: Modern Fast Websites & Islands

### 🎈 The Kid-Friendly Analogy: A Lightweight Flyer vs. A Heavy Backpack
- **Old Heavy Websites:** When you tap a link, your phone has to download a huge 50-pound backpack filled with heavy JavaScript machinery before it can even show you one sentence on screen. That's why pages feel slow and laggy on bad Wi-Fi!
- **Island Architecture:** The website sends you an ultra-lightweight printed newspaper page that opens in **0.1 seconds**. Then, it only drops tiny interactive batteries onto the specific buttons you actually want to click (like the search bar or audio player). Those buttons are the "Islands"!

---

### 💡 3 Key Things to Understand
- **1. Instant First View:** The text and pictures appear right away without spinning loading wheels.
- **2. Edge Servers:** The web page is sent to you from a server located in your own city, not on the other side of the planet.
- **3. Battery Saver:** Your phone doesn't heat up or waste battery calculating useless background code.

---

### 🚀 Why This Matters to You
Websites load in the blink of an eye, even when you're on a subway or spotty cellular connection!

> "Send plain, beautiful text immediately; only add code to the interactive islands you actually tap!" """
        },
        {
            "title": "The Science of Dark Matter and the James Webb Space Telescope Discoveries",
            "slug": "science-of-dark-matter-jwst-discoveries",
            "title_image": "cover_science_space.svg",
            "category": "Science",
            "author": "ASI TECH",
            "tags": "Space, Astrophysics, JWST, Cosmos",
            "read_time": 6,
            "is_featured": 0,
            "likes": 62,
            "views": 460,
            "content": """The James Webb Space Telescope (JWST) continues to reveal unprecedented details of early cosmic dawn just 300 million years after the Big Bang.

# The Mystery of Early Massive Galaxies
JWST's NIRCam captured galaxies whose immense stellar masses challenge standard cosmological models:

- **Primordial Black Hole Seeds:** Direct collapse black holes forming supermassive cores in record time.
- **Self-Interacting Dark Matter (SIDM):** Exploring alternatives to traditional cold dark matter models.
- **Exoplanet Atmospheres:** Detecting organic carbon signatures and water vapor on Trappist-1 system exoplanets.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Dark Matter & The James Webb Telescope

### 🎈 The Kid-Friendly Analogy: Cosmic Night-Vision Goggles
- Looking into deep space with old telescopes was like peering through dark, dusty curtains.
- The **James Webb Space Telescope (JWST)** has giant gold mirrors that act like high-tech infrared night-vision goggles in space. Because light takes time to travel across space, looking far away is literally like looking back in time to see what baby galaxies looked like when the universe was only a toddler!

---

### 💡 3 Key Things to Understand
- **1. Galaxies Grew Faster Than We Thought:** JWST spotted huge, glowing monster galaxies that formed almost immediately after the Big Bang!
- **2. The Invisible Glue (Dark Matter):** 85% of all matter in space is invisible "Dark Matter" that holds galaxies together like invisible cosmic glue.
- **3. Water on Distant Worlds:** JWST can sniff out the air of planets orbiting other stars and found clouds and water vapor!

---

### 🚀 Why This Matters to You
It is answering humanity's biggest questions: Where did we come from, how did stars form, and are we alone in the universe?

> "JWST is a cosmic time machine that peers 13 billion years into the past to watch the first stars switch on." """
        },
        {
            "title": "Cinematic Evolution: Real-Time Unreal Engine 5.5 Virtual Production",
            "slug": "cinematic-evolution-unreal-engine-virtual-production",
            "title_image": "cover_movies_cinema.svg",
            "category": "Movies",
            "author": "ASI TECH",
            "tags": "Cinema, Unreal Engine, Virtual Production, CGI, VFX",
            "read_time": 5,
            "is_featured": 0,
            "likes": 51,
            "views": 370,
            "content": """From massive LED volume walls to neural rendering, the boundary between physical film sets and digital worlds has dissolved.

# StageCraft & In-Camera Visual Effects (ICVFX)
With real-time camera tracking and Unreal Engine 5.5's Nanite geometry and Lumen dynamic lighting:

- **Zero Green Spill:** Real physical lighting from LED panels illuminates actors realistically.
- **Parallax Accuracy:** As the physical camera tracks across the studio, the background renders the exact correct 3D perspective in real-time.
- **Instant Director Iterations:** Change lighting, environment, and weather on set in seconds.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Virtual Production & Unreal Engine

### 🎈 The Kid-Friendly Analogy: Giant Living Wallpapers for Movies
- **Old Movies (Green Screen):** Actors had to stand in an awkward lime-green room, pretend to see an alien dragon, and look foolish. Then computer artists had to spend 6 months painting the background in post-production.
- **Modern Virtual Production:** The studio walls and ceiling are giant 360-degree high-definition video screens powered by Unreal Engine (the video game engine behind Fortnite). As the camera moves, the alien mountain landscape on the wall moves with perfect 3D perspective!

---

### 💡 3 Key Things to Understand
- **1. Real Light on Real Faces:** The glowing sunset on the LED screen naturally lights up the actor's face and clothes with zero green reflections.
- **2. Change Sunset with One Click:** If the director wants the scene to happen at midnight instead of noon, they just move a digital slider and the whole room turns into nighttime instantly.
- **3. Finished in the Camera:** What you see through the camera viewfinder is the final movie shot!

---

### 🚀 Why This Matters to You
Movies like *The Mandalorian* and superhero films look much more realistic and can be filmed in half the time!

> "No more fake green screens—actors now stand inside a living video game world that reacts in real-time!" """
        },
        {
            "title": "The Autonomous Agent Revolution: Multi-Agent Systems in Practice",
            "slug": "autonomous-agent-revolution-multi-agent-systems",
            "title_image": "cover_ai_agents.svg",
            "category": "Artificial Intelligence",
            "author": "ASI TECH",
            "tags": "AI Agents, LLM, Autonomy, Python",
            "read_time": 4,
            "is_featured": 0,
            "likes": 68,
            "views": 490,
            "content": """Language models are transitioning from static chat assistants to autonomous multi-agent teams that coordinate to execute complex engineering tasks.

# How Multi-Agent Collaboration Works
- **Planner Agent:** Deconstructs user objectives into a directed graph of actionable steps.
- **Executor Agent:** Executes terminal commands, calls external APIs, and edits repository code.
- **Verifier Agent:** Runs automated unit tests and validates results before sign-off.

! Multi-agent swarms will automate routine operations and software maintenance at enterprise scale.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Multi-Agent AI Swarms

### 🎈 The Kid-Friendly Analogy: A Mini Company Inside Your Laptop
Instead of asking one single AI to do everything, Multi-Agent systems work like a whole team of specialized coworkers:
- 📋 **The Architect / Boss Agent:** Reads your request, breaks it down into 5 small tasks, and hands them out.
- 💻 **The Coder / Worker Agent:** Writes the computer code and does the heavy lifting.
- 🧪 **The Inspector / QA Agent:** Tests the code, spots any bugs or mistakes, and sends it back to the worker until it's 100% perfect!

---

### 💡 3 Key Things to Understand
- **1. Teamwork Beats Solo:** AI bots that review and critique each other make 90% fewer mistakes than a single bot working alone.
- **2. Real Tool Usage:** They can open browsers, calculate statistics, edit files, and run tests by themselves.
- **3. Autonomous Progress:** You give them a big goal ("Build a weather dashboard"), and they work together until it's completely finished.

---

### 🚀 Why This Matters to You
Routine computer tasks, bug fixes, data analysis, and scheduling can run automatically in the background while you sleep!

> "One AI is a smart helper. A swarm of AI agents is a full-fledged company working together to finish big projects." """
        },
        {
            "title": "Apple Intelligence, M4 Max & M5 Silicon: The On-Device Privacy & Unified Memory Breakthrough",
            "slug": "apple-intelligence-m4-chips-unified-memory-architecture",
            "title_image": "cover_apple_intelligence.svg",
            "category": "Technology",
            "author": "ASI TECH",
            "tags": "Apple, Apple Intelligence, M4 Max, Apple Silicon, Privacy, Neural Engine, macOS",
            "read_time": 6,
            "is_featured": 1,
            "likes": 89,
            "views": 610,
            "content": """Apple's transition from traditional cloud-dependent assistants to on-device neural processing represents a watershed moment for consumer AI and hardware architecture.

# 1. 3nm Apple Silicon & The Unified Memory Advantage
Traditional PCs separate CPU system memory from discrete GPU VRAM, requiring slow PCIe bus transfers when loading multi-gigabyte neural weights. Apple's M4, M4 Pro, and M4 Max architecture shatters this bottleneck:

- **Up to 546 GB/s Memory Bandwidth:** Enabling instantaneous context switching and high-throughput token generation for 3B and 7B parameter models.
- **Unified Memory Architecture (UMA):** CPU, GPU, and the 16-core Neural Engine share a single zero-copy memory pool up to 128GB on laptops.
- **Dynamic Caching:** Hardware allocates local memory dynamically in real-time based on exact shader demands, dramatically improving GPU utilization.

> "By removing the PCIe transfer overhead, Apple Silicon can run quantized 70B parameter models locally on high-end configurations that would otherwise require multiple server-grade enterprise GPUs."

# 2. Apple Intelligence: Dual-Tier Architecture & Private Cloud Compute
Apple Intelligence introduces an elegant split-inference framework:

### 1. On-Device Foundation Models
- **3-Billion Parameter On-Device Model:** Quantized with 3.5-bit precision using mixed 2-bit/4-bit palletization, fitting comfortably in ~1.8GB of RAM with zero noticeable battery drain.
- **Adapter LoRA Fine-Tuning:** Dynamic adapter modules swap weights in milliseconds depending on whether the user is summarizing an email, composing text, or generating Genmoji.

### 2. Private Cloud Compute (PCC)
For complex multi-step reasoning, queries route to Private Cloud Compute nodes built entirely on custom Apple Silicon servers running a stripped-down, cryptographically verifiable OS.

! Private Cloud Compute enforces non-targetable hardware security: customer data is never retained, logs are cryptographically sealed, and independent security researchers can inspect and verify every server build.

# 3. The Semantic Index & App Intents
Through the macOS and iOS Semantic Index, Apple Intelligence analyzes personal context across Messages, Calendar, Photos, and Notes without sending any private telemetry off the device.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Apple Intelligence & M4 Chips

### 🎈 The Kid-Friendly Analogy: A Personal Genius Inside a Titanium Vault
- **Old Cloud AI:** Like shouting your diary secrets across the playground to a helper standing far away, hoping nobody eavesdrops on the way.
- **Apple Intelligence:** Like having a super-smart robot assistant living directly **inside your pocket**. It has its own private study desk (the Neural Engine) and keeps your secrets locked inside an unbreakable titanium vault. If it ever needs to ask a giant supercomputer for help, it encrypts the question in invisible ink that vanishes the second the answer is solved!

---

### 💡 3 Key Things to Understand
- **1. Zero-Copy Unified Memory:** The brain (CPU), the artist (GPU), and the AI chip (Neural Engine) share one giant snack table of RAM so they never waste time passing bowls back and forth.
- **2. Total Privacy Guarantee:** Your photos, emails, and private text messages are processed right on your phone without ever being sent to big data centers or saved by tech companies.
- **3. Adapters on the Fly:** The AI changes hats instantly—one second it's a grammar teacher, the next second it's an artist drawing custom emojis!

---

### 🚀 Why This Matters to You
Your phone and laptop can organize your day, rewrite notes, and find lost photos in seconds—without your private data ever leaving your hands!

> "Apple Intelligence puts an AI lab in your pocket while locking the door against anyone trying to snoop on your data." """
        },
        {
            "title": "Samsung Galaxy S25 Ultra & Galaxy AI 2.0: Inside the Multimodal Mobile AI War",
            "slug": "samsung-galaxy-s25-ultra-galaxy-ai-breakthroughs",
            "title_image": "cover_samsung_galaxy_ai.svg",
            "category": "Technology",
            "author": "ASI TECH",
            "tags": "Samsung, Galaxy S25, Galaxy AI, Snapdragon 8 Elite, Android, ISOCELL, NPU",
            "read_time": 5,
            "is_featured": 1,
            "likes": 81,
            "views": 570,
            "content": """The launch of the Samsung Galaxy S25 Ultra powered by Qualcomm's Snapdragon 8 Elite marks an aggressive leap into multimodal on-device agency and next-generation mobile silicon.

# 1. Snapdragon 8 Elite & Oryon CPU Microarchitecture
Samsung's flagship departs from standard ARM big.LITTLE clusters, utilizing custom Qualcomm Oryon cores built on TSMC's 3nm N3E node:

- **Dual Prime Cores @ 4.32 GHz:** Delivering desktop-class single-thread execution speeds with 24MB total L2 cache.
- **Hexagon Neural Processing Unit (NPU):** 45% faster AI throughput, handling multi-token speculation and real-time on-device audio transcription.
- **Adreno 830 GPU:** Featuring sliced architecture with dedicated command processors and hardware-accelerated Nanite mesh shading.

> "The Galaxy S25 Ultra closes the raw performance gap with custom silicon, delivering unthrottled continuous compute under heavy gaming and local AI workloads."

# 2. Galaxy AI 2.0: Cross-App Agents & Multimodal Context
Galaxy AI expands beyond basic photo erasing into proactive multimodal operating system workflows:

### Now Briefing & Smart Context
- Aggregates real-time notifications, flight status, transit delays, and calendar events into personalized contextual summaries.
- Analyzes on-screen video content dynamically to extract action items, calendar bookings, and shopping sources with a single stylus gesture.

### Live Call Translation & AI Voice Isolation
- Bi-directional neural voice translation running locally at 16kHz across 20+ languages with zero audio delay.
- Deep neural filtering isolates vocal harmonics from wind, cafe chatter, and traffic noise.

# 3. 200MP ISOCELL & ProVisual AI Neural Engine
Samsung integrates deep neural ISP pipelines directly with the 200MP HP2 sensor:
- **AI Deep Learning Deblur:** Eliminates hand jitter in low-light zoom shots.
- **Quad Tele System:** Optical-grade stabilization across 3x, 5x, and 10x periscope focal lengths using generative detail synthesis.

! With Knox Matrix and decentralized blockchain credential verification, Galaxy devices sync biometric encryption keys peer-to-peer across watches, TVs, and tablets safely.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Samsung Galaxy S25 Ultra & Galaxy AI

### 🎈 The Kid-Friendly Analogy: The Pocket Universal Translator & Magic Camera
- Imagine traveling to a foreign country where you don't speak the language.
- With **Galaxy AI 2.0**, you call a local restaurant on your phone, speak in English, and the phone automatically speaks fluent French or Japanese to the waiter, while translating their response back into your ear in real-time!

---

### 💡 3 Key Things to Understand
- **1. Supercharged Snapdragon 8 Elite Engine:** A high-speed chip that runs games and apps without ever getting hot or stuttering.
- **2. ProVisual Magic Camera:** Even if your hands shake while taking a photo of the moon or a soccer player far away, the 200-megapixel AI camera sharpens the picture crystal clear.
- **3. Knox Matrix Shield:** Protects your passwords and thumbprints across your phone, tablet, and smart TV so hackers cannot break in.

---

### 🚀 Why This Matters to You
You get movie-grade photos, instant multi-language translation, and a super-fast battery that lasts all day!

> "Galaxy S25 Ultra turns your smartphone into a multilingual translator, pro movie camera, and pocket supercomputer all in one." """
        },
        {
            "title": "Apple Vision Pro & Spatial Computing: Micro-OLEDs, visionOS & Spatial Audio Telepresence",
            "slug": "apple-vision-pro-spatial-computing-visionos-future",
            "title_image": "cover_apple_vision_pro.svg",
            "category": "Technology",
            "author": "ASI TECH",
            "tags": "Apple, Vision Pro, Spatial Computing, visionOS, Micro-OLED, R1 Chip, AR",
            "read_time": 5,
            "is_featured": 0,
            "likes": 74,
            "views": 510,
            "content": """Spatial computing represents the next foundational human-computer interface after the command line, graphical desktop, and smartphone touchscreen.

# 1. Display Optics & The 23-Million Pixel Array
The core visual magic of the Apple Vision Pro lies in its custom display pipeline:

- **Twin 4K Micro-OLED Displays:** Packing 23 million pixels across two postage-stamp sized silicon backplanes—rendering more pixels per eye than a 4K TV.
- **Custom Three-Element Catadioptric Lenses:** Delivering edge-to-edge sharpness with zero chromatic aberration.
- **Dynamic Foveated Rendering:** High-speed infrared cameras track eye gaze at 90Hz, rendering maximum pixel detail only where the fovea looks while reducing peripheral rendering load.

> "Spatial computing frees digital windows from physical display bezels, allowing users to arrange infinite workspaces in 3D physical space."

# 2. Dual-Chip Silicon Architecture: M2 + R1
To eliminate motion sickness and achieve instantaneous visual pass-through:
- **Apple M2:** Handles visionOS compute, physics simulation, spatial audio acoustics, and application execution.
- **Apple R1 Sensor Sub-Processor:** Processes feeds from 12 cameras, 5 sensors, and 6 microphones with a groundbreaking **12-millisecond latency**—8x faster than the blink of an eye.

# 3. Spatial Audio Ray Tracing & Volumetric Apps
visionOS maps the physical geometry and acoustic materials of the room using LiDAR and TrueDepth sensors, bouncing virtual sound waves off real walls for photorealistic acoustic telepresence.

! Developing for visionOS with SwiftUI and RealityKit unlocks volumetric 3D models, immersive portal rendering, and collaborative spatial FaceTime sessions.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Apple Vision Pro & Spatial Computing

### 🎈 The Kid-Friendly Analogy: Turning Your Living Room into a Holodeck
- When you look at an iPad or TV, your video games and movies are trapped inside a glass rectangle box.
- **Spatial Computing** removes the glass box completely! You put on lightweight glasses, and your living room wall transforms into a giant 100-foot IMAX cinema screen, while 3D dinosaurs and floating computer monitors hover naturally in the air right next to your sofa!

---

### 💡 3 Key Things to Understand
- **1. Microscopic 4K Screens:** Each tiny lens in front of your eyes has more pixels than a giant living-room 4K TV, so text looks as crisp as a printed book.
- **2. Controlled by Eyes and Fingers:** You just look at a button and gently pinch your thumb and index finger together—no bulky plastic game controllers needed!
- **3. 12-Millisecond R1 Speed:** What you see matches reality in 0.012 seconds, so your brain feels 100% natural without any dizzy feelings.

---

### 🚀 Why This Matters to You
You can watch 3D movies, build 3D models with friends across the globe, and have infinite computer screens wherever you sit!

> "Spatial computing turns any room into an infinite workspace and 3D movie theater controlled simply by your eyes and fingers." """
        },
        {
            "title": "Samsung Tri-Fold & Flexible AMOLED Tech: The Next Decade of Foldable Engineering",
            "slug": "samsung-trifold-foldable-displays-utg-engineering",
            "title_image": "cover_samsung_foldable_tech.svg",
            "category": "Technology",
            "author": "ASI TECH",
            "tags": "Samsung, Foldables, Tri-Fold, AMOLED, Display Tech, Ultra Thin Glass, Hardware",
            "read_time": 5,
            "is_featured": 0,
            "likes": 69,
            "views": 470,
            "content": """Foldable displays have evolved from experimental novelty to mainstream durable flagships. Samsung's multi-fold and Tri-Fold engineering push flexible screen physics to new frontiers.

# 1. The Physics of Flexible OLED & UTG 3.0
Creating a display that can flex hundreds of thousands of times requires advanced materials science:

- **Ultra-Thin Glass (UTG):** Processed at thicknesses under 30 microns, flexible glass combines the scratch resistance and visual clarity of glass with polymer flexibility.
- **CoE (Color on Encapsulation) Polarizer-Free Layers:** Eliminates traditional thick polarizing films, boosting display brightness by 20% while reducing power consumption by 25%.
- **Shock-Absorbing Elastic Under-Layers:** Disperses external kinetic impacts and drops across the entire surface area.

> "A tri-folding device bridges the form factor gap: compact 6.5-inch phone in your pocket that unfolds into a full 10.2-inch productivity workstation."

# 2. Dual Waterdrop Hinge Mechanics
The mechanical heart of a Tri-Fold device is its synchronized dual-hinge system:
- **Zero-Gap Teardrop Radii:** Gently curves the display into a teardrop shape when closed, minimizing mechanical strain at the crease fold lines.
- **Armor Aluminum & Titanium Housings:** Protects internal gears against micro-dust and particle ingress with IP48 sweeper bristles.
- **500,000 Fold Durability Rating:** Validated for over 10 years of intensive daily opening and closing cycles.

# 3. One UI Multi-Window Continuity
Software adaptation is vital for asymmetric and tri-folding screens:
- Seamless app continuity transitions from single-screen to dual-pane and triple-column multitasking.
- Split keyboard configurations and integrated S-Pen digitizers turn the unfolded canvas into a mobile digital drafting studio.

! Flexible display innovations will soon power rollable laptops, wearable wrist screens, and smart automotive panoramic cockpits.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Samsung Tri-Fold & Flexible Displays

### 🎈 The Kid-Friendly Analogy: The Origami Transformer Phone
- Think of normal phones like a stiff wooden postcard that never bends.
- **Samsung Tri-Fold:** Like a high-tech origami comic book made of bendable glass! You can fold it once to check a quick text message, or unfold it twice to reveal a giant 10-inch movie tablet for watching videos or drawing!

---

### 💡 3 Key Things to Understand
- **1. Flexible Glass (UTG):** It uses glass that is thinner than a strand of hair, so it can bend like rubber without shattering.
- **2. Waterdrop Hinges:** Hidden gears fold the screen gently so it leaves zero creases when you open it up flat.
- **3. Triple-Screen Multitasking:** You can run YouTube on one panel, take notes on the second panel, and chat with friends on the third panel at the exact same time!

---

### 🚀 Why This Matters to You
You get a slim phone that fits in your small pocket, but expands into a full tablet whenever you want to work or play!

> "Fold it into a pocket phone; unfold it into a giant tablet. It's the ultimate transformer gadget!" """
        },
        {
            "title": "NVIDIA Blackwell GB200 NVL72: Architecture of Exascale AI Supercomputing",
            "slug": "nvidia-blackwell-gb200-exascale-ai-supercomputing",
            "title_image": "cover_nvidia_blackwell.svg",
            "category": "Technology",
            "author": "ASI TECH",
            "tags": "NVIDIA, Blackwell, GB200, AI Hardware, GPUs, Supercomputing, NVLink",
            "read_time": 6,
            "is_featured": 1,
            "likes": 95,
            "views": 680,
            "content": """NVIDIA's Blackwell architecture marks the transition from single-board accelerator cards to integrated rack-scale exascale supercomputers engineered for trillion-parameter AI models.

# 1. Dual-Die 208-Billion Transistor Silicon
Manufactured on TSMC's custom 4NP node, Blackwell connects two maximum reticle-size dies into a unified single GPU:

- **10 TB/s NVLink-C2C Interconnect:** Die-to-die bandwidth that is 5x faster than PCIe Gen 5, functioning as a single coherent silicon processor with zero software latency.
- **192 GB HBM3e Memory:** Delivering 8.0 TB/s memory bandwidth to feed hungry matrix multipliers without cache starvation.
- **2nd-Generation Transformer Engine:** Supports micro-tensor **FP4 precision**, doubling throughput and halving memory footprint compared to Hopper FP8.

> "Blackwell GB200 NVL72 delivers a 30x inference speedup over the previous H100 generation for trillion-parameter reasoning models while slashing energy costs by 25x."

# 2. NVL72: The Rack-Scale Supercomputer
Rather than selling standalone PCIe cards, the flagship Blackwell configuration is the **GB200 NVL72**:
- Connects 36 Grace CPUs and 72 Blackwell GPUs in a single liquid-cooled rack.
- Features **130 TB/s aggregate NVLink bandwidth** through copper spine backplanes, allowing all 72 GPUs to address a unified 13.5 TB high-speed memory space as a single gigantic GPU.
- **Direct-to-Chip Liquid Cooling:** Dissipates 120kW per rack using specialized Coolant Distribution Units (CDUs) without noisy server fans.

# 3. Decompression & Cryptography Engines
Dedicated on-chip hardware decompression engines speed up Apache Spark SQL queries and vector database embeddings by 18x, unlocking real-time Graph RAG pipelines.

! The exascale compute density of Blackwell enables training frontier reasoning models with hundreds of billions of reinforcement learning parameters in weeks instead of years.""",
            "eli5_content": """# 👶 Explain Like I'm 5: NVIDIA Blackwell & AI Supercomputers

### 🎈 The Kid-Friendly Analogy: 72 Race Cars Hooked Up into One Mega Monster Truck
- **Normal Computers:** Like a single bicycle trying to move a giant mountain of homework.
- **NVIDIA Blackwell NVL72:** Like taking **72 supersonic race cars**, bolting them together with ultra-fast gold pipes, and cooling them with liquid ice water. They work together as one colossal brain that can read the entire internet in seconds!

---

### 💡 3 Key Things to Understand
- **1. 208 Billion Microscopic Switches:** Built with transistors smaller than a virus, all packed onto one super-chip.
- **2. FP4 Math Trick:** It uses clever mathematical shortcuts that make calculations twice as fast while using 25x less electricity!
- **3. Liquid-Cooled Radiator:** Instead of noisy fan blades, special chilled liquid flows right over the silicon to keep it super frosty.

---

### 🚀 Why This Matters to You
This supercomputer powers future AI helpers that can invent clean green energy formulas, cure diseases, and generate entire video games in real-time!

> "Blackwell connects 72 super-chips into one giant liquid-cooled brain to train the world's smartest AI systems." """
        },
        {
            "title": "Humanoid Robotics & Embodied AI: Tesla Optimus Gen 2 vs Boston Dynamics Atlas",
            "slug": "humanoid-robotics-embodied-ai-optimus-atlas",
            "title_image": "cover_humanoid_robotics.svg",
            "category": "Technology",
            "author": "ASI TECH",
            "tags": "Robotics, Humanoid, Embodied AI, Tesla Optimus, Boston Dynamics, Actuators, AI",
            "read_time": 5,
            "is_featured": 0,
            "likes": 77,
            "views": 530,
            "content": """Robotics is witnessing a profound shift from pre-programmed industrial arms to autonomous bipedal humanoid robots driven by end-to-end Vision-Language-Action (VLA) neural networks.

# 1. The Actuator & Mechanics Showdown
Humanoid robots require an unprecedented balance of torque density, low latency, and energy efficiency:

### Tesla Optimus Gen 2
- **Custom Electric Actuators:** Integrates custom planetary and harmonic drive electric motors with integrated load cells and positional encoders.
- **11-Degree-of-Freedom Hands:** Tactile sensor fingertips capable of manipulating delicate eggs and heavy automotive battery packs.
- **Weight Optimization:** Reduced structural mass by 10kg with articulated 2-DOF neck and foot force sensors.

### Boston Dynamics New Atlas
- **All-Electric High-Torque Swiveling Joints:** Replaces legacy hydraulic pumps with compact, ultra-powerful 360-degree rotating electric actuators.
- **Superhuman Kinematic Reach:** Atlas can spin its torso and limbs 360 degrees, picking up objects behind its back without turning its feet.

> "Humanoid form factors allow robots to operate directly within human-designed factories, kitchens, and stairs without redesigning infrastructure."

# 2. Embodied AI: Vision-to-Action Foundation Models
The real intelligence breakthrough is neural control:
- **Zero Hardcoded Paths:** The robot takes multi-camera video input and outputs direct torque motor commands via end-to-end transformers.
- **Teleoperation Reinforcement Learning:** Human operators train complex dexterous tasks using VR rigs; models generalize behaviors across diverse objects and friction levels.
- **Spatial Occupancy Grids:** Real-time visual SLAM calculates moving human trajectories to guarantee safe collaboration on factory floors.

! Automotive assembly lines and warehouse logistics hubs will begin deploying thousands of humanoid units over the next 24 months.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Humanoid Robots & Embodied AI

### 🎈 The Kid-Friendly Analogy: Giving AI a Body with Legs, Eyes, and Gentle Hands
- **ChatGPT / Chatbots:** Like a brain in a jar that can only write text messages.
- **Humanoid Robots (Optimus & Atlas):** Like giving that smart brain a real pair of legs, arms, and sensitive fingers so it can walk up stairs, carry heavy boxes, sort laundry, and hand you an egg without cracking the shell!

---

### 💡 3 Key Things to Understand
- **1. Sees with Cameras:** It uses cameras for eyes and calculates 3D space around it so it never bumps into people or furniture.
- **2. 11-Finger Dexterity:** Tactile fingertip sensors let it feel how soft or slippery an object is before picking it up.
- **3. Learns by Watching:** Instead of writing millions of lines of code, engineers teach it new chores simply by demonstrating them in virtual reality!

---

### 🚀 Why This Matters to You
Humanoid robots will soon handle dangerous factory jobs, carry heavy groceries, and help elderly people around the house!

> "Embodied AI takes the brain of AI and puts it into helpful robot hands and feet to do physical work safely." """
        },
        {
            "title": "Wi-Fi 7 & 6G Terahertz Networks: Sub-Millisecond Latency & 40Gbps Wireless Bandwidth",
            "slug": "wifi-7-and-6g-terahertz-wireless-networks",
            "title_image": "cover_wifi7_6g_wireless.svg",
            "category": "Technology",
            "author": "ASI TECH",
            "tags": "Wi-Fi 7, 6G, Wireless, Networking, Telecommunications, Speed, 4096-QAM",
            "read_time": 4,
            "is_featured": 0,
            "likes": 63,
            "views": 450,
            "content": """Wireless connectivity is undergoing its biggest structural evolution in two decades with the simultaneous deployment of Wi-Fi 7 (802.11be) and 6G Sub-Terahertz research.

# 1. The Core Innovations of Wi-Fi 7 (802.11be)
Wi-Fi 7 delivers up to **46 Gbps theoretical peak throughput**—nearly 5x faster than Wi-Fi 6E:

- **320 MHz Ultra-Wide Channels:** Doubling channel bandwidth in the 6 GHz frequency band for zero interference and ultra-high data density.
- **4096-QAM (4K-QAM) Modulation:** Packing 12 bits per symbol (a 20% transmission rate improvement over Wi-Fi 6's 1024-QAM).
- **Multi-Link Operation (MLO):** Devices can aggregate multiple frequency bands (2.4 GHz, 5 GHz, and 6 GHz) simultaneously. If one channel suffers interference, packets route dynamically over the alternative band with zero packet drop.

> "Multi-Link Operation drops wireless latency to under 5 milliseconds, enabling deterministic wireless gaming, cloud computing, and real-time AR telepresence."

# 2. 6G Terahertz & Sub-Millimeter Wave Horizons
Looking forward to 2030 and beyond, 6G networks operate in the 100 GHz to 3 THz frequency spectrum:
- **100 Gbps to 1 Tbps Mobile Bandwidth:** Transmitting holographic video streams wirelessly in real-time.
- **Sub-Millisecond Edge Latency:** Critical for synchronized swarm robotics and autonomous vehicle V2X collision avoidance.
- **Joint Communications and Sensing (JCAS):** 6G base stations double as high-resolution radar sensors, mapping weather, obstacle trajectories, and gestures.

! Wi-Fi 7 routers and client devices from Apple, Samsung, Qualcomm, and Intel are officially available worldwide today.""",
            "eli5_content": """# 👶 Explain Like I'm 5: Wi-Fi 7 & 6G Wireless

### 🎈 The Kid-Friendly Analogy: Turning a 1-Lane Dirt Road into a 16-Lane Super-Highway
- **Old Wi-Fi:** Like a narrow single-lane road. If your brother is downloading a giant game and your parents are streaming 4K movies, your video call stutters and freezes.
- **Wi-Fi 7 (Multi-Link):** Like a **16-lane super-highway** where your device can drive on the 2.4GHz, 5GHz, and 6GHz lanes all at the exact same millisecond! If one lane gets crowded, your stream instantly zips over to the empty lane without a single hiccup!

---

### 💡 3 Key Things to Understand
- **1. Download a Movie in 2 Seconds:** Wi-Fi 7 delivers speeds up to 46 gigabits per second.
- **2. Zero Lag for Online Gaming:** Drops delay down to practically zero, so online multiplayer games feel instantaneous.
- **3. 6G Terahertz Radar:** Future 6G antennas will transmit holographic 3D calls and even sense weather and moving obstacles like radar!

---

### 🚀 Why This Matters to You
No more spinning loading wheels, no dropped video calls, and instant ultra-fast downloads everywhere in your house!

> "Wi-Fi 7 links all wireless channels together at once so you never experience lag or buffering again." """
        }
    ]

    for b in blogs_data:
        db.execute(
            """INSERT INTO blogs (title, slug, title_image, content, eli5_content, category, author, tags, read_time, is_featured, likes, views)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (b["title"], b["slug"], b["title_image"], b["content"], b.get("eli5_content", ""), b["category"], b["author"], b["tags"], b["read_time"], b["is_featured"], b["likes"], b["views"])
        )
    
    sample_reviews = [
        (1, "David Miller", "david@ai-labs.org", 5, "DeepSeek-R1's reinforcement learning methodology without heavy SFT is a game changer for open source AI."),
        (1, "Elena Rostova", "elena@quantum.io", 5, "The explanation of test-time compute scaling is spot on. Fantastic writeup!"),
        (2, "Marcus Vance", "marcus@mit.edu", 5, "The hybrid Quantum-Classical pipeline breakdown is the clearest I've read all year."),
        (3, "Dr. Kenneth Wong", "kwong@ev-tech.de", 5, "Solid-state electrolyte safety combined with 800V charging will accelerate EV adoption tenfold."),
        (5, "Chris Anderson", "chris@systems-dev.com", 5, "Rust for safe backends and Mojo for AI kernels is the exact combination we are adopting at our startup."),
        (10, "Tim Cooksey", "tcooksey@silicon-insights.com", 5, "The unified memory 546 GB/s breakdown explains exactly why M4 Max runs local LLMs so effortlessly."),
        (11, "Jae-hyun Park", "jpark@seoul-tech.kr", 5, "Snapdragon 8 Elite's Oryon CPU paired with Galaxy AI 2.0 multimodal agents is a true iPhone rival."),
        (12, "Rachel Sterling", "rachel@spatial-vr.io", 5, "12ms R1 latency is why Vision Pro feels so natural. Best breakdown of foveated rendering!"),
        (14, "Jensen Liu", "jensen@deeplearning-hub.com", 5, "Blackwell GB200 NVL72 with FP4 precision and liquid CDUs changes datacenter economics completely.")
    ]
    for r in sample_reviews:
        db.execute(
            """INSERT INTO reviews (blog_id, name, email, rating, comment)
               VALUES (?, ?, ?, ?, ?)""",
            (r[0], r[1], r[2], r[3], r[4])
        )
    db.commit()

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Category metadata with fiery purplish accents
CATEGORY_CONFIG = {
    'Artificial Intelligence': {'icon': 'fa-brain', 'color': '#c084fc', 'badge': 'ai', 'desc': 'Neural nets, reasoning LLMs, quantum ML and autonomy.'},
    'Technology': {'icon': 'fa-laptop-code', 'color': '#a855f7', 'badge': 'tech', 'desc': 'High-performance systems, solid-state tech, edge architectures.'},
    'Science': {'icon': 'fa-atom', 'color': '#ec4899', 'badge': 'sci', 'desc': 'Astrophysics, neurotechnology, post-quantum cryptography & cosmos.'},
    'Education': {'icon': 'fa-graduation-cap', 'color': '#fb923c', 'badge': 'edu', 'desc': 'Career roadmaps, clean code, and engineering mastery.'},
    'Movies': {'icon': 'fa-film', 'color': '#f43f5e', 'badge': 'mov', 'desc': 'Virtual production, generative video, and cinema VFX.'}
}

# ==============================================================================
# ASI AI CHATBOT LOGIC (GEMINI & LOCAL MULTI-DOMAIN INTELLIGENCE ENGINE)
# ==============================================================================
def ask_gemini_or_asi(prompt, history=None):
    if not prompt or not prompt.strip():
        return "Please provide a question or topic so I can assist you."

    prompt_text = prompt.strip()
    prompt_lower = prompt_text.lower()
    
    # --------------------------------------------------------------------------
    # 1. TRY GOOGLE GEMINI API (GEMINI 2.0 & 1.5 MULTI-TIER ENGINE)
    # --------------------------------------------------------------------------
    if GEMINI_API_KEY:
        models_to_try = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ]
        system_instruction = (
            "You are ASI, an elite, sharp, and steady AI Assistant and Chief Scientist for 'ASI TECH' (a premier Tech, AI, Science, and Cinema journal). "
            "You have deep, universal mastery across software engineering (Python, JavaScript, TypeScript, Rust, C++, Go, SQL, Web Dev, DevOps), "
            "algorithms, machine learning (LLMs, transformers, RAG), physics, mathematics, science, modern tech hardware (Apple, Samsung, NVIDIA, etc.), "
            "and general problem solving. "
            "Always respond directly, accurately, and steadily. Format responses with clean Markdown headers, structured bullet points, and syntax-highlighted code blocks where helpful."
        )

        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
                contents_payload = []
                
                # Append multi-turn history if provided
                if history and isinstance(history, list):
                    for msg in history[-6:]:  # Keep last 6 context messages
                        role = "user" if msg.get("role") in ["user", "human"] else "model"
                        contents_payload.append({
                            "role": role,
                            "parts": [{"text": msg.get("text", "")}]
                        })
                
                # Add current user prompt
                contents_payload.append({
                    "role": "user",
                    "parts": [{"text": f"[System Context: {system_instruction}]\n\nUser Question: {prompt_text}"}]
                })

                payload = {
                    "contents": contents_payload,
                    "generationConfig": {
                        "temperature": 0.6,
                        "maxOutputTokens": 900,
                        "topP": 0.95
                    }
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=6) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    text_response = result['candidates'][0]['content']['parts'][0]['text']
                    if text_response and len(text_response.strip()) > 10:
                        return text_response.strip()
            except Exception:
                continue  # Try next model or fallback

    # --------------------------------------------------------------------------
    # 2. LOCAL INTELLIGENCE & REASONING KNOWLEDGE ENGINE (OFFLINE / FALLBACK)
    # --------------------------------------------------------------------------

    # --- Identity & Capabilities ---
    if any(k in prompt_lower for k in ['who are you', 'what is your name', 'what are you', 'introduce yourself']):
        return (
            "👋 Hello! I am **ASI**, your intelligent research and engineering assistant on **ASI TECH**.\n\n"
            "### 🌟 My Core Capabilities:\n"
            "- 💻 **Full-Stack Software Engineering:** Python, JavaScript, TypeScript, Rust, Go, C++, SQL, Docker, Linux, and APIs.\n"
            "- 🧠 **AI & Machine Learning:** DeepSeek-R1, reasoning architectures, transformers, RAG, quantization, and LLMOps.\n"
            "- 📱 **Hardware & Mobile Tech:** Apple Silicon (M4/M5), Samsung Galaxy S25, NVIDIA Blackwell GPUs, and Foldables.\n"
            "- ⚛️ **Science & Mathematics:** Quantum physics, calculus, linear algebra, aerospace, and solid-state energy.\n"
            "- 🛠️ **Troubleshooting & Code Review:** Debugging errors, code optimization, architecture design, and algorithms.\n\n"
            "Ask me any coding question, tech comparison, or scientific concept!"
        )

    # --- Greetings & Salutations ---
    if any(prompt_lower.strip() == k for k in ['hi', 'hello', 'hey', 'greetings', 'sup', 'yo', 'good morning', 'good evening']):
        return (
            "✨ Hello! I am **ASI**, your AI assistant on **ASI TECH**.\n\n"
            "How can I help you today? You can ask me:\n"
            "- 🐍 **Coding:** *'How do I implement binary search in Python?'* or *'Explain closures in JS'*\n"
            "- 🍎 **Hardware:** *'What makes Apple M4 unified memory so fast?'*\n"
            "- 📱 **Mobile:** *'What are the best features of Samsung Galaxy S25?'*\n"
            "- 🧠 **AI:** *'How do reasoning models like DeepSeek-R1 work?'*\n"
            "- 🚀 **Science:** *'Explain quantum superposition or general relativity'*\n\n"
            "Feel free to type any question!"
        )

    # --- Apple Silicon & Apple Ecosystem ---
    if any(k in prompt_lower for k in ['apple', 'iphone', 'm4', 'm5', 'silicon', 'vision pro', 'macbook', 'ios 18', 'macos']):
        return (
            "🍎 **Apple Silicon, Apple Intelligence & Spatial Computing Breakdown**\n\n"
            "Apple's ecosystem leverages tightly integrated hardware-software architecture:\n\n"
            "### Key Architectural Highlights:\n"
            "1. **Unified Memory Architecture (UMA):** M4 Max delivers up to **546 GB/s zero-copy memory bandwidth** across CPU, GPU, and 16-Core Neural Engine (38 TOPS), enabling local execution of 70B quantized LLMs without GPU VRAM transfer bottlenecks.\n"
            "2. **Apple Intelligence On-Device AI:** 3B parameter foundation models run locally within ~1.8GB RAM with LoRA adapter hot-swapping, backed by cryptographically verifiable Private Cloud Compute (PCC).\n"
            "3. **Vision Pro Spatial Computing:** Twin 4K Micro-OLEDs (23M pixels) paired with custom **Apple R1 sensor chip** achieving ultra-low 12ms photon-to-motion pass-through latency.\n\n"
            "📖 *Read our full deep-dive: 'Apple Intelligence, M4 Max & M5 Silicon' in the Technology journal!*"
        )

    # --- Samsung & Mobile Hardware ---
    if any(k in prompt_lower for k in ['samsung', 'galaxy', 's25', 'foldable', 'trifold', 'snapdragon 8 elite', 'one ui']):
        return (
            "📱 **Samsung Galaxy S25 Ultra, Galaxy AI 2.0 & Tri-Fold Hardware**\n\n"
            "Samsung pairs custom mobile silicon with multimodal OS agents:\n\n"
            "### Engineering Innovations:\n"
            "1. **Snapdragon 8 Elite for Galaxy:** Custom Qualcomm Oryon prime cores @ 4.32 GHz with Hexagon NPU for 45% faster generative AI processing.\n"
            "2. **Galaxy AI 2.0 Multimodal Agents:** Real-time bi-directional voice translation across 20+ languages at 16kHz, Now Briefing context aggregator, and decentralized Knox Matrix security.\n"
            "3. **Tri-Fold Flexible AMOLED Displays:** Dual waterdrop zero-gap hinges and 30-micron Ultra-Thin Glass (UTG 3.0) tested for over 500,000 fold cycles.\n\n"
            "📖 *Explore 'Samsung Galaxy S25 Ultra & Galaxy AI 2.0' in our Technology section!*"
        )

    # --- NVIDIA & GPU Supercomputing ---
    if any(k in prompt_lower for k in ['nvidia', 'blackwell', 'gb200', 'nvlink', 'gpu', 'h100', 'cuda', 'tensor core']):
        return (
            "🟢 **NVIDIA Blackwell GB200 & Exascale AI Supercomputing**\n\n"
            "NVIDIA's Blackwell architecture redefines datacenter compute density:\n\n"
            "### Architecture Highlights:\n"
            "- **Dual-Die 208B Transistor Package:** Unified via **10 TB/s NVLink-C2C** high-speed bus connecting two TSMC 4NP reticle-sized dies into one coherent GPU.\n"
            "- **NVL72 Liquid-Cooled Rack:** Unifies 72 Blackwell GPUs and 36 Grace CPUs into a single 13.5 TB high-bandwidth memory space.\n"
            "- **FP4 Transformer Engine:** 30x faster inference throughput for trillion-parameter reasoning models with 25x lower energy consumption.\n\n"
            "📖 *Check out our dedicated article: 'NVIDIA Blackwell GB200 NVL72' on ASI TECH!*"
        )

    # --- Robotics & Embodied AI ---
    if any(k in prompt_lower for k in ['robot', 'robotics', 'optimus', 'atlas', 'humanoid', 'embodied ai']):
        return (
            "🤖 **Humanoid Robotics & Embodied AI (Optimus vs Atlas)**\n\n"
            "Modern robotics has moved from rigid scripting to end-to-end Vision-Language-Action (VLA) foundation models:\n\n"
            "### Technical Breakdown:\n"
            "- **Tesla Optimus Gen 2:** Custom planetary electric actuators with 11-DOF tactile fingertip sensors and real-time vision-only SLAM occupancy networks.\n"
            "- **Boston Dynamics All-Electric Atlas:** 360-degree swiveling joint actuators delivering superhuman kinematic flexibility and continuous dynamic balance.\n"
            "- **Vision-to-Action Transformers:** Direct video-to-torque motor control trained via simulation domain randomization and VR teleoperation."
        )

    # --- Wi-Fi 7 & 6G Wireless ---
    if any(k in prompt_lower for k in ['wifi 7', '6g', 'wireless', 'network', '4096-qam', 'mlo', 'bandwidth']):
        return (
            "📡 **Wi-Fi 7 (802.11be) & 6G Terahertz Wireless Networks**\n\n"
            "Next-generation wireless networks deliver fiber-grade speeds over the air:\n\n"
            "### Core Innovations:\n"
            "- **Wi-Fi 7 (46 Gbps Throughput):** 320 MHz channels, 4096-QAM modulation, and **Multi-Link Operation (MLO)** aggregating 2.4, 5, and 6 GHz simultaneously for sub-5ms latency.\n"
            "- **6G Sub-Terahertz (100 GHz - 3 THz):** Terabit wireless bandwidth and Joint Communications and Sensing (JCAS) radar mapping.\n\n"
            "📖 *Read our publication: 'Wi-Fi 7 & 6G Terahertz Networks' in the Technology category!*"
        )

    # --- AI Reasoning & DeepSeek / Claude ---
    if any(k in prompt_lower for k in ['deepseek', 'r1', 'reasoning', 'o3', 'claude 3.7', 'cot', 'test-time compute']):
        return (
            "🧠 **DeepSeek-R1, Claude 3.7 & Reasoning LLMs Breakdown**\n\n"
            "Reasoning models represent a fundamental paradigm shift toward **test-time compute scaling**.\n\n"
            "### Architectural Innovations:\n"
            "1. **Pure Rule-Based RL (DeepSeek-R1-Zero):** Reinforcement learning directly on deterministic verification rules without supervised human demonstrations.\n"
            "2. **Dynamic Chain-of-Thought:** The model autonomously allocates thinking tokens to backtrack, hypothesize, verify sub-goals, and self-correct.\n"
            "3. **Inference Scaling Laws:** Allocating compute at query time yields exponential error reduction on math, coding, and logical proofs.\n\n"
            "```python\n"
            "# Multi-Step Reasoning Verification Flow\n"
            "def verify_reasoning_step(hypothesis, verification_rule):\n"
            "    state = execute_verification(hypothesis)\n"
            "    if not state.is_valid:\n"
            "        return backtrack_and_refine(hypothesis, state.error_trace)\n"
            "    return state.validated_solution\n"
            "```"
        )

    # --- Quantum Computing ---
    if any(k in prompt_lower for k in ['quantum', 'qubit', 'superposition', 'entanglement', 'shor']):
        return (
            "⚛️ **Quantum Computing & AI Convergence Overview**\n\n"
            "Quantum information systems leverage quantum mechanics to explore exponential state spaces in parallel:\n\n"
            "### Core Concepts:\n"
            "- **Quantum Superposition:** Qubits represent linear superpositions $|\\psi\\rangle = \\alpha|0\\rangle + \\beta|1\\rangle$, evaluating combinatorial paths simultaneously.\n"
            "- **Quantum Entanglement:** Synchronized quantum states allowing instantaneous non-local state correlation.\n"
            "- **Parameterized Quantum Circuits (PQC):** Variational layers optimized via quantum gradient descent for Quantum Machine Learning (QML).\n\n"
            "```python\n"
            "from qiskit import QuantumCircuit\n"
            "qc = QuantumCircuit(2)\n"
            "qc.h(0)         # Create Superposition on qubit 0\n"
            "qc.cx(0, 1)     # Entangle qubit 0 and qubit 1\n"
            "print(qc.draw())\n"
            "```"
        )

    # --- Data Structures & Algorithms ---
    if any(k in prompt_lower for k in ['binary search', 'algorithm', 'data structure', 'linked list', 'dynamic programming', 'two pointer', 'bfs', 'dfs', 'sorting', 'time complexity', 'big o']):
        return (
            "🧮 **Algorithms & Data Structures Master Guide**\n\n"
            "Optimizing time and space complexity is fundamental to building scalable systems:\n\n"
            "### 1. Binary Search (Time: O(log N), Space: O(1)):\n"
            "```python\n"
            "def binary_search(arr, target):\n"
            "    left, right = 0, len(arr) - 1\n"
            "    while left <= right:\n"
            "        mid = left + (right - left) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        elif arr[mid] < target:\n"
            "            left = mid + 1\n"
            "        else:\n"
            "            right = mid - 1\n"
            "    return -1\n"
            "```\n\n"
            "### 2. Core Problem-Solving Patterns:\n"
            "- **Two Pointers:** Optimal for sorted arrays, palindrome checking, and container volume problems (O(N)).\n"
            "- **Sliding Window:** Best for subarray sums, substring matching with length K.\n"
            "- **Dynamic Programming:** Break overlapping subproblems into memoized tabular states (e.g. Knapsack, Edit Distance)."
        )

    # --- DevOps, Docker & Git ---
    if any(k in prompt_lower for k in ['docker', 'kubernetes', 'git', 'ci/cd', 'linux', 'bash', 'nginx', 'deploy']):
        return (
            "🐳 **DevOps, Docker & Modern Infrastructure**\n\n"
            "Modern deployment pipelines prioritize reproducible container environments and automated CI/CD:\n\n"
            "### 1. Production Multi-Stage Dockerfile for Python/Node:\n"
            "```dockerfile\n"
            "# Build stage\n"
            "FROM python:3.11-slim as builder\n"
            "WORKDIR /app\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir --user -r requirements.txt\n"
            "\n"
            "# Final minimal runtime\n"
            "FROM python:3.11-slim\n"
            "WORKDIR /app\n"
            "COPY --from=builder /root/.local /root/.local\n"
            "COPY . .\n"
            "ENV PATH=/root/.local/bin:$PATH\n"
            "EXPOSE 5000\n"
            "CMD [\"gunicorn\", \"--workers=4\", \"--bind=0.0.0.0:5000\", \"app:app\"]\n"
            "```\n\n"
            "### 2. Essential Git Workflow Commands:\n"
            "- `git checkout -b feature/new-feat` -> Create isolated branch\n"
            "- `git rebase main` -> Keep linear, clean commit history\n"
            "- `git cherry-pick <commit-hash>` -> Apply specific commit to current branch"
        )

    # --- Networking, Security & APIs ---
    if any(k in prompt_lower for k in ['tcp', 'udp', 'cors', 'oauth', 'jwt', 'rest', 'graphql', 'http', 'security', 'ssl', 'tls']):
        return (
            "🛡️ **Networking Protocols, Security & API Design**\n\n"
            "### 1. TCP vs UDP Comparison:\n"
            "- **TCP (Transmission Control Protocol):** Connection-oriented, guarantees ordered packet delivery via 3-way handshake and retransmissions (HTTPS, APIs, File transfer).\n"
            "- **UDP (User Datagram Protocol):** Connectionless, lightweight with zero retransmission overhead (VoIP, Live Video Streaming, Online Gaming).\n\n"
            "### 2. Fixing CORS (Cross-Origin Resource Sharing):\n"
            "CORS errors occur when a browser blocks frontend requests to a different domain/port. Fix by returning CORS headers on the server:\n"
            "```python\n"
            "# Flask CORS Header Setup\n"
            "@app.after_request\n"
            "def add_cors_headers(response):\n"
            "    response.headers['Access-Control-Allow-Origin'] = '*'\n"
            "    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'\n"
            "    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'\n"
            "    return response\n"
            "```\n\n"
            "### 3. JWT Authentication Flow:\n"
            "- Client sends credentials -> Server validates & signs JWT token -> Client includes `Authorization: Bearer <token>` in subsequent requests."
        )

    # --- Systems Programming (Rust, Zig, Mojo) ---
    if any(k in prompt_lower for k in ['rust', 'zig', 'mojo', 'systems programming', 'c++']):
        return (
            "🦀 **Systems Programming: Rust vs Zig vs Mojo Comparison**\n\n"
            "Modern systems programming focuses on memory safety, explicit semantics, and hardware acceleration:\n\n"
            "### 1. Rust (Safe & Fearless Concurrency)\n"
            "- **Compile-time safety:** Enforces memory safety through ownership and borrow checking without garbage collection overhead.\n\n"
            "```rust\n"
            "fn compute_tensor(data: &[f32]) -> f32 {\n"
            "    data.iter().map(|&x| x * x).sum()\n"
            "}\n"
            "```\n\n"
            "### 2. Zig (Simplicity & Comptime)\n"
            "- **No hidden control flow:** Explicit allocation with compile-time code execution (`comptime`) and seamless C interoperability.\n\n"
            "### 3. Mojo (AI Hardware Acceleration)\n"
            "- **Python syntax with C performance:** Built natively on MLIR (Multi-Level Intermediate Representation) for massive SIMD and GPU tensor parallelization."
        )

    # --- Python Programming Catch-all ---
    if any(k in prompt_lower for k in ['python', 'asyncio', 'decorator', 'generator', 'list comprehension', 'gil', 'fastapi']):
        return (
            "🐍 **Python Engineering & Best Practices**\n\n"
            "Python is the dominant language for AI engineering, backend systems, and data pipelines:\n\n"
            "### 1. High-Performance Idiomatic Patterns:\n"
            "```python\n"
            "# 1. Clean Custom Decorator with Timing\n"
            "import time\n"
            "from functools import wraps\n"
            "\n"
            "def benchmark(func):\n"
            "    @wraps(func)\n"
            "    def wrapper(*args, **kwargs):\n"
            "        start = time.perf_counter()\n"
            "        result = func(*args, **kwargs)\n"
            "        print(f'{func.__name__} executed in {time.perf_counter() - start:.6f}s')\n"
            "        return result\n"
            "    return wrapper\n"
            "\n"
            "# 2. Memory-Efficient Generator Pipeline\n"
            "def stream_large_dataset(filepath):\n"
            "    with open(filepath, 'r') as f:\n"
            "        for line in f:\n"
            "            if line.strip():\n"
            "                yield line.strip()\n"
            "```\n\n"
            "### 2. Pro-Tips for Production Python:\n"
            "- Use `pydantic` and `typing` for strict runtime schema validation.\n"
            "- Use `asyncio` for I/O-bound microservices and `multiprocessing` to bypass the GIL for CPU-bound tasks.\n"
            "- Use vectorization (`numpy`, `polars`) for numerical operations."
        )

    # --- JavaScript / TypeScript / Web Development Catch-all ---
    if any(k in prompt_lower for k in ['javascript', 'typescript', 'closure', 'promise', 'async/await', 'react', 'next.js', 'css', 'dom']):
        return (
            "⚡ **JavaScript & Modern Web Architecture**\n\n"
            "Modern frontend & fullstack web engineering focuses on reactivity, static optimization, and type safety:\n\n"
            "### 1. Closures & Asynchronous Event Loop:\n"
            "```javascript\n"
            "// Example: Encapsulated State via Closure\n"
            "function createRateLimiter(limit, intervalMs) {\n"
            "    let calls = 0;\n"
            "    let resetTime = Date.now() + intervalMs;\n"
            "    return function allow() {\n"
            "        if (Date.now() > resetTime) {\n"
            "            calls = 0;\n"
            "            resetTime = Date.now() + intervalMs;\n"
            "        }\n"
            "        if (calls < limit) {\n"
            "            calls++;\n"
            "            return true;\n"
            "        }\n"
            "        return false;\n"
            "    };\n"
            "}\n"
            "```\n\n"
            "### 2. TypeScript Generics & Strict Safety:\n"
            "```typescript\n"
            "interface ApiResponse<T> {\n"
            "    data: T;\n"
            "    status: 'success' | 'error';\n"
            "    timestamp: number;\n"
            "}\n"
            "```\n\n"
            "### 3. Key Web Principles:\n"
            "- **Island Architecture:** Hydrate only interactive UI components to achieve instant First Contentful Paint (FCP).\n"
            "- **Edge SSR:** Render dynamic pages near users via global CDN workers."
        )

    # --- Mathematics & Science ---
    if any(k in prompt_lower for k in ['math', 'calculus', 'derivative', 'integral', 'matrix', 'physics', 'relativity', 'einstein', 'crispr', 'dna', 'thermodynamics', 'black hole']):
        return (
            "🌌 **Scientific Principles & Mathematical Foundations**\n\n"
            "### 1. Calculus & Optimization in Machine Learning:\n"
            "- **Gradient Descent:** $\\theta_{t+1} = \\theta_t - \\eta \\nabla L(\\theta_t)$\n"
            "- Uses the chain rule to backpropagate partial derivatives of error through multi-layer neural weights.\n\n"
            "### 2. Einstein's General Relativity & Spacetime:\n"
            "- Mass-energy tells spacetime how to curve ($G_{\\mu\\nu} = \\frac{8\\pi G}{c^4} T_{\\mu\\nu}$), and curved spacetime tells matter how to move.\n"
            "- Leads to gravitational time dilation, black hole event horizons, and gravitational lensing.\n\n"
            "### 3. CRISPR-Cas9 Gene Editing:\n"
            "- Utilizes a guide RNA (gRNA) to match precise DNA sequences and Cas9 endonuclease to make targeted molecular cuts for genetic repairs."
        )

    # --- Dynamic RAG / Search in Database ---
    try:
        db = get_db()
        words = [w for w in re.findall(r'\w+', prompt_lower) if len(w) > 3]
        if words:
            query_str = f"%{words[0]}%"
            matching_blog = db.execute(
                "SELECT title, slug, category, content FROM blogs WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? LIMIT 1",
                (query_str, query_str, query_str)
            ).fetchone()
            if matching_blog:
                clean_preview = re.sub(r'<[^>]+>', ' ', matching_blog['content'])
                clean_preview = re.sub(r'#+\s*', '', clean_preview)[:260].strip()
                return (
                    f"💡 **ASI Research Insight: '{prompt_text}'**\n\n"
                    f"Regarding **{prompt_text}**, this topic is actively explored in our **{matching_blog['category']}** research division.\n\n"
                    f"### Key Summary:\n"
                    f"{clean_preview}...\n\n"
                    f"📖 *Read our full in-depth article: [{matching_blog['title']}](/blog/{matching_blog['slug']}) for detailed technical analysis!*"
                )
    except Exception:
        pass

    # --- Universal Sharp Synthesizer (Handles ANY out-of-blog question steadily) ---
    topic_clean = re.sub(r'[^\w\s]', '', prompt_text).strip()
    return (
        f"🎯 **ASI Technical Analysis: {prompt_text}**\n\n"
        f"Here is a sharp, structured breakdown regarding **{topic_clean or prompt_text}**:\n\n"
        "### 1. Core Definition & Concept\n"
        f"- In modern engineering and computer science, **{topic_clean or prompt_text}** relates to optimizing system efficiency, architectural clarity, and reliable execution.\n"
        "- The objective is to decouple complexity while maximizing throughput, security, and maintainability.\n\n"
        "### 2. Key Principles & Implementation Steps\n"
        "1. **Deconstruct the Problem:** Break the objective into isolated, testable modular components.\n"
        "2. **State & Memory Management:** Ensure predictable data flow, minimal allocation overhead, and zero side-effects.\n"
        "3. **Verification & Observability:** Implement unit testing, edge-case coverage, and structured logging.\n\n"
        "### 3. Practical Example Pattern\n"
        "```python\n"
        "# Idiomatic, resilient implementation structure\n"
        "def execute_task(input_data: dict) -> dict:\n"
        "    if not input_data:\n"
        "        raise ValueError('Invalid input parameters')\n"
        "    \n"
        "    # Process data with deterministic guarantees\n"
        "    processed = {k: v for k, v in input_data.items() if v is not None}\n"
        "    return {'status': 'success', 'result': processed}\n"
        "```\n\n"
        "💡 **Pro-Tip:** *Always measure bottlenecks with profilers before optimizing, and maintain comprehensive test suites!*"
    )

# ============== FRONTEND ROUTES ==============

@app.route('/')
def home():
    db = get_db()
    featured = db.execute(
        "SELECT * FROM blogs WHERE is_featured = 1 ORDER BY created_at DESC LIMIT 3"
    ).fetchall()
    if not featured:
        featured = db.execute(
            "SELECT * FROM blogs ORDER BY views DESC LIMIT 3"
        ).fetchall()
    
    latest_blogs = db.execute(
        "SELECT * FROM blogs ORDER BY created_at DESC LIMIT 12"
    ).fetchall()
    
    categories_raw = db.execute(
        "SELECT category, COUNT(*) as count FROM blogs GROUP BY category"
    ).fetchall()
    
    total_blogs = db.execute("SELECT COUNT(*) as count FROM blogs").fetchone()['count']
    total_views = db.execute("SELECT COALESCE(SUM(views), 0) as total FROM blogs").fetchone()['total']
    total_reviews = db.execute("SELECT COUNT(*) as count FROM reviews").fetchone()['count']
    
    return render_template(
        'index.html',
        featured_blogs=featured,
        blogs=latest_blogs,
        categories=categories_raw,
        total_blogs=total_blogs,
        total_views=total_views,
        total_reviews=total_reviews,
        category_config=CATEGORY_CONFIG
    )

@app.route('/blog/<slug>')
def blog_detail(slug):
    db = get_db()
    blog = db.execute("SELECT * FROM blogs WHERE slug = ?", (slug,)).fetchone()
    if blog is None:
        alt_slug = slug.replace('-37-', '-3-7-') if '-37-' in slug else slug.replace('-3-7-', '-37-')
        blog = db.execute("SELECT * FROM blogs WHERE slug = ?", (alt_slug,)).fetchone()
        if blog:
            return redirect(url_for('blog_detail', slug=blog['slug']), code=301)

    if blog is None:
        flash('The requested article could not be found.', 'error')
        return redirect(url_for('home'))
    
    db.execute("UPDATE blogs SET views = views + 1 WHERE id = ?", (blog['id'],))
    db.commit()
    
    reviews = db.execute(
        "SELECT * FROM reviews WHERE blog_id = ? ORDER BY created_at DESC",
        (blog['id'],)
    ).fetchall()
    
    avg_rating = 5.0
    if reviews:
        total_score = sum(r['rating'] for r in reviews)
        avg_rating = round(total_score / len(reviews), 1)

    related = db.execute(
        "SELECT * FROM blogs WHERE category = ? AND id != ? ORDER BY created_at DESC LIMIT 3",
        (blog['category'], blog['id'])
    ).fetchall()
    
    if len(related) < 3:
        extra = db.execute(
            "SELECT * FROM blogs WHERE id != ? AND id NOT IN (SELECT id FROM blogs WHERE category = ? AND id != ?) ORDER BY created_at DESC LIMIT ?",
            (blog['id'], blog['category'], blog['id'], 3 - len(related))
        ).fetchall()
        related = list(related) + list(extra)

    prev_blog = db.execute(
        "SELECT title, slug FROM blogs WHERE id < ? ORDER BY id DESC LIMIT 1",
        (blog['id'],)
    ).fetchone()
    next_blog = db.execute(
        "SELECT title, slug FROM blogs WHERE id > ? ORDER BY id ASC LIMIT 1",
        (blog['id'],)
    ).fetchone()

    tag_list = [t.strip() for t in blog['tags'].split(',') if t.strip()] if blog['tags'] else []

    eli5_content = blog['eli5_content']
    if not eli5_content or not eli5_content.strip():
        eli5_content = generate_eli5_fallback(blog['title'], blog['content'])
    eli5_read_time = calculate_read_time(eli5_content)

    # Fetch reaction counts
    reactions_raw = db.execute(
        "SELECT reaction_type, count FROM blog_reactions WHERE blog_id = ?",
        (blog['id'],)
    ).fetchall()
    reactions = {r['reaction_type']: r['count'] for r in reactions_raw}
    for rtype in ['fire', 'bulb', 'rocket', 'mindblown', 'heart']:
        if rtype not in reactions:
            reactions[rtype] = 0

    # Fetch article quiz
    quiz_data = get_article_quiz(blog)

    return render_template(
        'blog.html',
        blog=blog,
        eli5_content=eli5_content,
        eli5_read_time=eli5_read_time,
        reviews=reviews,
        avg_rating=avg_rating,
        related=related,
        prev_blog=prev_blog,
        next_blog=next_blog,
        tag_list=tag_list,
        reactions=reactions,
        quiz_data=quiz_data,
        category_config=CATEGORY_CONFIG
    )

@app.route('/blog/<slug>/review', methods=['POST'])
def add_review(slug):
    db = get_db()
    blog = db.execute("SELECT id FROM blogs WHERE slug = ?", (slug,)).fetchone()
    if blog is None:
        flash('Blog not found!', 'error')
        return redirect(url_for('home'))
    
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    
    name = request.form.get('name', user_name or 'Tech Reader').strip()
    email = request.form.get('email', user_email or '').strip()
    try:
        rating = int(request.form.get('rating', 5))
    except ValueError:
        rating = 5
    comment = request.form.get('comment', '').strip()

    if not comment:
        flash('Please write a comment for your review!', 'error')
        return redirect(url_for('blog_detail', slug=slug) + '#reviews')
    
    db.execute(
        "INSERT INTO reviews (blog_id, name, email, rating, comment) VALUES (?, ?, ?, ?, ?)",
        (blog['id'], name if name else 'Tech Reader', email, rating, comment)
    )
    db.commit()
    flash('Thank you! Your review has been posted.', 'success')
    return redirect(url_for('blog_detail', slug=slug) + '#reviews')

@app.route('/api/blog/<slug>/like', methods=['POST'])
def like_blog(slug):
    db = get_db()
    blog = db.execute("SELECT id, likes FROM blogs WHERE slug = ?", (slug,)).fetchone()
    if not blog:
        return jsonify({'status': 'error', 'message': 'Blog not found'}), 404
    
    new_likes = (blog['likes'] or 0) + 1
    db.execute("UPDATE blogs SET likes = ? WHERE id = ?", (new_likes, blog['id']))
    db.commit()
    return jsonify({'status': 'success', 'likes': new_likes})

# ==============================================================================
# TECH BENCHMARK & COMPARISON SUITE DATA
# ==============================================================================
TECH_COMPARISONS = {
    'apple-m4-max-vs-snapdragon-8-elite': {
        'id': 'apple-m4-max-vs-snapdragon-8-elite',
        'title': 'Apple M4 Max vs Qualcomm Snapdragon 8 Elite',
        'category': 'Silicon & Mobile Architecture',
        'headline': 'The Battle for Maximum Efficiency & AI Inference Throughput',
        'item_a': {
            'name': 'Apple Silicon M4 Max',
            'badge': 'macOS / Workstation',
            'color': '#38bdf8',
            'specs': {
                'Process Node': 'TSMC 3nm (N3E)',
                'Max Clock Speed': '4.50 GHz Performance Core',
                'Memory Bandwidth': '546 GB/s Unified Memory',
                'Max RAM Capacity': 'Up to 128 GB Unified RAM',
                'NPU AI Power': '38 TOPS (16-Core)',
                'Single-Core (GB6)': '4,060',
                'Multi-Core (GB6)': '26,700',
                'Target Form Factor': 'MacBook Pro & Mac Studio'
            },
            'pros': [
                'Unmatched 546 GB/s zero-copy memory bandwidth',
                'Runs local 70B quantized LLMs effortlessly in RAM',
                'Class-leading single-core IPC and battery runtime'
            ],
            'cons': [
                'Locked to Apple hardware ecosystem',
                'Non-upgradable unified memory'
            ]
        },
        'item_b': {
            'name': 'Snapdragon 8 Elite (for Galaxy)',
            'badge': 'Android / Flagship Mobile',
            'color': '#a855f7',
            'specs': {
                'Process Node': 'TSMC 3nm (N3E)',
                'Max Clock Speed': '4.32 GHz Oryon Prime Core',
                'Memory Bandwidth': '100 GB/s LPDDR5X',
                'Max RAM Capacity': 'Up to 24 GB Mobile RAM',
                'NPU AI Power': '45 TOPS Hexagon NPU',
                'Single-Core (GB6)': '3,250',
                'Multi-Core (GB6)': '10,600',
                'Target Form Factor': 'Samsung Galaxy S25 Ultra'
            },
            'pros': [
                'Desktop-class custom Oryon core clock speeds',
                '45 TOPS NPU specialized for multi-token speculation',
                'Hardware-accelerated Nanite mesh shading for gaming'
            ],
            'cons': [
                'Thermal throttling under sustained extreme loads',
                'Limited memory bandwidth compared to desktop silicon'
            ]
        },
        'verdict': 'Apple M4 Max reigns supreme for heavy workstation compute, video rendering, and multi-gigabyte local LLMs. Snapdragon 8 Elite is the undisputed king of pocket mobile flagships with superior peak clock speeds and on-device multimodal agents.'
    },
    'deepseek-r1-vs-claude-3-7': {
        'id': 'deepseek-r1-vs-claude-3-7',
        'title': 'DeepSeek-R1 vs Claude 3.7 Sonnet',
        'category': 'Frontier Reasoning AI',
        'headline': 'Pure Rule-Based Reinforcement Learning vs Hybrid Hybrid-Thinking Foundation Models',
        'item_a': {
            'name': 'DeepSeek-R1',
            'badge': 'Open-Weights Frontier',
            'color': '#38bdf8',
            'specs': {
                'Architecture': 'Mixture-of-Experts (MoE) 671B (37B active)',
                'Training Paradigm': 'Pure Rule-Based Reinforcement Learning (RL)',
                'Reasoning Mechanism': 'Autonomous Dynamic Chain-of-Thought',
                'MATH-500 Benchmark': '97.3%',
                'AIME 2024 Benchmark': '79.8%',
                'Codeforces Percentile': '96.3%',
                'Inference Cost': '$0.55 / 1M Input Tokens'
            },
            'pros': [
                'Open weights downloadable for local and private deployment',
                'Incredible reasoning capabilities emergent from pure RL',
                'Extreme cost efficiency via MoE architectural sparsity'
            ],
            'cons': [
                'Requires substantial local VRAM for unquantized weights',
                'Less conversational polish compared to heavily aligned assistants'
            ]
        },
        'item_b': {
            'name': 'Claude 3.7 Sonnet',
            'badge': 'Hybrid Frontier API',
            'color': '#ec4899',
            'specs': {
                'Architecture': 'Dense / Hybrid Dynamic Reasoning Transformer',
                'Training Paradigm': 'Constitutional RL + Test-Time Thinking Control',
                'Reasoning Mechanism': 'Controllable Thinking Budget Slider',
                'MATH-500 Benchmark': '96.8%',
                'AIME 2024 Benchmark': '82.4%',
                'Codeforces Percentile': '97.1%',
                'Inference Cost': '$3.00 / 1M Input Tokens'
            },
            'pros': [
                'Dynamic slider to dial thinking time up or down per query',
                'Unrivaled software engineering & full-stack code refactoring',
                'Nuanced natural language synthesis and ethical steerability'
            ],
            'cons': [
                'Proprietary closed-source API model',
                'Higher per-token pricing for heavy inference workloads'
            ]
        },
        'verdict': 'DeepSeek-R1 broke the open-source barrier proving that pure RL yields frontier reasoning. Claude 3.7 Sonnet provides the most polished, controllable hybrid engineering assistant for enterprise teams.'
    },
    'rust-vs-zig-vs-mojo': {
        'id': 'rust-vs-zig-vs-mojo',
        'title': 'Rust vs Zig vs Mojo',
        'category': 'High-Performance Systems & AI',
        'headline': 'Memory Safety Champion vs Explicit Comptime Simplicity vs Hardware AI Velocity',
        'item_a': {
            'name': 'Rust',
            'badge': 'Memory-Safe Standard',
            'color': '#fb923c',
            'specs': {
                'Memory Management': 'Compile-Time Borrow Checker',
                'Garbage Collector': 'Zero GC',
                'Compilation Speed': 'Moderate (LLVM heavy)',
                'C Interoperability': 'Via `extern "C"` FFI bindings',
                'Primary Domain': 'OS Kernels, High-Throughput Backends, Cryptography',
                'Ecosystem Maturity': 'Industry Standard (Linux kernel, Windows)'
            },
            'pros': [
                'Guarantees zero data races and memory corruption at compile time',
                'Massive crates.io ecosystem and production enterprise adoption',
                'Rich trait system and ergonomic functional combinators'
            ],
            'cons': [
                'Steep borrow-checker learning curve for newcomers',
                'Slower compilation times on massive codebases'
            ]
        },
        'item_b': {
            'name': 'Mojo',
            'badge': 'AI Accelerator',
            'color': '#ef4444',
            'specs': {
                'Memory Management': 'Hybrid Ownership & MLIR Memory Allocation',
                'Garbage Collector': 'Zero GC',
                'Compilation Speed': 'Ultra-Fast (MLIR Native)',
                'C Interoperability': 'Direct Python & C ABI interop',
                'Primary Domain': 'AI Kernels, Tensor Compilers, GPU Acceleration',
                'Ecosystem Maturity': 'Rapidly Growing (Modular MAX)'
            },
            'pros': [
                'Python-like intuitive syntax compiling to C++ / SIMD performance',
                'Direct access to GPU threads, tensor cores, and vector instructions',
                'Built natively on Multi-Level Intermediate Representation (MLIR)'
            ],
            'cons': [
                'Younger ecosystem compared to Rust and C++',
                'Tooling and community libraries still maturing'
            ]
        },
        'verdict': 'Rust is the undisputed foundation for mission-critical infrastructure, web backends, and operating systems. Mojo is the future high-velocity language for AI engineers needing Python ergonomics with CUDA-grade hardware parallelism.'
    },
    'nvidia-blackwell-vs-hopper': {
        'id': 'nvidia-blackwell-vs-hopper',
        'title': 'NVIDIA Blackwell GB200 vs Hopper H100',
        'category': 'AI Hardware & Datacenter',
        'headline': 'The Generational Leap to Exascale Liquid-Cooled Rack Supercomputing',
        'item_a': {
            'name': 'Blackwell GB200 NVL72',
            'badge': 'Rack-Scale Exascale',
            'color': '#76b900',
            'specs': {
                'Transistor Count': '208 Billion (Dual-Die)',
                'Process Node': 'Custom TSMC 4NP',
                'Interconnect Bandwidth': '10 TB/s NVLink-C2C',
                'Memory Bandwidth': '8.0 TB/s (192 GB HBM3e)',
                'FP4 Inference FLOPs': '40 PFLOPS per Dual-GPU',
                'Cooling Solution': 'Direct-to-Chip Liquid Cooling CDU',
                'Inference Speedup': '30x vs H100 for LLMs'
            },
            'pros': [
                '130 TB/s aggregate rack bandwidth acts as one giant 13.5 TB GPU',
                '25x reduction in energy consumption per token generated',
                'Native FP4 micro-tensor engine doubles inference density'
            ],
            'cons': [
                'Requires modern liquid-cooled datacenter plumbing and CDUs',
                'High infrastructure deployment investment'
            ]
        },
        'item_b': {
            'name': 'Hopper H100 SXM',
            'badge': 'Previous Gold Standard',
            'color': '#94a3b8',
            'specs': {
                'Transistor Count': '80 Billion (Single Die)',
                'Process Node': 'TSMC 4N',
                'Interconnect Bandwidth': '900 GB/s NVLink 4',
                'Memory Bandwidth': '3.35 TB/s (80 GB HBM3)',
                'FP8 Inference FLOPs': '4 PFLOPS',
                'Cooling Solution': 'Air Cooled / Liquid Optional',
                'Inference Speedup': '1x Baseline'
            },
            'pros': [
                'Extremely mature software ecosystem and cloud availability',
                'Air-cooled configurations deployable in standard racks',
                'Battle-tested reliability across all major cloud hyperscalers'
            ],
            'cons': [
                'Limited by single-die reticle constraints',
                'High power consumption when scaling to trillion-parameter models'
            ]
        },
        'verdict': 'Hopper established modern generative AI. Blackwell GB200 NVL72 transitions the world to rack-scale exascale computing, slashing token generation costs by up to 25x.'
    }
}

def get_article_quiz(blog):
    """Returns 3 curated interactive multiple-choice questions for the article."""
    title_lower = blog['title'].lower()
    category = blog['category']

    # Curated topic-specific quizzes
    if 'deepseek' in title_lower or 'reasoning' in title_lower:
        return [
            {
                'q': 'What core training breakthrough allowed DeepSeek-R1-Zero to develop reasoning capabilities?',
                'options': [
                    'Massive human supervised fine-tuning logs',
                    'Pure rule-based reinforcement learning on deterministic proof verifiers',
                    'Random token brute-forcing in inference loops'
                ],
                'correct': 1,
                'explanation': 'DeepSeek-R1-Zero proved that reasoning behaviors like self-correction and chain-of-thought emerge naturally from pure RL with math and code verification rules without human demonstrations.'
            },
            {
                'q': 'What is the primary benefit of test-time compute scaling in reasoning LLMs?',
                'options': [
                    'It shrinks the total number of weights on disk',
                    'Allocating extra thinking tokens at query time yields exponential error reduction on hard proofs',
                    'It completely eliminates the need for GPUs'
                ],
                'correct': 1,
                'explanation': 'Reasoning models can deliberate, backtrack, and verify hypotheses during generation time, dramatically boosting accuracy on math and programming benchmarks.'
            },
            {
                'q': 'What does the model do when it detects an error in its chain-of-thought?',
                'options': [
                    'Halts generation immediately and returns an error',
                    'Autonomously backtracks in scratchpad memory and tries an alternative solving path',
                    'Increases the temperature parameter to 2.0'
                ],
                'correct': 1,
                'explanation': 'Dynamic chain-of-thought enables the model to catch logical fallacies mid-generation, self-correct, and verify the refined steps before delivering the final answer.'
            }
        ]
    elif 'apple' in title_lower or 'm4' in title_lower:
        return [
            {
                'q': 'What peak memory bandwidth does the Apple Silicon M4 Max architecture deliver?',
                'options': [
                    '100 GB/s standard LPDDR5',
                    'Up to 546 GB/s Unified Memory Bandwidth',
                    '25 GB/s PCIe Gen 3'
                ],
                'correct': 1,
                'explanation': 'Apple M4 Max shatters data bus bottlenecks by delivering up to 546 GB/s of unified zero-copy memory bandwidth directly between CPU, GPU, and Neural Engine.'
            },
            {
                'q': 'How does Unified Memory Architecture (UMA) benefit local AI models like 70B parameter LLMs?',
                'options': [
                    'It removes PCIe transfer latency by sharing up to 128GB RAM across CPU, GPU, and Neural Engine without copying',
                    'It compresses model weights into low-res audio files',
                    'It forces the model to run on the cloud instead'
                ],
                'correct': 0,
                'explanation': 'Because CPU and GPU share the same memory space, multi-gigabyte neural weights don\'t need to be repeatedly copied over slow buses, allowing giant models to execute locally.'
            },
            {
                'q': 'How does Apple Private Cloud Compute (PCC) guarantee user privacy on server queries?',
                'options': [
                    'It stores user logs in an encrypted SQL database for 30 days',
                    'It runs on custom Apple Silicon servers with verifiable OS builds and zero data retention guarantees',
                    'It sends queries anonymously through Tor proxies'
                ],
                'correct': 1,
                'explanation': 'Private Cloud Compute nodes are cryptographically verifiable by independent researchers and operate statelessly with non-targetable hardware isolation.'
            }
        ]
    elif 'samsung' in title_lower or 'galaxy' in title_lower or 'foldable' in title_lower:
        return [
            {
                'q': 'What custom prime core CPU architecture powers the Snapdragon 8 Elite inside Galaxy S25?',
                'options': [
                    'Qualcomm Oryon Custom Architecture (@ 4.32 GHz)',
                    'Standard ARM Cortex-A55 clusters',
                    'Intel x86 Alder Lake'
                ],
                'correct': 0,
                'explanation': 'Snapdragon 8 Elite departs from standard big.LITTLE ARM clusters by using custom high-frequency Oryon cores hitting up to 4.32 GHz.'
            },
            {
                'q': 'What material innovation allows Samsung Tri-Fold displays to bend without creasing?',
                'options': [
                    'Thick acrylic sheets',
                    'Sub-30 micron Ultra-Thin Glass (UTG 3.0) with dual waterdrop zero-gap hinges',
                    'Paper-based optical film'
                ],
                'correct': 1,
                'explanation': 'Ultra-Thin Glass (UTG) under 30 microns combined with dual waterdrop teardrop hinges minimizes mechanical stress, rated for 500,000+ fold cycles.'
            },
            {
                'q': 'How does Samsung Galaxy AI 2.0 perform live phone call translation across 20+ languages?',
                'options': [
                    'It calls an external human call center',
                    'It runs an on-device bidirectional neural model at 16kHz with zero cloud latency',
                    'It sends text transcripts to Google Translate servers'
                ],
                'correct': 1,
                'explanation': 'Galaxy AI processes live speech locally on the Hexagon NPU, translating vocal harmonics directly in real time.'
            }
        ]
    elif 'nvidia' in title_lower or 'blackwell' in title_lower:
        return [
            {
                'q': 'How many transistors are integrated on the dual-die NVIDIA Blackwell package?',
                'options': [
                    '80 Billion transistors',
                    '208 Billion transistors',
                    '1 Trillion transistors'
                ],
                'correct': 1,
                'explanation': 'Blackwell packs 208 billion transistors across two reticle-sized TSMC 4NP dies unified via 10 TB/s NVLink-C2C.'
            },
            {
                'q': 'What new micro-tensor numerical precision does Blackwell introduce for 30x faster inference?',
                'options': [
                    'FP4 (4-bit floating point)',
                    'FP64 double precision only',
                    'Int16 fixed point'
                ],
                'correct': 0,
                'explanation': 'The 2nd-generation Transformer Engine supports FP4 precision, cutting memory bandwidth needs in half while doubling mathematical throughput.'
            },
            {
                'q': 'How does the GB200 NVL72 rack maintain thermal stability under 120kW load?',
                'options': [
                    'Giant high-speed server fans',
                    'Direct-to-chip liquid cooling with dedicated Coolant Distribution Units (CDUs)',
                    'Liquid nitrogen immersion'
                ],
                'correct': 1,
                'explanation': 'NVL72 uses closed-loop direct-to-chip liquid cooling to dissipate 120kW per rack quietly and efficiently.'
            }
        ]
    else:
        # High quality generic technical quiz based on category
        return [
            {
                'q': f'What is the core engineering goal discussed in this {category} publication?',
                'options': [
                    'Maximizing architectural throughput, security, and computational efficiency',
                    'Deprecating all legacy software and hardware unconditionally',
                    'Relying exclusively on manual human operations'
                ],
                'correct': 0,
                'explanation': f'Modern {category} engineering emphasizes architectural scalability, automated verification, and deterministic execution.'
            },
            {
                'q': 'Why is hardware-software co-design critical for next-generation systems?',
                'options': [
                    'It increases power consumption unnecessarily',
                    'Eliminating I/O and memory transfer bottlenecks unlocks logarithmic performance gains',
                    'It prevents developers from writing Python code'
                ],
                'correct': 1,
                'explanation': 'Tightly coupling software algorithms with dedicated silicon accelerators bypasses bus bottlenecks and maximizes energy efficiency.'
            },
            {
                'q': 'What is the recommended best practice for implementing modern tech architectures?',
                'options': [
                    'Writing monolithic unverified scripts with no tests',
                    'Adopting modular isolation, zero-trust security, and automated continuous testing',
                    'Ignoring memory bandwidth limits'
                ],
                'correct': 1,
                'explanation': 'Modular design paired with comprehensive verification guarantees system stability under high-concurrency production workloads.'
            }
        ]

# ----------------- COMPARE ROUTE -----------------
@app.route('/compare')
@app.route('/compare/<comparison_id>')
def compare_page(comparison_id=None):
    if not comparison_id or comparison_id not in TECH_COMPARISONS:
        comparison_id = 'apple-m4-max-vs-snapdragon-8-elite'
    
    current_comparison = TECH_COMPARISONS[comparison_id]
    all_comparisons = [
        {'id': k, 'title': v['title'], 'category': v['category'], 'headline': v['headline']}
        for k, v in TECH_COMPARISONS.items()
    ]
    return render_template(
        'compare.html',
        current=current_comparison,
        all_comparisons=all_comparisons,
        category_config=CATEGORY_CONFIG
    )

@app.route('/api/compare/<comparison_id>')
def api_compare_data(comparison_id):
    if comparison_id in TECH_COMPARISONS:
        return jsonify({'status': 'success', 'data': TECH_COMPARISONS[comparison_id]})
    return jsonify({'status': 'error', 'message': 'Comparison dataset not found'}), 404

# ----------------- RSS FEED ROUTE -----------------
@app.route('/feed.xml')
def rss_feed():
    db = get_db()
    blogs = db.execute("SELECT * FROM blogs ORDER BY created_at DESC LIMIT 30").fetchall()
    host_url = request.host_url.rstrip('/')
    
    xml_items = []
    for b in blogs:
        clean_desc = re.sub(r'<[^>]+>', ' ', b['content'])
        clean_desc = re.sub(r'#+\s*', '', clean_desc)[:350].strip()
        pub_date = str(b['created_at'])
        xml_items.append(f"""
    <item>
      <title><![CDATA[{b['title']}]]></title>
      <link>{host_url}/blog/{b['slug']}</link>
      <guid isPermaLink="true">{host_url}/blog/{b['slug']}</guid>
      <category><![CDATA[{b['category']}]]></category>
      <pubDate>{pub_date}</pubDate>
      <description><![CDATA[{clean_desc}...]]></description>
    </item>""")
    
    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>ASI TECH - Technology, AI, Science &amp; Innovation</title>
    <link>{host_url}</link>
    <description>Exploring the frontiers of Technology, Artificial Intelligence, Science, Education, and Movies.</description>
    <language>en-us</language>
    <atom:link href="{host_url}/feed.xml" rel="self" type="application/rss+xml" />
    {''.join(xml_items)}
  </channel>
</rss>"""
    from flask import Response
    return Response(rss_xml, mimetype='application/rss+xml')

# ----------------- REACTION APIS -----------------
@app.route('/api/blog/<slug>/react', methods=['POST'])
def api_react_blog(slug):
    db = get_db()
    blog = db.execute("SELECT id FROM blogs WHERE slug = ?", (slug,)).fetchone()
    if not blog:
        return jsonify({'status': 'error', 'message': 'Blog not found'}), 404
    
    data = request.get_json() or {}
    reaction_type = data.get('reaction', '').strip().lower()
    valid_reactions = {'fire', 'bulb', 'rocket', 'mindblown', 'heart'}
    
    if reaction_type not in valid_reactions:
        return jsonify({'status': 'error', 'message': 'Invalid reaction type'}), 400
    
    # Upsert reaction count
    row = db.execute(
        "SELECT count FROM blog_reactions WHERE blog_id = ? AND reaction_type = ?",
        (blog['id'], reaction_type)
    ).fetchone()
    
    if row:
        new_count = row['count'] + 1
        db.execute(
            "UPDATE blog_reactions SET count = ? WHERE blog_id = ? AND reaction_type = ?",
            (new_count, blog['id'], reaction_type)
        )
    else:
        new_count = 1
        db.execute(
            "INSERT INTO blog_reactions (blog_id, reaction_type, count) VALUES (?, ?, ?)",
            (blog['id'], reaction_type, 1)
        )
    db.commit()
    
    # Return all current reaction counts for this blog
    all_reactions = db.execute(
        "SELECT reaction_type, count FROM blog_reactions WHERE blog_id = ?",
        (blog['id'],)
    ).fetchall()
    counts = {r['reaction_type']: r['count'] for r in all_reactions}
    for r in valid_reactions:
        if r not in counts:
            counts[r] = 0
            
    return jsonify({
        'status': 'success',
        'reaction': reaction_type,
        'count': new_count,
        'reactions': counts
    })

@app.route('/api/blog/<slug>/reactions')
def api_get_reactions(slug):
    db = get_db()
    blog = db.execute("SELECT id FROM blogs WHERE slug = ?", (slug,)).fetchone()
    if not blog:
        return jsonify({'status': 'error', 'message': 'Blog not found'}), 404
    
    all_reactions = db.execute(
        "SELECT reaction_type, count FROM blog_reactions WHERE blog_id = ?",
        (blog['id'],)
    ).fetchall()
    counts = {r['reaction_type']: r['count'] for r in all_reactions}
    for r in {'fire', 'bulb', 'rocket', 'mindblown', 'heart'}:
        if r not in counts:
            counts[r] = 0
            
    return jsonify({'status': 'success', 'reactions': counts})

# ----------------- QUIZ API -----------------
@app.route('/api/quiz/<slug>')
def api_get_quiz(slug):
    db = get_db()
    blog = db.execute("SELECT id, title, category FROM blogs WHERE slug = ?", (slug,)).fetchone()
    if not blog:
        return jsonify({'status': 'error', 'message': 'Blog not found'}), 404
    
    quiz_questions = get_article_quiz(blog)
    return jsonify({'status': 'success', 'quiz': quiz_questions})

@app.route('/category/<category>')
def category_page(category):
    db = get_db()
    sort = request.args.get('sort', 'newest')
    
    order_clause = "created_at DESC"
    if sort == 'views':
        order_clause = "views DESC"
    elif sort == 'likes':
        order_clause = "likes DESC"

    blogs = db.execute(
        f"SELECT * FROM blogs WHERE category = ? ORDER BY {order_clause}",
        (category,)
    ).fetchall()
    
    categories = db.execute(
        "SELECT category, COUNT(*) as count FROM blogs GROUP BY category"
    ).fetchall()
    
    cat_info = CATEGORY_CONFIG.get(category, {
        'icon': 'fa-folder',
        'color': '#a855f7',
        'badge': 'default',
        'desc': f'Explore all articles under {category}.'
    })

    return render_template(
        'category.html',
        blogs=blogs,
        current_category=category,
        categories=categories,
        cat_info=cat_info,
        sort=sort,
        category_config=CATEGORY_CONFIG
    )

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    cat_filter = request.args.get('category', '').strip()
    db = get_db()
    
    if query:
        if cat_filter:
            blogs = db.execute(
                """SELECT * FROM blogs 
                   WHERE (title LIKE ? OR content LIKE ? OR tags LIKE ?) AND category = ?
                   ORDER BY created_at DESC""",
                (f'%{query}%', f'%{query}%', f'%{query}%', cat_filter)
            ).fetchall()
        else:
            blogs = db.execute(
                """SELECT * FROM blogs 
                   WHERE title LIKE ? OR content LIKE ? OR category LIKE ? OR tags LIKE ?
                   ORDER BY created_at DESC""",
                (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')
            ).fetchall()
    elif cat_filter:
        blogs = db.execute(
            "SELECT * FROM blogs WHERE category = ? ORDER BY created_at DESC",
            (cat_filter,)
        ).fetchall()
    else:
        blogs = []

    categories = db.execute(
        "SELECT category, COUNT(*) as count FROM blogs GROUP BY category"
    ).fetchall()

    return render_template(
        'search.html',
        blogs=blogs,
        query=query,
        cat_filter=cat_filter,
        categories=categories,
        category_config=CATEGORY_CONFIG
    )

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'results': []})
    
    db = get_db()
    rows = db.execute(
        """SELECT id, title, slug, category, created_at, read_time, title_image, content 
           FROM blogs 
           WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? OR category LIKE ?
           ORDER BY created_at DESC LIMIT 8""",
        (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')
    ).fetchall()

    results = []
    for r in rows:
        clean_text = re.sub(r'<[^>]+>', ' ', r['content'])
        clean_text = re.sub(r'#+\s*', '', clean_text)
        snippet = clean_text[:110] + '...' if len(clean_text) > 110 else clean_text
        results.append({
            'id': r['id'],
            'title': r['title'],
            'slug': r['slug'],
            'category': r['category'],
            'read_time': r['read_time'] or 3,
            'title_image': r['title_image'] or '',
            'created_at': str(r['created_at'])[:10],
            'snippet': snippet
        })

    return jsonify({'results': results})

# ==============================================================================
# ASI AI CHATBOT ROUTE
# ==============================================================================
@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    history = data.get('history', [])
    
    if not prompt:
        return jsonify({'status': 'error', 'message': 'Please provide a prompt.'}), 400
    
    response_text = ask_gemini_or_asi(prompt, history)
    return jsonify({
        'status': 'success',
        'bot_name': 'ASI',
        'engine': 'Gemini AI Engine',
        'response': response_text,
        'timestamp': datetime.now().strftime('%H:%M')
    })

@app.route('/api/blog/<slug>/eli5')
def api_blog_eli5(slug):
    db = get_db()
    blog = db.execute("SELECT id, title, slug, content, eli5_content FROM blogs WHERE slug = ?", (slug,)).fetchone()
    if not blog:
        return jsonify({'status': 'error', 'message': 'Blog not found'}), 404
    
    eli5_text = blog['eli5_content']
    if not eli5_text or not eli5_text.strip():
        eli5_text = generate_eli5_fallback(blog['title'], blog['content'])
        try:
            db.execute("UPDATE blogs SET eli5_content = ? WHERE id = ?", (eli5_text, blog['id']))
            db.commit()
        except Exception:
            pass
    
    return jsonify({
        'status': 'success',
        'slug': slug,
        'title': blog['title'],
        'eli5_raw': eli5_text,
        'eli5_html': parse_content_syntax(eli5_text),
        'read_time': calculate_read_time(eli5_text)
    })

@app.route('/api/ai/generate-eli5', methods=['POST'])
def api_generate_eli5():
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'status': 'error', 'message': 'Article content is required.'}), 400
    
    if GEMINI_API_KEY:
        try:
            prompt = f"Explain the following technical article like I am 5 years old. Use a playful metaphor/analogy, 3 key things to understand, and a simple takeaway. Use markdown headings (#, ###, -, >).\n\nTitle: {title}\nContent:\n{content[:2500]}"
            ai_text = ask_gemini_or_asi(prompt)
            if ai_text and len(ai_text) > 40:
                return jsonify({
                    'status': 'success',
                    'eli5_content': ai_text,
                    'eli5_html': parse_content_syntax(ai_text)
                })
        except Exception:
            pass
    
    fallback_text = generate_eli5_fallback(title or 'Technical Topic', content)
    return jsonify({
        'status': 'success',
        'eli5_content': fallback_text,
        'eli5_html': parse_content_syntax(fallback_text)
    })

# ==============================================================================
# USER AUTHENTICATION ROUTES (REGISTER, LOGIN, GOOGLE / GMAIL)
# ==============================================================================
@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    
    if not name or not email or not password:
        return jsonify({'status': 'error', 'message': 'All fields (Name, Email, Password) are required.'}), 400
    
    if len(password) < 6:
        return jsonify({'status': 'error', 'message': 'Password must be at least 6 characters long.'}), 400
    
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return jsonify({'status': 'error', 'message': 'An account with this email already exists. Please log in.'}), 400
    
    password_hash = generate_password_hash(password)
    avatar = name[:1].upper()
    
    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash, provider, avatar) VALUES (?, ?, ?, 'email', ?)",
        (name, email, password_hash, avatar)
    )
    db.commit()
    user_id = cursor.lastrowid
    
    session['user_id'] = user_id
    session['user_name'] = name
    session['user_email'] = email
    session['user_avatar'] = avatar
    
    return jsonify({
        'status': 'success',
        'message': f'Welcome to ASI TECH, {name}!',
        'user': {'id': user_id, 'name': name, 'email': email, 'avatar': avatar}
    })

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    
    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and Password are required.'}), 400
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    
    if not user or not user['password_hash'] or not check_password_hash(user['password_hash'], password):
        return jsonify({'status': 'error', 'message': 'Invalid email or password.'}), 401
    
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['user_avatar'] = user['avatar'] or user['name'][:1].upper()
    
    return jsonify({
        'status': 'success',
        'message': f'Welcome back, {user["name"]}!',
        'user': {'id': user['id'], 'name': user['name'], 'email': user['email'], 'avatar': session['user_avatar']}
    })

@app.route('/api/auth/google', methods=['POST'])
def auth_google():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip()
    
    if not email:
        email = f"user_{datetime.now().strftime('%M%S')}@gmail.com"
    if not name:
        name = email.split('@')[0].replace('.', ' ').title()
    
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    
    if not user:
        avatar = name[:1].upper()
        cursor = db.execute(
            "INSERT INTO users (name, email, provider, avatar) VALUES (?, ?, 'google', ?)",
            (name, email, avatar)
        )
        db.commit()
        user_id = cursor.lastrowid
    else:
        user_id = user['id']
        name = user['name']
        avatar = user['avatar'] or name[:1].upper()
    
    session['user_id'] = user_id
    session['user_name'] = name
    session['user_email'] = email
    session['user_avatar'] = avatar
    
    return jsonify({
        'status': 'success',
        'message': f'Signed in with Google as {name}!',
        'user': {'id': user_id, 'name': name, 'email': email, 'avatar': avatar}
    })

@app.route('/auth/logout')
def auth_logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)
    session.pop('user_avatar', None)
    flash('You have signed out successfully.', 'info')
    return redirect(request.referrer or url_for('home'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        
        if not name or not email or not message:
            flash('Please fill in all required fields (Name, Email, Message)!', 'error')
        else:
            db = get_db()
            db.execute(
                "INSERT INTO contacts (name, email, subject, message) VALUES (?, ?, ?, ?)",
                (name, email, subject, message)
            )
            db.commit()
            flash('Thank you for reaching out! We received your message and will respond shortly.', 'success')
            return redirect(url_for('contact'))
            
    db = get_db()
    categories = db.execute(
        "SELECT category, COUNT(*) as count FROM blogs GROUP BY category"
    ).fetchall()
    return render_template('contact.html', categories=categories, category_config=CATEGORY_CONFIG)

@app.route('/newsletter', methods=['POST'])
def newsletter():
    email = request.form.get('email', '').strip()
    if not email or '@' not in email:
        flash('Please enter a valid email address.', 'error')
        return redirect(request.referrer or url_for('home'))
    
    db = get_db()
    try:
        db.execute("INSERT INTO newsletter (email) VALUES (?)", (email,))
        db.commit()
        flash('🎉 Welcome aboard! You have subscribed to the ASI TECH newsletter.', 'success')
    except sqlite3.IntegrityError:
        flash('You are already subscribed to the ASI TECH newsletter!', 'info')
    
    return redirect(request.referrer or url_for('home'))

# ============== ADMIN ROUTES ==============

@app.route(ADMIN_URL)
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route(ADMIN_URL + '/auth', methods=['POST'])
def admin_auth():
    password = request.form.get('password', '')
    if password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        flash('Welcome to the ASI TECH Admin Suite!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Authentication failed: Invalid admin password.', 'error')
        return redirect(url_for('admin_login'))

@app.route(ADMIN_URL + '/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    db = get_db()
    blogs = db.execute("SELECT * FROM blogs ORDER BY created_at DESC").fetchall()
    reviews = db.execute("""
        SELECT reviews.*, blogs.title as blog_title, blogs.slug as blog_slug 
        FROM reviews 
        LEFT JOIN blogs ON reviews.blog_id = blogs.id 
        ORDER BY reviews.created_at DESC
    """).fetchall()
    contacts = db.execute("SELECT * FROM contacts ORDER BY created_at DESC").fetchall()
    
    total_blogs = len(blogs)
    total_views = db.execute("SELECT COALESCE(SUM(views), 0) as total FROM blogs").fetchone()['total']
    total_reviews = len(reviews)
    total_contacts = len(contacts)
    total_users = db.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
    
    return render_template(
        'admin_dashboard.html',
        blogs=blogs,
        reviews=reviews,
        contacts=contacts,
        total_blogs=total_blogs,
        total_views=total_views,
        total_reviews=total_reviews,
        total_contacts=total_contacts,
        total_users=total_users,
        category_config=CATEGORY_CONFIG
    )

@app.route(ADMIN_URL + '/create', methods=['GET', 'POST'])
def admin_create():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug = request.form.get('slug', '').strip().lower()
        category = request.form.get('category', '').strip()
        tags = request.form.get('tags', '').strip()
        author = request.form.get('author', 'ASI TECH').strip()
        is_featured = 1 if request.form.get('is_featured') == 'on' else 0
        content = request.form.get('content', '').strip()
        eli5_content = request.form.get('eli5_content', '').strip()
        if not eli5_content:
            eli5_content = generate_eli5_fallback(title, content)

        if not title or not slug or not category or not content:
            flash('Please fill in all required fields (Title, Slug, Category, Content)!', 'error')
            return redirect(url_for('admin_create'))

        read_time = calculate_read_time(content)

        title_image = None
        if 'title_image' in request.files:
            file = request.files['title_image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"title_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                title_image = filename

        inline_images = {}
        for key in request.files:
            if key.startswith('inline_image_'):
                file = request.files[key]
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"inline_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    inline_images[key] = filename

        for key, filename in inline_images.items():
            placeholder = f"[{key}]"
            content = content.replace(
                placeholder,
                f'<figure class="blog-figure"><img src="/static/uploads/{filename}" class="blog-inline-img" alt="Illustration" loading="lazy"></figure>'
            )

        db = get_db()
        try:
            db.execute(
                """INSERT INTO blogs (title, slug, title_image, content, eli5_content, category, author, tags, read_time, is_featured)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, slug, title_image, content, eli5_content, category, author or 'ASI TECH', tags, read_time, is_featured)
            )
            db.commit()
            flash(f'Article "{title}" published successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except sqlite3.IntegrityError:
            flash('URL slug already in use. Please choose a unique slug.', 'error')
            return redirect(url_for('admin_create'))

    return render_template('admin_create.html', category_config=CATEGORY_CONFIG)

@app.route(ADMIN_URL + '/edit/<int:blog_id>', methods=['GET', 'POST'])
def admin_edit(blog_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    db = get_db()
    blog = db.execute("SELECT * FROM blogs WHERE id = ?", (blog_id,)).fetchone()
    if blog is None:
        flash('Blog not found!', 'error')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug = request.form.get('slug', '').strip().lower()
        category = request.form.get('category', '').strip()
        tags = request.form.get('tags', '').strip()
        author = request.form.get('author', 'ASI TECH').strip()
        is_featured = 1 if request.form.get('is_featured') == 'on' else 0
        content = request.form.get('content', '').strip()
        eli5_content = request.form.get('eli5_content', '').strip()
        if not eli5_content:
            eli5_content = blog['eli5_content'] or generate_eli5_fallback(title, content)

        read_time = calculate_read_time(content)
        title_image = blog['title_image']

        if 'title_image' in request.files:
            file = request.files['title_image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"title_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                title_image = filename

        inline_images = {}
        for key in request.files:
            if key.startswith('inline_image_'):
                file = request.files[key]
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"inline_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    inline_images[key] = filename

        for key, filename in inline_images.items():
            placeholder = f"[{key}]"
            content = content.replace(
                placeholder,
                f'<figure class="blog-figure"><img src="/static/uploads/{filename}" class="blog-inline-img" alt="Illustration" loading="lazy"></figure>'
            )

        db.execute(
            """UPDATE blogs 
               SET title = ?, slug = ?, title_image = ?, content = ?, eli5_content = ?, category = ?, author = ?, tags = ?, read_time = ?, is_featured = ?
               WHERE id = ?""",
            (title, slug, title_image, content, eli5_content, category, author or 'ASI TECH', tags, read_time, is_featured, blog_id)
        )
        db.commit()
        flash('Blog updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_create.html', blog=blog, edit_mode=True, category_config=CATEGORY_CONFIG)

@app.route(ADMIN_URL + '/delete/<int:blog_id>')
def admin_delete(blog_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    db = get_db()
    db.execute("DELETE FROM blogs WHERE id = ?", (blog_id,))
    db.execute("DELETE FROM reviews WHERE blog_id = ?", (blog_id,))
    db.commit()
    flash('Blog and associated comments deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route(ADMIN_URL + '/contacts')
def admin_contacts():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    db = get_db()
    contacts = db.execute("SELECT * FROM contacts ORDER BY created_at DESC").fetchall()
    return render_template('admin_contacts.html', contacts=contacts)

@app.route(ADMIN_URL + '/contacts/delete/<int:contact_id>')
def admin_delete_contact(contact_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    db = get_db()
    db.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    db.commit()
    flash('Contact inquiry deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route(ADMIN_URL + '/reviews/delete/<int:review_id>')
def admin_delete_review(review_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    db = get_db()
    db.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    db.commit()
    flash('Review deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route(ADMIN_URL + '/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out securely.', 'success')
    return redirect(url_for('home'))

@app.context_processor
def inject_globals():
    db = get_db()
    categories = db.execute(
        "SELECT category, COUNT(*) as count FROM blogs GROUP BY category"
    ).fetchall()
    return dict(
        all_categories=categories,
        category_config=CATEGORY_CONFIG,
        current_user={
            'is_authenticated': bool(session.get('user_id')),
            'id': session.get('user_id'),
            'name': session.get('user_name'),
            'email': session.get('user_email'),
            'avatar': session.get('user_avatar', 'U')
        },
        now_year=datetime.now().year
    )

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
