# Bringing Big into the classroom — Narrative

_Spells and craft — what conversational programming opens for our students_

Working draft of the talk as continuous prose. Each `###` beat below corresponds to one current slide; the slide id is preserved in an HTML comment so we can rebuild `keynote.json` from this file once the narrative settles.

Editing freely is the point: rewrite, merge, split, reorder, delete. Beats without a `<!-- slide: ... -->` comment will become brand-new slides when we re-derive the deck.


---

## Opening

### Bringing Big into the classroom
<!-- slide: d4b13a60-7827-4c7c-b905-fd953a8dbde1 -->

- WCCCE 2026
- Juancho Buchanan
- Professor of The Practice
- Khoury College of Computer Science
- Vancouver campus.

### Vibe Coding vs Conversational Programming
<!-- slide: 5f02ca54-1b6c-4a3f-9e1b-8c5a0d9e1c01 -->

# Vibe Coding
- **No CS knowledge needed** — just describe the vibe and see what happens.

# Conversational Programming
- **Collaborative** — engineers and LLMs work as a team.
- The LLM is a **partner**, sparking innovation, not just providing answers.
- We lead on design, review, testing, and outcomes.

### Sundar Picha, CEO — 22 April 2026
<!-- slide: 7a4b9d12-8e3c-4d05-a2f6-1c9e0b4d5e02 -->

#  Google Cloud Next '26
- **75%** of all new code at **Google** is now **AI-generated and approved by engineers**.
- **Up from 50%** last fall.

# What their engineers do now
- Orchestrate **fully autonomous digital task forces** of agents.
- A **complex code migration**: agents + engineers, **~6× faster** than a year ago with engineers alone.
- **Gemini app on macOS**: idea → **native Swift prototype in days**, built on **Antigravity**.

### How I got here — and why this talk
<!-- slide: 4f6dc626-83d5-43e2-8ba4-14d61f676cd8 -->


---

## Section 1 — Return to academia

### Back to academia, teaching LLM-forward
<!-- slide: 3f26df8b-61b9-4cfb-9eb6-7796406882ab -->

I came back to academia excited about LLM influence on software developers

# I believe we need to teach how to use

- industry is moving there
- i want to know how to use
- so i can help my students learn.


---

## Section 2 — My history of building stuff

### Arthur C. Clarke's Third Law
<!-- slide: f37b2620-3fa0-4a58-b09d-154230b886ff -->

> "Any sufficiently advanced technology is indistinguishable from magic."
>
> — **Arthur C. Clarke**, *Profiles of the Future* (1973)

### Spells, Magic, and My Journey
<!-- slide: 6b18f9d6-fd5b-4056-918a-a75cd0381a45 -->

- In this talk, **spells** mean **coding** — languages, rituals, the work at the keyboard.
- **Magic** is what **delights the customer** — the outcome only **building** can produce.
- I fell in love with that **magic**, not with collecting **spells** for their own sake.
- You just saw **what I have been trying** in my courses since **2023**; what follows is **how I got here** — and **why** I care about **builders**, not just **spells**.

### Why I'm Here
<!-- slide: 121d9e95-4b96-48a1-a552-e61f91c2568b -->

I fell in love with **building things**.

Not with collecting spells. Not with syntax or frameworks or the latest tools.

With the **magic** — that moment when something you made delights someone else. When code becomes craft.

That's what I want for my students. Not just certified graduates. **Builders.**

And that's the thread running through everything I'm about to share with you.

### 1977
<!-- slide: 2c155803-8ca0-4672-a9d6-cc8b4fb991cc -->

- **John Loader**, maths teacher — got an account at the **University of Sussex**.
- He taught us programming (I think **FORTRAN**).
- We filled out **mark-sense cards**.
- We **mailed them in**.
- I got mine back — my incantation had been **cursed**.
- Curse this computer thing.

### 1978 — A Game on a Casio
<!-- slide: f663552b-2fb6-4f8d-be50-5c075e7c4a10 -->

# Programmable calculator.
- A **random** target on a **100×100** grid.

- You type **x** and **y**
- it answers with **distance** to the ship.
- You **close in** until you hit it.
- None of my friends wanted to understand
- They did like the game
- it was 1978

### Summer Job 1980-1984
<!-- slide: eec49a0c-db98-49f4-b4e8-764993ca849a -->

- Lead–Acid Batteries Tonolli recycling
- My uncle broke down **forklift batteries** for recycling.
- We weighed cells (**50–160 kg**),
- counted cells,
- tallied, billed Tonoly.
- First customer
- I wrote **BASIC** on a **TRS-80 Model I**
- End-of-day totals, **saved**,
- Auditable if we mistyped.

### First Time I Delighted a "Customer"
<!-- slide: e82aae96-dff1-4f99-acd0-bef0031b9739 -->

- **Me** — less pain doing the books.
- My **uncle** — faster, more accurate billing.
- Problem ->
- Understanding ->
- Do Magic incantations ->
- Uncle saw them as magical
- Happy Uncle

### Research and collaborators
<!-- slide: 0ce10e4a-ca60-4a4a-a281-f022c5f2c615 -->


### My Ph.D. Incantation: Faster Convolution
<!-- slide: 5a3cc000-4391-4270-9db4-7c1388053fef -->

- My Ph.D. was one giant **magic spell** for speed:

- Start with expensive **filter integrals** in convolution.
- **Decompose the filter** into a **basis representation**.
- **Precompute** the integral of each **basis function** with the data.
- Reuse those precomputed pieces to assemble results quickly.
- Same math, same answer — dramatically less repeated work.

# Pure magic

### Why I Pivoted to NPR Tools
<!-- slide: 409d7b9b-c6c1-4569-b2d9-48d518aec024 -->

- Non Photorealistic Rendering
- After my Ph.D., I decided to build tools for **non-CS people**.
- Medical imaging felt like a **red sea** to me.

# I wanted to explore how computers could help **artists**.
- Photorealism was largely solved.
- It became magic for magic sake
- No real visual difference.
- I was more interested in expressive tools that expanded human creativity.

### Mario Costa Sousa, Ph.D. — simulating pencil drawing
<!-- slide: 1cfed1e1-b4d9-402a-989f-91ef570ae8c8 -->

- **Mario Costa Sousa** completed a Ph.D. on **simulating pencil drawing**.
- At first we worried tools like this might **replace** artists.
- **Desmond Rochfort** — a **pencil artist** — sat on the committee.

### Desmond’s use for the tool
<!-- slide: 5bbf065a-5a45-46ea-b49b-23dcdd5a697e -->

# Desmond Rochfort is a pencil artist.

- We were worried he would be threatened.
- He taught us a lesson

# He did not like
- Style exploration, it cost too much

# He could use our simulation
- To get to the fun part

### CMU — Game Sketching
<!-- slide: e7d1f1a8-1e2c-494f-951f-58c330ba6b77 -->

- At **Carnegie Mellon**, I worked on **game sketching** — a story that **dropped out** of how I usually tell this arc.
- The **game designer** would **converse** with the setup; **characters** in the world **reacted** — **early**, almost **LLM-like** interactivity.
- Under the hood: **six puppeteers** in a **back room**, **listening** and **driving** the characters from **script** — we could **pivot fast** when the conversation changed.
- The designer **iterated** about **thirty times** in **two weeks** — **three** runs on a **heavy** day.
- The honest question: **Can we ship this?** **No** — you still have to **implement** the real thing.

### From story to curriculum
<!-- slide: 64cc806e-fcfc-41a0-8c1d-6cfb4191204b -->



---

## Section 3 — How the academy has reacted to new tech

### How the academy pushed back
<!-- slide: 3796416b-05af-466e-b80e-0e4a662e3219 -->


### "That Isn't a Real Computer"
<!-- slide: 2c78bc0a-a3b4-46f3-b764-c31caa559126 -->

- University of Windsor — I wanted coursework on my **Z-80** instead of the lab **IBM 360**.
- A professor said I did not have a **real** machine unless it was **32-bit**.
- **Punch cards** were part of training — that was how you drove the **IBM 360**.
- You had to program on **cards** to really be a **magician**.

### The Pattern Didn't Stop
<!-- slide: 0a182380-5fc8-4fcc-8640-ebd38b3c9290 -->

- **IDEs:** some faculty banned them — unless you used **vi** and **make**, it wasn't "real CS."
- **Tab completion:** a senior engineer wanted it **off** for juniors — too easy to tell who had **memorized the library incantations**.
- Same mistake: **confusing ritual with skill** — difficulty as a **proxy for merit**.

### A Colleague, Early in My Career
<!-- slide: a59301cc-5869-4b6a-b2ba-be981c5aeba5 -->

- I asked why he didn't program anymore.

# I don't need to practice.
- I already know it.

# In his mind
- Teaching CS was teaching **the spells**

# You know the spells
- **That**, to him, **was** computer science — **done**.


---

## Section 4 — My stories from the academy

### Harnessing Big Systems in Education
<!-- slide: 3be918fc-120b-47e8-bc33-b1ec8979f334 -->

# From Industry to Classroom
I transitioned from the tech industry in 2023 after serving as VP of Engineering at Staffbase
- team of **80 engineers**.  

We had **89 repositories** lacking unit test coverage.  

- we deployed **Copilot**. 
- It excelled in supporting **unit tests**, which was impressive.  

**Result:** 
- led to a **weekly increase in unit tests** across our projects.

### 2023 — Line Completion in Software Engineering
<!-- slide: 7c72bed1-4006-400d-9d72-4ae6df7c23b7 -->

I wanted the students to think about 
- The recalc engine
- The end to end testing

# LLM generated 
- test-button0
- ...
- test-button9
- test-button10

### Diving Deep into Testing
<!-- slide: 87a9d1e3-b29b-406c-acd9-9d73268876b0 -->

Let's challenge students to think critically about unit tests.

- Instead of just checking boxes, we can immerse them.
- Plunge them into code that demands understanding or they risk sinking.
- Then, we throw them lifelines—structured guidance and support.

This way, they learn not just to test, but to truly understand the impact of their work.

### Students extended the platform
<!-- slide: bf2aae11-b08a-47ba-bf57-900ceeee852a -->

# Students kept building
- A **chat feature** — added by students so students could **ask the teacher questions** right inside the system.
- A **tutorial mode** — also student-built, to onboard the next cohort.
- **Extensive functions** layered on top of the core — well beyond what the assignment asked for.

# What that told me
- Given the right scaffolding, students do not stop at the rubric.
- They extend the platform for **each other**.
- That is the kind of ownership we want — and it is exactly what conversational programming makes reachable.

### 2024 — Beginning of Agentic Work
<!-- slide: 298ac503-9342-40af-b83a-534bd3e8c41a -->

- In a **TypeScript graphics** course, students built two systems in parallel:
- a software renderer, and an **OpenGL scene renderer**.
- The point was orchestration: compare approaches, iterate, and keep both tracks moving.

### Tough Choice
<!-- slide: 22e2b7c5-e7a8-4967-b51b-a097b5c81362 -->

# Teach cutting-edge hardware  
- OpenGL is messy 
- Highlevel gets lost in the tedium
- What the machine does is not clear
# Write software renderer
- Took a long time, no fun graphics

# We can do both
- The tedium of OpenGl is handed to LLM
- The tedium of writing software rendering is lessened.

### 2025 — Software Engineering (BC Cancer Foundation)
<!-- slide: a26362d3-08e7-4245-8f4e-0db9a0891bf3 -->

- Real project context: **BC Cancer Foundation**.
- Students built a **four-language REST API** system.
- Emphasis: interoperability, contracts, and shipping across language boundaries.

### 2025 — Game Engine Programming
<!-- slide: 8b3b0619-254b-477d-aaef-ded5df8bded9 -->

- Students worked across **four languages**.
- They were **reading systems**, **using systems**, and **building games while learning** those systems.
- Weekly ritual: **How did we do with LLM?** sharing circle on wins, misses, and adjustments.

### 2026 — 5001/5002 (Intro CS + Discrete Math)
<!-- slide: e98a6215-fa52-4fe9-860d-ac4eae3f6cf0 -->

- Students received a **large existing codebase** to explore.
- Project: build educational software that explains a **discrete math** topic.
- LLMs were encouraged as **tutors** during exploration and implementation.

### 2026 — OO Programming (Shape Editor)
<!-- slide: c10fad7d-99ae-4c0b-a078-6c1e40100221 -->

- Build tasks were small: implement **Square** and **Circle** in ~50 lines each.
- Understanding tasks were large: code-walk **ObjectHolder** and **Canvas** (~500 and ~800 lines).
- Testing literacy was larger still: explain unit tests across ~**2000 lines**.
- Goal: tiny feature work plus deep system reading and explanation.


---

## The spells / discipline arc  (was: my attack on the academy)

### From Spells to Access
<!-- slide: ccf2dd4c-2b7c-4ce6-b256-25e0969ddb75 -->

# Use computer magic
- For people who could not recite the spells and incantations.


# CS for everyone.
- **Everyone** should be able to build.
- **NOT** everyone should be able to program.

### Why Computer Science?
<!-- slide: cb69c653-526f-4718-a43e-fa137e053da0 -->

# So we can build things that delight customers

- Real people with real problems, who should leave **glad** we existed.
- Everything else is in service of that.

# Theory in service of building
- What must graduates **understand**?
- What must we **teach**?
- **To whom** — future builders, researchers, or specialists — and in what **balance**?

### Mastering the Magic of Code
<!-- slide: 6ad6d0f3-a810-4064-9134-9e563a919a06 -->

# Programming languages
- First attempt to make the conversation more human

# Coding as an ancient art
- It requires practice and understanding.
- Once you grasp the 'incantations,' you can **build** amazing things.

# The curriculum grew around the spells — for good reason
- Students **needed** competency across a **large catalog**: **data structures**, flow, storage, systems.
- Teaching **spells well** was the price of **access** to the work.
- A serious **project** often landed **late** because shipping cost was high — **now** the shipping cost is **lower**, and there is **room for craft alongside the spells**.

### The spells became the discipline.
<!-- slide: f5d2cb68-5dc9-4d16-a2ca-ef28e342811f -->

- Computer programming came to **dominate** our education — because it **had to**.

# Spells are testable
- **Teach** known spells
- **Teach** more languages
- **Evaluate**: did they repeat the spells correctly?

# The book kept growing
- More **languages**, **frameworks**, **APIs** — a **four-year** catalog of coverage.
- We got **very good** at this — it is a **real achievement**.

# The new room
- With **conversational programming**, the per-spell cost is lower.
- That opens **space** to **also** teach the **craft** that turns spells into **shipped product**.

### Spells required by the ACM-Based CS Education
<!-- slide: 38be4b99-67fa-41ef-b47a-f6262f18700e -->

- **Core computation:** programming across paradigms, **algorithms**, **data structures**, and **systems** threads (architecture, OS, networks, security).
- **Engineering practice:** development process, quality, databases, collaboration.
- **Plus electives and depth** every program layers on — the hazard is **coverage** crowding out **building**.

### Magicians were paid very well
<!-- slide: a60de312-1f4f-4969-a2ba-e165e370a170 -->

# Well paid
- Because no one else could do it.

# The spells
- The vocabulary
- The rituals
- Tab or {

# Tough stuff

### Industry Needs Builders
<!-- slide: 7de99796-eafe-4669-a642-b87f9a99a321 -->

- Spells are **necessary** — you cannot do this work without them.
- Spells are **not sufficient**.
- In my career, I have had to let **four employees** go — all with **A+ averages** from Waterloo, Toronto, or Alberta.

# They knew the spells
# They had the guild documents!
- Could not **use** them on real problems
- Could not progress to **problem solving** for a customer

# The opportunity
- Teach the spells **and** the **craft** — that is what industry has always needed and what we can **finally make room for**.

### Making the Spells Easier to Cast
<!-- slide: 8eb4334d-5238-45cb-befa-7f103e029b33 -->

# Programming is hard 

- **make** — repeat the same build **ritual** without retyping every command.
- **IDEs** — edit, navigate, debug, and refactor in **one workshop**.
- **Tab completion** from **library documentation** — names and signatures **without memorizing the whole scroll**.

### Spells to Ease the Pain
<!-- slide: 16ad2e41-4ce5-4c21-af2b-0ab4cba218a3 -->

- Each wave still aimed at the same thing: **alleviate** the **excruciating grind** of casting by hand.
- **LLM line suggestion** — whole **lines** from context and intent, not just tokens.
- **Agentic conversational programming** — **describe** the goal, **iterate** in dialogue, let a **partner** carry routine spellwork.
- **Relief** and **speed** — the pattern did not stop; it **accelerated**.

### So How Has the Academy Responded?
<!-- slide: 35fdb5ad-ad42-4f24-852f-ac4207c5d229 -->

- So how has the academy responded to this challenge?
- How do we incorporate tools that actually help people build?
- A strong reaction has been: **We know our magic — leave us alone.**
- I have **lived** the pushback — policies, habits, and hallway arguments — when we tried to move beyond **pure magic**.


---

## Builders, users, and what we can do now (closing)

### Builders, users, and ranks
<!-- slide: e86832cb-bf36-49cc-8003-a53943110e56 -->


### Chisel Builders
<!-- slide: 216604f7-0618-4026-9167-0401a56a55b6 -->

- **Heat treating**
- **Alloys**
- **Tempering**
- Depth in **metal** and **process** — how the edge **holds** and **survives** the work.

### Chisel Users
<!-- slide: cf9ac370-d9e0-4547-baee-1a6acca90587 -->

- **Sharpening**
- **Hitting** — angle, force, control
- **Using** — reading the **grain**, stopping cuts, **safety**
- Mastery at the **bench**, not at the **crucible**.

### Builders vs Users
<!-- slide: 66dde2dc-56e0-4149-98e5-9607989c0418 -->

- The **chisel builder** needs to understand **what the chisel is for** — the job shapes the steel.
- The **chisel user** does not need to understand **how the chisel was made** at all.
- **Two** expertises — both **legitimate** — **not** the same curriculum.

### Wizards — Career Path
<!-- slide: 2381e5f5-6e54-48c1-a351-ff7182ee90ae -->

- Let's look at the **career path** of our **wizards**.
- **Chisel** was about **which expertise** we teach; these ranks are about **how responsibility grows** in the hall.
- **Youngens**
- **Midlings**
- **Elders**

### Youngens
<!-- slide: eef7a4df-18ea-4ab4-9689-343942b45d79 -->

- **Youngens** **cast the spells they are given** — from **scrolls**, **seals**, and the master's **examples**.
- The work is **clear glyphs**, **correct ritual**, and **steady execution**.
- This is **not** meant as a lifelong seat in the circle — the aim is to **grow out** of it.
- **Up-or-out**: learn fast, rise in rank, or find another path.

### Midlings
<!-- slide: c6165e55-2057-4668-8f5a-34a4d0d68a1e -->

- **Midlings** **solve the problems they are handed** — break the **work** into **pieces**, pick **how** to **proceed**, own the **outcome** within the **charter**.
- They move through the **guild hall** with others and get **unstuck** on their own more often.
- This **is** a real path: work that makes the **hall** stronger.
- Many strong **midlings** **never** become **elders** — and that can be **completely fine**.

### Elders
<!-- slide: e3010384-7aa6-41cb-816e-a4f8965a57a9 -->

- **Elders** weigh the **guild's fortunes** and **name the problems** worth confronting.
- They set **direction**, **manage risk**, and choose **what not** to conjure.
- They turn **messy reality** into **quests** other **wizards** can actually **run**.

### Plain engineering language
<!-- slide: 018dcb1e-eb8b-4062-9833-8cd359640b59 -->


### Back to Programming
<!-- slide: 945af64a-5f1b-4aee-bb89-657cc130d054 -->

- **Same ranks** — **youngens**, **midlings**, and **elders** were just **story names**.
- From here on: **junior**, **mid-level**, and **senior** engineers — **programming**, **shipping**, and **teams** in plain language.

### From Senior to Junior: How Tasks Flow
<!-- slide: ad7ab361-0568-42b6-8a2b-ba5b0dea51f0 -->

- A **senior** frames the problem, constraints, and acceptance criteria.
- Work is split into tasks with examples, tests, and checkpoints.
- **Juniors** implement; mids integrate and refine; seniors review and adjust scope.
- The system is a pipeline of intent — not a solo spellcasting contest.

### The Pattern Repeats
<!-- slide: 05e7bc73-8136-4773-a9e0-feb8c3581478 -->

- This is the **backbone** of our industry — how serious systems get built and kept running.
- Industry **trains juniors** into the **middle band** that carries the load — at **Amazon**, people say **AWS** stands on **SDE2** (mid-level engineers).
- **LLMs** shift the **junior execution loop** — employers want **mid-level contribution** sooner.
- The bar rises on **judgment**, **integration**, **ownership**, **shipping** — and **customer-facing** work that is **reliable**, **tested**, **secure**, **useful**.
- Tools make you **faster**; the shipped **artifact** still demands **deeper** understanding, not shallower.

### Counselors Know the Gap
<!-- slide: 856f468e-0e7d-49b5-9def-288074664f56 -->

- We **did** notice the gap between spell-mastery and shipping.
- Counselors would say: **do a project** — push **final-year** work where you **finally ship** something the world might want, as if the first three years were **rehearsal**.
- The job market still asks for people who **delight customers** — not **only** people who ace the canon.

### Co-ops: Industry Teaches What We Didn’t
<!-- slide: 31252e4e-d167-4da3-bfd3-7b69bb81227a -->

- **Co-operative education** became common because universities struggled to teach **how to build** in the core curriculum.
- So we leaned on **terms in industry** — apprenticeships off-campus — to supply the missing experience.
- That helped.
- It also quietly admitted the gap: **building** was not what the lecture hall was optimized for.

### Reframing
<!-- slide: 6813fcfd-95d6-4421-827b-534264fec7fe -->

# Not only:
- How do we **AI-proof** our teaching of spells?

# Also:
- How do we teach the **craft** of building — good, secure product for problems that won't fit last decade's homework?

# Infrastructure for learning
- **Keep teaching the spells** — that does not go away.
- **Add the craft**: managing a conversational engineering partner to ship real work.

### What we can do now
<!-- slide: b10ea8e4-aeb2-44f9-9feb-ef3881021b10 -->


### The Most Exciting Shift in My Career
<!-- slide: 5cde0626-a29e-4359-8a2e-554b4aaaaf65 -->

- **LLM-assisted coding** is the **most exciting** thing that has happened in my **career** — I want that **energy** in this room.
- **Example:** I learned a **new language** and shipped a **functional spreadsheet for children** for my **course** — **four weeks** from cold start to **something they could use**.
- That **pace**, with me still **owning** design and correctness, is what **rekindled** my joy in **building**.
- I want students to see that **speed is possible** — with **standards**, **tests**, and **honesty** — not magic without responsibility.

### Read Code in Systems That Matter
<!-- slide: 2f8eae72-8f58-46e7-8801-3c3f9ed31409 -->

- Help students **learn to read code** by **building systems** that **solve customer problems**.
- Put them in **problem spaces** they can **grow inside** — where files, APIs, and failures **mean something**.
- When the **customer** is real, **reading** is not a spelling drill — it is how you **keep the promise** you shipped.

### Give Them the Messy Charter
<!-- slide: 60421627-2ee9-451d-b1b8-095110b8f56a -->

- We have the **opportunity** to assign **large, ill-defined problems** — the kind industry actually wrestles with.
- Students can start performing **at mid-level** sooner when the **brief** is real and **mentors** stay close.

### Stay Builders for the Next Wave
<!-- slide: 0352a509-8b64-4c48-839b-2e2789faff37 -->

- **Building never ends** — we must be **practitioners of building**, not replayers of the old canon.
- If we **teach spells**, we can end up like that **colleague**: *I already know it — **I'm done**.*
- If we **train builders**, every **LLM advance** **excites us more** — and we become **exceptional partners** in our **students'** and **colleagues'** **growth**.

### Let's Build
<!-- slide: b234d7ad-276e-4014-b6de-265de40a376d -->

# Dr Richard Caron
- **1983** — numerical analysis: Never before have we been so capable of **computing numbers**, **our job** is to ensure they are **correct**.

# Me (with respect to Dr Caron)
- Never before have we been able to **generate so much code**. **Our job** is to teach our students to do that **correctly**.

# Let us practice building.

### A Student Asked: Vibe Coding vs Us?
<!-- slide: 30de3cb1-0c39-4090-a506-ea9eec58bf00 -->

- A student asked: **What's the difference between vibe coding and us?**
- My answer — back to where we started this talk:
- **Vibe coding** is **product management** with an oracle — describe, accept, ship.
- **What we do** is **conversational programming** — we **understand the machine**, we **examine** what was produced, **trace** why it works (or fails), and **fix** it with intent.
- That is the difference between **guessing output** and **building systems** that hold up for real people.

### Our Responsibility
<!-- slide: 44290e10-5a3b-4e20-81f0-ded368595803 -->

- **Teach the spells** — still essential. Our students cannot converse with an engineering partner without them.
- **Also teach the craft** — the magic that **delights the customer**: design, review, tests, security, shipping with intent.
- **Builders** make the world **better by building**: safer, clearer, more **humane** systems — one **honest** release at a time.
- When we **train builders**, we give the next generation the habit of **asking what should exist** — and the **craft** to **make it real**.


---

## Appendix — abandoned slides

Slides parked from earlier drafts. Mine for content; not part of the live arc.

### Abandoned slides
<!-- slide: 2639e4d2-f521-4f94-8207-12cb35268cf0 -->

The slides after this point are no longer part of the active arc.
Kept here so we can mine them for content if needed.

### Future Classroom Dynamics
<!-- slide: 2dbda6fb-1308-4821-b553-a0c7f4de660e -->

# Rethinking Our Approach  
- AI now drives most new code, with engineers giving the thumbs up.  

# Key skills becoming essential: 
- **reading code** 
- **design**
- **testing**
- **security** 

# Solid CS foundations remain crucial
# Understanding is key to good approvals.  
- This is the change we need in education.

### Empowering Students Through Big Projects
<!-- slide: 28572fab-d726-4fce-94c5-b4d857bbcd84 -->

# Unlocking Tools for Builders
- **Big projects** give students access to all the tools they need.
- Work with **large code bases** that reflect real-world scenarios.

# Collaborating with Technology
- Partner with **LLMs** to expand problem-solving capabilities.
- Experience the fusion of creativity and technical skills.

# A Pathway to Mastery
- Foster **hands-on experiences** that ignite inspiration.
- Focus on building a strong foundation in **CS fundamentals**!

### Dr Richard Caron — The Other Side
<!-- slide: 4f24956a-5553-4879-833a-a93faa374067 -->

- **Dr Richard Caron** showed the positive side.
- In **numerical analysis**, he got excited to understand the **8-bit** machine.
- Same department — a different stance: **curiosity** instead of **gatekeeping**.

### A Better Machine — Same Ritual
<!-- slide: 8d293112-31c6-4da5-9292-ff3a1f0132e8 -->

- Year three: Computing Services bought a **DEC VAX 780** — better than the 360, a **room of terminals**.
- The **same professor** had the VAX wired as a **line-editor front end to the 360**: edit like punch cards, **batch to the 360**, pick up printouts at the **I/O window**.
- The **VAX still wasn't "real."** The **360** stayed the center of gravity.

### Back to Building
<!-- slide: 0c0001e2-be2c-4edd-992f-b43288d0086a -->

- **Back to building** — what we keep circling.
- Industry does not want **A+ students** who can only **recite the spells**.
- It wants **skilled magicians** who **use** them to **delight customers**.
