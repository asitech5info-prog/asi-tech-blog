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

        db.commit()
        
        count = cursor.execute("SELECT COUNT(*) FROM blogs").fetchone()[0]
        has_empty_eli5 = cursor.execute("SELECT COUNT(*) FROM blogs WHERE eli5_content IS NULL OR eli5_content = ''").fetchone()[0]
        if count < 10 or has_empty_eli5 > 0:
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
        (5, "Chris Anderson", "chris@systems-dev.com", 5, "Rust for safe backends and Mojo for AI kernels is the exact combination we are adopting at our startup.")
    ]
    for r in sample_reviews:
        db.execute(
            """INSERT INTO reviews (blog_id, name, email, rating, comment)
               VALUES (?, ?, ?, ?, ?)""",
            r
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
# ASI AI CHATBOT LOGIC (GEMINI ENGINE)
# ==============================================================================
def ask_gemini_or_asi(prompt, history=None):
    prompt_lower = prompt.lower().strip()
    
    # Try calling Google Gemini API if key is present
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            system_instruction = (
                "You are ASI, an ultra-intelligent, friendly, and expert AI Assistant for 'ASI TECH' (a premier Tech, AI, Science, and Cinema journal). "
                "Provide accurate, insightful, beautifully structured markdown responses with code snippets when relevant."
            )
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{system_instruction}\n\nUser Question: {prompt}"}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 600
                }
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=7) as response:
                result = json.loads(response.read().decode('utf-8'))
                text_response = result['candidates'][0]['content']['parts'][0]['text']
                return text_response
        except Exception:
            pass  # Fallback to local intelligent neural engine

    # High-Intelligence Contextual Fallback Knowledge Engine (ASI)
    if any(k in prompt_lower for k in ['who are you', 'what is your name', 'what are you']):
        return (
            "👋 Hello! I am **ASI**, your enterprise AI research assistant on **ASI TECH**.\n\n"
            "### Core Capabilities:\n"
            "- **Artificial Intelligence & LLMs:** Test-time compute, DeepSeek-R1, reasoning architectures, and agentic workflows.\n"
            "- **Systems Engineering:** High-performance code in Rust, Zig, Mojo, C++, and Go.\n"
            "- **Deep Tech & Science:** Quantum computing, 800V solid-state batteries, fusion energy, and orbital space mechanics.\n"
            "- **Virtual Production & VFX:** Real-time Unreal Engine 5.5 volumes and diffusion video models (Sora).\n\n"
            "What technical topic or engineering challenge can I assist you with today?"
        )
    
    elif any(k in prompt_lower for k in ['deepseek', 'r1', 'reasoning', 'o3', 'claude 3.7']):
        return (
            "🧠 **DeepSeek-R1, Claude 3.7 & Reasoning LLMs Breakdown**\n\n"
            "Reasoning models represent a fundamental paradigm shift toward **test-time compute scaling**.\n\n"
            "### Architectural Innovations:\n"
            "1. **Pure Rule-Based RL (DeepSeek-R1-Zero):** Reinforcement learning directly on deterministic verification rules (math proofs, code execution) without supervised human demonstrations.\n"
            "2. **Dynamic Chain-of-Thought:** The model autonomously allocates thinking tokens to backtrack, hypothesize, verify sub-goals, and self-correct.\n"
            "3. **Inference Scaling Laws:** Compute allocated at query time yields logarithmic error reduction on complex multi-step reasoning benchmarks.\n\n"
            "```python\n"
            "# Example: Multi-Step Reasoning Verification Loop\n"
            "def verify_reasoning_step(hypothesis, verification_rule):\n"
            "    state = execute_verification(hypothesis)\n"
            "    if not state.is_valid:\n"
            "        return backtrack_and_refine(hypothesis, state.error_trace)\n"
            "    return state.validated_solution\n"
            "```\n\n"
            "📖 *Read our deep-dive publication: 'DeepSeek-R1, Claude 3.7 Sonnet & Reasoning LLMs' in the AI category.*"
        )

    elif any(k in prompt_lower for k in ['quantum', 'qubit', 'superposition', 'entanglement']):
        return (
            "⚛️ **Quantum Computing & AI Convergence Overview**\n\n"
            "Quantum information systems utilize quantum mechanical principles to navigate exponentially large dimensional spaces.\n\n"
            "### Core Principles:\n"
            "- **Quantum Superposition:** Qubits exist as linear superpositions $|\\psi\\rangle = \\alpha|0\\rangle + \\beta|1\\rangle$, evaluating combinatorial states in parallel.\n"
            "- **Quantum Entanglement:** Correlated quantum states enable instant non-local state synchronization.\n"
            "- **Parameterized Quantum Circuits (PQC):** Hybrid quantum-classical optimization layers utilized in Quantum Machine Learning (QML).\n\n"
            "```python\n"
            "# Example: Quantum Superposition Simulation via Qiskit\n"
            "from qiskit import QuantumCircuit\n"
            "\n"
            "qc = QuantumCircuit(2)\n"
            "qc.h(0)         # Hadamard gate -> Superposition\n"
            "qc.cx(0, 1)     # CNOT gate -> Bell State Entanglement\n"
            "print(qc.draw())\n"
            "```\n\n"
            "Explore our full research article in the **Science & Space** section!"
        )

    elif any(k in prompt_lower for k in ['battery', 'ev', 'solid state', 'charging', '800v']):
        return (
            "⚡ **Solid-State Battery & 800V Architecture Breakthroughs**\n\n"
            "The transition from liquid lithium-ion to all-solid-state battery (ASSB) cells represents a transformative leap for electric mobility.\n\n"
            "### Key Engineering Metrics:\n"
            "- **Energy Density:** Reaches **1,000 Wh/L volumetric** density (up from ~650 Wh/L in standard Li-ion).\n"
            "- **Thermal Runaway Immunity:** Solid ceramic/sulfide electrolytes prevent volatile thermal ignition even under mechanical puncturing.\n"
            "- **800V / 900V Charging:** Enables sustained 350-400 kW DC fast-charging with 10-minute 10-80% charge cycles.\n"
            "- **Dendrite Prevention:** High-shear solid-state separators eliminate lithium dendrite formation, extending lifecycle beyond 2,500 full cycles."
        )

    elif any(k in prompt_lower for k in ['rust', 'zig', 'mojo', 'systems', 'c++']):
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

    elif any(k in prompt_lower for k in ['roadmap', 'learn', 'engineer', 'career', 'study']):
        return (
            "🚀 **2026 Full-Stack AI Engineer Roadmap**\n\n"
            "The modern AI engineering stack has evolved beyond simple wrapper APIs:\n\n"
            "### Phase 1: Core Mathematical & Tensor Foundations\n"
            "- Linear Algebra, PyTorch 2.5, CUDA Memory Hierarchy, Triton Kernels.\n\n"
            "### Phase 2: Agentic Engineering & Structured Reasoning\n"
            "- Tool orchestration, schema-constrained JSON sampling, and multi-agent consensus protocols.\n\n"
            "### Phase 3: Advanced Retrieval-Augmented Generation (RAG)\n"
            "- Hybrid Sparse/Dense vector search, ColBERT token-level reranking, and Knowledge Graph-RAG.\n\n"
            "### Phase 4: Production LLMOps & Inference Optimization\n"
            "- FP8/AWQ quantization, vLLM continuous batching, Prefix Caching, and low-latency speculative decoding."
        )

    elif any(k in prompt_lower for k in ['sora', 'cinema', 'video', 'movie', 'vfx', 'unreal']):
        return (
            "🎬 **Generative Cinema, Sora & Virtual Production (ICVFX)**\n\n"
            "The intersection of deep learning and cinematic production is reshaping modern filmmaking:\n\n"
            "### Technical Breakdown:\n"
            "- **Spacetime Latent Patches:** Models like Sora compress raw video into 3D spacetime volumes, training diffusion transformers across varying resolutions and aspect ratios.\n"
            "- **In-Camera Visual Effects (ICVFX):** High-density LED walls powered by Unreal Engine 5.5 render photorealistic backgrounds in real time, synchronizing camera tracking parallax with zero green screen spill.\n"
            "- **Neural Rendering & 3D Gaussian Splatting:** Instant reconstruction of complex physical sets with realistic specular lighting."
        )
    
    elif any(k in prompt_lower for k in ['hi', 'hello', 'hey', 'greetings', 'help']):
        return (
            "✨ Hello! I am **ASI**, your intelligent research assistant on **ASI TECH**.\n\n"
            "### How I can assist you today:\n"
            "- 🧠 **AI & Machine Learning:** DeepSeek-R1, reasoning architectures, transformers, and agent systems.\n"
            "- ⚛️ **Deep Tech & Physics:** Quantum algorithms, solid-state batteries, and orbital space mechanics.\n"
            "- 🦀 **Systems & Code:** Code reviews and comparisons in Rust, Zig, Mojo, Python, and C++.\n"
            "- 🚀 **Engineering Guidance:** Technical roadmap and career milestones for 2026.\n\n"
            "Feel free to ask any technical question or pick a quick topic from above!"
        )
    
    else:
        return (
            f"💡 **ASI Research Insight: '{prompt}'**\n\n"
            f"Regarding **{prompt}**, engineering and research frontiers in 2026 emphasize computational efficiency, robust reliability, and deterministic system scaling.\n\n"
            "### Architectural Focus Areas:\n"
            "1. **High-Throughput Acceleration:** Leveraging specialized tensor accelerators, kernel fusion, and memory-bandwidth-bound optimization.\n"
            "2. **Reliability & Security:** Zero-trust architecture, automated formal verification, and telemetry observability.\n"
            "3. **Extensibility:** Composable microservices with asynchronous non-blocking event loops.\n\n"
            "Would you like a deeper architectural breakdown, code implementation, or related articles from our journal?"
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
    total_blogs = db.execute("SELECT COUNT(*) as count FROM blogs").fetchone()['count']
    total_views = db.execute("SELECT COALESCE(SUM(views), 0) as total FROM blogs").fetchone()['total']
    total_reviews = db.execute("SELECT COUNT(*) as count FROM reviews").fetchone()['count']
    total_contacts = db.execute("SELECT COUNT(*) as count FROM contacts").fetchone()['count']
    total_users = db.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
    
    return render_template(
        'admin_dashboard.html',
        blogs=blogs,
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
    flash('Message deleted.', 'success')
    return redirect(url_for('admin_contacts'))

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
    app.run(host='0.0.0.0', port=5000, debug=True)
