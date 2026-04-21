# Stashed ideas (WCCCE keynote)

Raw fragments — promote into `keynote.md` when ready.

**Keynote through-line (v1):** *I’ve always been a builder* — personal stories are evidence; school kept offering incantations; the red thread is **shipping** things (games, tools, workarounds) that change outcomes.

**Provocations — strong statements for argument (cross-cutting, draft):**

- **Computer science is not a typing contest.** If your degree certifies keystrokes, you are selling a **pre-industrial** idea of the job.
- **Any assessment a model can pass is not evidence of human mastery** — it is evidence that you assigned **the wrong task**.
- **Correctness converges.** Two honest professionals solving the same problem **should** produce similar code; calling that “plagiarism” is **category error**.
- **Grading source files is grading the tool.** The moment generation is cheap, **the file is not the student**.
- **Integrity isn’t “did you suffer?”** Integrity is **can you explain, defend, break, and fix** what ships.
- **We don’t need more people who can recite syntax.** We need people who can **frame problems, choose trade-offs, and own consequences**.

---

## 2026-04-08 — Incantations vs. building

**Thesis (rough — sharpened for debate):**

CS in industry was never *about* hand-authoring every line; we taught it that way because courses were easy to **grade**, not because they were true to the work. That contract is **broken**: the LLM knows the incantations **cold**.

**The final challenge:**

You are professors — you know the incantations. So does every LLM.

The goal is no longer to teach incantations, but rather to teach how to **build**.

So: become builders, fall in love with building, and teach building to your students.

**Implied beat (maybe too sharp for stage — tune later):**

If you do not do this, then retire — which is why *I* am not retiring.

**Supporting line:**

Teaching coding was a lazy way (but necessary) — **and it is no longer defensible as the center of the curriculum.**

---

## 2026-04-08 — Grade 2, upside-down reading, “first ChatGPT”

**Story (stash — tighten for stage):**

In grade 2, during multiplication tables, the teacher kept the tables printed on her desk. I was already interested in messing with the system, so I went home and taught myself to read upside down.

My mother caught me practicing and asked why. I told her the teacher was effectively showing me the quiz answers on her desk, and I was going to read upside down so I wouldn’t have to drill my times tables. That’s what I did — I can still read upside down — and I never really memorized the tables. It hasn’t hurt my career.

**Punchline / bridge:**

That was my first “something like ChatGPT”: not magic, just figuring out the **prompt** (how to position myself, what to learn) to get the data I needed.

---

## 2026-04-08 — Incantations, compilers, and CS1

**Argument (stash):**

Computers traditionally demanded very precise **incantations** before you could use them for anything actually useful. The basic communication problem is translating a pseudo-mathematical language into machine language — hence the **compiler** (and the whole toolchain).

CS programs have tended to spend the first year teaching students to *speak* that language. That’s the first layer of incantations: where the semicolons go, where the tabs go, what initializing a variable *means* — and if you’re lucky, what those incantations do to the underlying representation of data.

But we **never actually talk about the problems we’re trying to solve**.

**Possible slide beats:** compiler as translator; CS1 as syntax boot camp; gap between representation and purpose.

---

## 2026-04-08 — Algorithms, Big-O, and “previous magicians”

**Argument (stash):**

Next we move to **slightly more complicated, domain-specific incantations**. We ask students to build on logic for processing data — the algorithms the field has found that work *reasonably well in reasonable time*. We introduce the magical yardstick **Big-O notation**.

Students are expected to **understand** these richer incantations — but they will **almost never have to invent** them, because **previous magicians** already did.

**Possible slide beats:** curriculum as inherited spellbook; analysis without authorship; tension between “know the classics” and “ship something that matters.”

---

## 2026-04-08 — Specialized incantations: data you can *ask* (databases / SQL)

**Argument (stash) — refines the ladder:**

Once students have a **broad base of basic incantations** *and* a sense of **how expensive** those operations can be (cost models, asymptotics — the “price” of magic), they hit the **next layer: specialized incantations about data**.

We already told them something about **storing** data; now the pitch shifts: store and arrange it so you can **reach it quickly** and **interrogate it** — ask questions of the data. That opens a whole new spellbook: **database queries**.

What’s interesting here: these incantations are **much closer to English**. You’re speaking at a **more general level** about the data — not just shuffling machine-level detail — e.g. *select everything in this set that satisfies these conditions*. That’s the **next level of magic**: declarative, set-oriented talk about what you want *from* the data.

**Possible slide beats:** from “how to say it to the machine” → “how to say what you want from the world the data describes”; SQL as almost-natural language; contrast with low-level syntax incantations.

---

## 2026-04-08 — The compiler layer as “pinnacle”; mimicry as learning; still not building

**Argument (stash) — curriculum arc + critique:**

So far: **level-one incantations** (syntax, foundations), then **domain-specific** layers (algorithms, data/query magic, etc.). Then comes a *especially* privileged set of spells: the ones you write so you can **translate** lower-level incantations **into machine-level** incantations — the **compiler / translation** story (however your department frames it).

This is often treated as a **pinnacle of undergraduate CS**: heavy magic, taught from the stance **we know this; you don’t** — so we **digest** it and hand you the digest. The “value add” of the course is that **we** packaged it; you **give it back** in a form that **looks like what we gave you**. The grade rewards **successful mimicry**. Underneath, it can feel like: *you’re being praised for echoing the incantations we modeled.*

**Punchline:** By the end of **year three**, you’re supposedly in training for a career that is **about building things** — and many students **still haven’t built anything** that isn’t an assignment shaped to prove they repeated the magic correctly.

**Broader pattern:** All we’ve done so far is **present a spellbook** and ask students to **reproduce** it in a way that **matches our template** — and we call that **learning the magic**.

**Counselors / structure (anecdotal beat):** Career counselors often push students, in the **final year**, toward **courses where they finally start to make something** the outside world might recognize as useful — as if **three years of apprenticeship** were preparation for *beginning* to touch “real” work.

**What the industry actually wants (closing line):** People who can look at **human problems**, understand them, and **turn them into** the right **arcane incantations** (systems, code, data, interfaces) so they **delight customers** — not people who only excel at **rehearsing** the canon.

**Note:** If “Emily” was a real example, replace the generic “many students” with the name; if it was dictation for “and they,” the stash above uses the generic on purpose.

---

## 2026-04-08 — “I don’t program anymore; I already know it” (colleague anecdote)

**Story (stash — tighten / anonymize for stage as needed):**

In my **first job as a professor** (before industry), I asked a colleague **why he didn’t program anymore**. His answer was very telling of that era: he said he **doesn’t need to practice** — **because he already knows it**.

In his mental model, **teaching CS** was teaching the **performance of incantations** that prepared people to **become computer scientists** — and computer scientists were simply people who could **earn A’s** all the way through **learning the incantations**. Once you **know all the incantations**, you **are** a computer scientist — so **you’re done**. No further making required.

**Contrast / punchline:** That isn’t the real world. The world doesn’t want **magicians who simply repeat the old magic**. It wants **wizards** who can **look around**, **see problems that need solving**, and **deliver solutions** so that **people are glad** (happy customers / users / communities).

**Possible slide beats:** “knowing” vs “doing”; faculty modeling (or not) the builder habit; short quote-style slide with the colleague line if you’re comfortable with it ethically.

---

## 2026-04-08 — “That isn’t a real computer” (gatekeeping tech stack as CS)

**Thesis (stash):**

Much of CS education’s history is **faculty defending whatever stack is already institutionalized** and calling **that** “computer science” — while dismissing what students (and the world) are actually reaching for.

**Story 1 — Z-80 vs IBM 360 + punch cards (undergrad, year 2):**

I got access to a **Z-80** personal computer and wanted to do coursework on it instead of the department’s **IBM 360** (the **32-bit** machine the course assumed). I asked a professor if I could use my Z-80 for assignments. He said I **did not have a real computer** — that if it wasn’t a **32-bit** machine, it **wasn’t real**. He also insisted that part of my training as a computer scientist was learning **punch cards**, because that’s how you drove the **IBM 360** at **University of Windsor**.

**Story 2 — VAX 780 “isn’t real” either; punch cards by proxy (undergrad, year 3, Windsor):**

In my **third year**, **Computing Services** bought a **Digital Equipment VAX 780** — a **much better** machine than the **IBM 360**, with a **room full of terminals** so students could use the new environment.

The **same professor** who had blocked my **Z-80** insisted the **VAX 780** be set up as a **line-editor front end for the IBM 360**: you edited in an environment that **looked and behaved like you were still editing punch cards**, then submitted a **batch job to the 360**, then went to the **IOL window** to pick up your **printout**. Why? Because in that worldview the **VAX still wasn’t a “real computer”** — the **360** remained the **real** center of gravity.

**Story 3 — IDEs vs “real CS”:**

When **IDEs** arrived, some faculty **banned** them: unless you used **vi** and **make**, you weren’t doing **real computer science**. I’ve heard echoes of that logic **recently**, though thankfully many people have moved on.

**Story 4 — tab completion and “too easy to evaluate juniors”:**

When IDEs gained **tab completion** on function calls, a **senior engineer** at a company I worked at wanted it **turned off** for juniors — it made the job **too easy**, so he couldn’t judge how “good” they were. His implicit model: a strong programmer **had memorized** the **arcane incantations** of the **current** library version.

**Thread:** Same mistake repeated — **confusing the tool / ritual with the skill**, and using difficulty as a **proxy for merit**.

**Possible slide beats:** Windsor trilogy: **Z-80** (not real) → **IBM 360 + cards** (real) → **VAX 780** (better hardware, still treated as fake) feeding the **same batch / punch-card ritual**; then jump to IDE / tab-completion stories; LLM parallel optional.

---

## 2026-04-08 — Lead–acid forklift batteries, Model I BASIC, first “delighted customer”

**Story (stash — tighten for stage):**

That **summer** I went home. My **uncle** ran a business **breaking down lead–acid forklift batteries** for recycling. Billing worked like this: **weigh** each battery on a scale, **record how many cells** it had (cells could run **~50–160 kg**), **tally** everything, and **submit the bill** to the **recycling plant** we contracted with.

I wrote a **BASIC** program on my **Radio Shack TRS-80 Model I** (Z-80–based home machine) to **enter** cell weights and counts per battery. At **end of day** it produced an **accurate, printable tally** we could **audit**; data was **saved** so we could **correct** the running total if we’d mistyped something.

**What clicked:** It was the first time I felt what this stuff was **for** — I made a **real person’s** life easier (**mine**, I was the one doing the tallies), and my **uncle** (my boss in that job) was **genuinely impressed**: **less time** reconciling weights, **more accuracy**. First time I **delighted a customer** — even though the “customer” was family and me.

**Bridge to keynote themes:** *building* beats *incantations*; “science / CS” as **reducing pain** and **earning trust** with something **checkable** (audit trail), not grades on mimicry.

**Possible slide beats:** contrast “professor says your Z-80 isn’t real” with “same machine class, real payroll impact”; optional photo of Model I or forklift battery as texture (permissions / taste).

---

## 2026-04-08 — 1977: Casio calculator “battleship / minesweeper” game

**Story (stash — tighten for stage):**

**1977** — I wrote a game on a **Casio programmable calculator**.

- **Grid:** conceptually **100×100** (however the device could represent it).
- **Setup:** the program picks a **random hidden point** (the “ship” / target).
- **Play:** you enter **x** and **y**; the calculator returns the **distance** to the target.
- **Goal:** home in and **hit** the ship.

**Texture:** Crude, but a lot like **Minesweeper**-style deduction — **fun to actually play**.

**Bridge to keynote themes:** **building** for **delight** (even toy delight) on **absurdly constrained** hardware; predates the TRS-80 / Windsor era — **play** as motivation, not grades.

**Possible slide beats:** “before the machines they called ‘real’”; pair with grade-2 upside-down story as **early pattern: games + systems thinking**; photo of a period Casio programmable if you can source one.

---

## 2026-04-10 — Plagiarism vs. professional sameness in CS (slide section)

**Opening slide (exact vibe):**

**Plagiarism: I stole this idea.**

(Optional subtitle beat: *In CS, following good practice often makes everyone’s code look the same — and that isn’t theft.*)

**Thesis (stash):**

Academic integrity frameworks imported **plagiarism** from fields where **voice and originality of expression** are the point. In much of **undergraduate CS**, we are not grading novel prose; we are grading whether students can **apply canonical patterns** (idioms, APIs, safe memory discipline, language conventions). **Good engineering converges** — formatters, linters, Stack Overflow idioms, textbook solutions, and “the one obvious way” to satisfy a spec. Treating **similarity** as **sin** mis-measures what we say we teach.

**Debate lines (lift to slides):**

- **Plagiarism protects authorship.** In CS1, we are usually **not assigning authorship** — we are assigning **competence**. Different moral.
- **If two solutions are identical because the problem admits one clean answer, that is success, not theft.**
- **Honor codes that treat “looks like the internet” as cheating** accidentally punish **students who learned the standard** — and reward **students who write weird, wrong code** that slips past the detector.
- **Originality is not a virtue in a safety-critical merge.** We want **boring, correct, reviewed** code — not a **unique snowflake** `for`-loop.

**How we’ve usually framed plagiarism (functional definition):**

- **Passing off someone else’s work as your own** — especially **words** or **distinctive creative choices** you did not originate.
- **Institutional use:** protect **fair grading**, certify **individual competence**, and in humanities/arts protect **authorship** and **original contribution**.

**Why plagiarism rules matter (where they fit):**

- **Creative and subjective fields:** essays, poetry, criticism, research claims — the **expression** or the **novel claim** *is* the artifact. Copying without attribution is fraud about **intellectual origin** and **credit**.
- **Professional norms:** we still care about **licensing**, **attribution**, and **not misrepresenting** what you personally verified.

**Why “plagiarism” is often the wrong lens for most of undergrad CS:**

- **Convergent solutions:** the assignment has a **unique correct structure**; two students who **both learned well** will submit **structurally identical** programs.
- **Industry practice:** we **want** shared style guides, patterns, and reuse — **DRY**, libraries, “boring” code that matches the team.
- **Detectors and policy:** similarity scores and “AI detectors” **punish competence** and **punish following instructions** (use the standard library, match the API in the handout).

**Pivot — what to do instead:**

- Move **earlier** into **larger, messier projects** that require **system design**: trade-offs, decomposition, interfaces, testing strategy, failure modes — not “implement `sort()` from the book.”
- **Assessment shifts** from “did you type unique characters?” to “can you **justify** and **defend** a design?” — including **artifacts of the process**: sketches, revisions, **the trace of a design conversation** with an LLM (prompts, iterations, what you rejected and why).
- The **non-plagiarized** thing is no longer the **line-by-line text**; it’s the **unique outcome of a design path** — your problem, your constraints, your integration — and evidence that **you** steered the build.

**Possible slide beats:**

- Side-by-side: “canonical solution” vs “plagiarism panic” — same code, two stories (one honest, one copied); **only process evidence** separates them → that’s the pedagogical point.
- One-liner: **Originality in CS is often in architecture, not in parentheses.**
- Bridge to keynote: **builders** are judged on **what they shipped** and **why**, not on novelty of boilerplate.

---

## 2026-04-10 — Don’t evaluate students on their code (LLMs will write it)

**Thesis (strong claim — stash):**

**Stop grading code as proof of learning.** Not “less weight on code” — **stop treating the source file as the exam.** In every plausible future, **routine implementation is generated**; there is **no rollback** to a world where **solo authorship** of standard solutions is the job. If your rubric rewards **typing**, you are measuring **labor**, not **capability** — and you are **obsolete**.

**Debate lines (lift to slides):**

- **The compiler already broke “handcrafted bits”; the LLM breaks “handcrafted source.”** Education must follow where **value migrates**.
- **You are not fighting cheating — you are fighting economics.** Generation is **cheap**; attention to **correctness** is the scarce good.
- **A transcript that certifies “wrote 10,000 lines alone” will soon read like a transcript that certifies “long division without a calculator.”** Admirable in a museum; **irrelevant** on the job.
- **If the student passes when the model passes, your question was not about the student.**

**What that implies:**

- **Shift the unit of assessment** to what a human must still own: **problem framing**, **requirements**, **trade-offs**, **architecture**, **test strategy**, **debugging judgment**, **security and ethics**, **explaining failure modes**, **operating** what was built — and **revision under critique** (oral, portfolio, live troubleshooting).
- **Code may still appear** in submissions, but as **evidence in context** (e.g., can you walk the call graph, justify this API choice, defend this invariant?), not as **proxy for understanding** the way we used it when typing was scarce.
- **Align with practice:** professionals already **direct** generators and **review** output; education should train **orchestration and accountability**, not **solo keystroke authenticity**.

**Steel man — what they’ll say in Q&A (short ripostes):**

- *“They must learn fundamentals.”* → **Fundamentals are models and invariants — proof is prediction, debugging, and explanation**, not empty-handed syntax under exam conditions.
- *“They’ll never learn if the machine does it.”* → **Then grade the failure modes:** change the spec, break the build, ask for the invariant — **stress the human**, not the tokenizer.
- *“Industry still interviews with coding.”* → **Industry is also scrambling**; your job is to teach **what outlasts this year’s interview format** — **design, responsibility, verification**.

**Tension to acknowledge (optional beat — don’t derail the keynote):**

- Early courses sometimes need **constrained exercises** so novices **see** how machines work; even then, the **learning outcome** is not “authored every line” but **can predict behavior, fix bugs, and reason about the model of execution**. (If even that is eventually scaffolded by AI, the **assessment still moves upstack** — prediction, explanation, modification — not “did you produce the text.”)

**Possible slide beats:**

- **“If you grade the file, you’re grading ChatGPT.”**
- Timeline slide: **compilers** removed the moral value of **machine code**; **LLMs** remove the moral value of **boilerplate source** — what’s left is **design and responsibility**.
- One-liner: **We don’t need CS graduates who type; we need graduates who can ship and defend.**

---

## 2026-04-10 — Video game course v2: drift, LLM limits, SHA-256 “build receipts” (teaching story)

**Story (stash — tighten / anonymize for stage as needed):**

**Video game course, version 2:** bump the class number, copy the project into a new directory, add features across **seven lessons**. Over time, **unintended drift** showed up — files that **should not have been edited** had been touched. I watched this happen as early as **lesson four**.

**First fix (lesson four):** I built a small **LLM-assisted workflow**: have the model **ingest the tree of files** and **report what had changed** — good enough when the project was still **small and simple**.

**Failure mode (lesson seven):** the codebase had grown **too complex** for that approach. The “read everything and tell me what’s wrong” prompt **stopped scaling** — classic **context / reasoning ceiling**.

**Second fix (engineering response):** Stop and **design a system**. For **each class’s build**, record a **SHA-256 fingerprint** (checksum) per artifact — a **receipt** for “what this lesson’s snapshot *is*.” Generate a **report** of **which files diverged** from the expected baseline. Then **use the LLM surgically**: not “understand the whole repo,” but **compare this snapshot to that one**, **between which lessons** the drift appeared, and **whether each change was justified** (intentional feature vs. accidental edit).

**Punchline for the keynote:**

That’s **real** CS teaching content: **know the model’s limits**, **build tooling** when naive prompting fails, **reduce entropy** with deterministic checks (hashes, reports), and **pair human judgment** with LLM assistance on **bounded** subproblems. **This** is the kind of thing we should be teaching **students** — not “prompt harder,” but **systems thinking + verification + escalation when the tool breaks down**.

**Possible slide beats:**

- Diagram: **v1 strategy** (LLM reads entire tree) → **hits wall** → **v2 strategy** (hashes + diff report + targeted LLM).
- One-liner: **When the oracle gets tired, give it an audit trail.**

---

## References — AI-resistant / resilient assessment & GenAI in education

Literature rarely uses the exact phrase “AI-proofing”; search terms that work: **AI-resistant assessment**, **AI-resilient assessment**, **authentic assessment** + **generative AI**, **academic integrity** + **higher education**.

### Peer-reviewed & preprints (with DOIs)

1. **Alkouk, W. A., & Khlaif, Z. N. (2024).** *AI-resistant assessments in higher education: practical insights from faculty training workshops.* **Frontiers in Education**, 9, 1499495. https://doi.org/10.3389/feduc.2024.1499495

2. **Perkins, G. (2026).** *Resilient assessment in the age of AI: authentic design and the case for verbal examinations in business education.* **Assessment & Evaluation in Higher Education**. https://doi.org/10.1080/02602938.2026.2644516

3. **Ding, K. (2025–2026).** *Designing AI-Resilient Assessments Using Interconnected Problems: A Theoretically Grounded and Empirically Validated Framework.* **arXiv** (cs.CY). https://doi.org/10.48550/arXiv.2512.10758 — empirical angle on **interconnected problems** vs modular homework; computing/data-education context.

4. Authentic assessment + GenAI (Taylor & Francis): *Embracing a new world: authentic assessment designs in an age of generative artificial intelligence (GenAI)* — verify full author list on publisher page. https://doi.org/10.1080/13603108.2025.2601741

5. **Systematic review (2024–2025):** *The Evolving Landscape of AI in Education: A Systematic Review of Contemporary Research (2024–2025)* — listed on ResearchGate; prefer **final journal citation** if available, not only RG. https://www.researchgate.net/publication/399328411_The_Evolving_Landscape_of_AI_in_Education_A_Systematic_Review_of_Contemporary_Research_2024-2025

6. **Ardito, L. (2025).** *Generative AI detection in higher education assessments.* **New Directions for Teaching and Learning** (Wiley). https://doi.org/10.1002/tl.20624 — detection / integrity strand (often contrasted with design-based “resilience”).

7. Survey-style overview (verify venue before citing as peer-reviewed): *Artificial Intelligence in Higher Education Assessment: Opportunities, Challenges and Pedagogical Considerations* — ResearchGate landing page: https://www.researchgate.net/publication/393618066_Artificial_Intelligence_in_Higher_Education_Assessment_Opportunities_Challenges_and_Pedagogical_Considerations

### Policy / framing (not journal papers)

- **UNESCO** — *What’s worth measuring? The future of assessment in the AI age*: https://www.unesco.org/en/articles/whats-worth-measuring-future-assessment-ai-age

### Handy search strings

- `"AI-resistant" assessment higher education`
- `"AI-resilient" assessment`
- `"authentic assessment" "generative AI"`

**Journals to trawl:** *Assessment & Evaluation in Higher Education*, *Computers and Education: Artificial Intelligence*, *Frontiers in Education*, *International Journal of Educational Technology in Higher Education*.

---

## References — AI enhancing teaching (beyond rote learning & recall-heavy testing)

Scholarly and policy work that argues AI can support teaching by moving **away from rote memorization and recall-heavy testing** toward deeper learning, competence, and alternative assessment. (Many sources also warn about over-reliance; pair “advocacy” items with systematic reviews.)

### Explicitly framing AI + teaching vs. rote / factual recall

1. **Ma et al. (2025).** *Preparing Students for an AI-Driven World: Generative AI and Curriculum Reform in Higher Education.* **Frontiers of Digital Education** (Springer). https://link.springer.com/article/10.1007/s44366-025-0067-6 — curriculum reform toward problem-solving and higher-order skills; GenAI changes the value of factual recall.

2. **Teaching Cognitive Reasoning Processes Rather Than Factual Recall in AI-Supported Educational Environments** — ResearchGate listing; verify venue/year before citing. https://www.researchgate.net/publication/400253771_Teaching_Cognitive_Reasoning_Processes_Rather_Than_Factual_Recall_in_AI-_Supported_Educational_Environments

3. **Ni Uanachain & Aouad.** *Generative AI in Education: Rethinking Learning, Assessment & Student Agency for the AI Era* — ResearchGate listing. https://www.researchgate.net/publication/396168151_Generative_AI_in_Education_Rethinking_Learning_Assessment_Student_Agency_for_the_AI_Era — rethinking assessment beyond memorization-heavy practices.

### Assessment reform (often tied to “beyond the exam”)

4. *Is AI changing learning and assessment as we know it? Evidence from a ChatGPT experiment and a conceptual framework* — **Heliyon** (Elsevier). https://www.sciencedirect.com/science/article/pii/S2405844024019844

5. **HEPI (2026).** *What generative AI reveals about assessment reform in higher education* — policy / think-tank (not a journal article). https://www.hepi.ac.uk/2026/02/06/what-generative-ai-reveals-about-assessment-reform-in-higher-education/

### Personalized / adaptive AI (“mastery” vs. shallow use)

6. *Artificial intelligence in personalized learning: A global systematic review of current advancements and shaping future opportunities* — **Computers and Education: Artificial Intelligence** (ScienceDirect). https://www.sciencedirect.com/science/article/pii/S2590291125008447

7. *Artificial intelligence-based personalised learning in education: a systematic literature review* — **Discover Artificial Intelligence** (Springer). https://link.springer.com/article/10.1007/s44163-025-00598-x

8. *Mastering knowledge: the impact of generative AI on student learning outcomes* — **Studies in Higher Education** (Taylor & Francis, 2025). https://www.tandfonline.com/doi/full/10.1080/03075079.2025.2487570 — how students use GenAI in relation to mastery vs. shallow use.

### Handy search strings

- `generative AI` `curriculum reform` `higher education` `rote`
- `personalized learning` `artificial intelligence` `systematic review`
- `assessment reform` `generative AI` `higher education`

---

## References — What does it mean to *know* something? (instant access, search, LLMs)

Themes: **access ≠ understanding**; **extended cognition** (when is the tool “part of” thinking?); **cognitive offloading** (performance vs. durable knowledge); **epistemic agency** (judgment, verification, intellectual virtue).

### Books & canonical philosophy (still cited in AI debates)

1. **Lynch, M. P. (2016).** *The Internet of Us: Knowing More and Understanding Less in the Age of Big Data.* W. W. Norton. — introduces **“Google-knowing”**: fast lookup vs. integrated **understanding**; democracy of knowledge vs. **echo chambers**; not about LLMs but sets the vocabulary for “knowing with machines.” Author page: https://michael-lynch.philosophy.uconn.edu/books/

2. **Clark, A., & Chalmers, D. (1998).** “The Extended Mind.” — classic argument that cognition (and by extension some “knowing”) can **span brain + environment** when tools are tightly coupled (Otto’s notebook). Gateway to all “smartphone / internet as extended mind” discussion.

3. **Pritchard, D.** *Extended Epistemology* / **extended knowledge** program — when does technology **facilitate** vs. **constitute** knowledge? Virtue-reliability angle. Overview: https://philpapers.org/rec/PRIEK-3 — also **socially extended scientific knowledge** (e.g. Frontiers in Psychology, 2022): https://doi.org/10.3389/fpsyg.2022.894738

### Recent peer-reviewed (LLMs + epistemology / mind)

4. **Clark, A., et al. (2025).** *Extending Minds with Generative AI.* **Nature Communications.** https://doi.org/10.1038/s41467-025-59906-9 — GenAI as **amplification / coupling** in a Clark-style cognitive ecology (“natural-born cyborgs”).

5. **Smart, P. R., Clark, A., & Clowes, R. W. (2025).** *ChatGPT, extended: large language models and the extended mind.* **Synthese.** https://doi.org/10.1007/s11229-025-05046-y — LLMs and the extended mind thesis (incl. RAG / “digital Andy” style demonstration).

6. **Malfatti, F. I. (or as published).** *ChatGPT, Education, and Understanding.* **Social Epistemology** (Taylor & Francis, 2025). https://doi.org/10.1080/02691728.2025.2449599 — philosophical angle on **understanding** vs. mere answers in educational use of ChatGPT.

7. **SSRN working paper:** *Epistemology in the Age of AI: Rethinking Knowledge…* https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6182658 — check for updated venue if formally published.

8. *Philosophical leadership in education: Rethinking pedagogy in an AI-driven world* — **Computers and Education: Artificial Intelligence** (ScienceDirect). https://www.sciencedirect.com/science/article/pii/S2590291126002640 — pedagogy + philosophy framing.

### Cognitive science / “outsourced mind”

9. Review / empirical strand on **cognitive offloading**: consequences for memory and metacognition (e.g. “Consequences of cognitive offloading…” — **PMC**): https://pmc.ncbi.nlm.nih.gov/articles/PMC8358584/

10. **Risk, R., & Gilbert, S. J.** *Extended Cognition and the Internet* — **PMC** discussion piece: https://pmc.ncbi.nlm.nih.gov/articles/PMC6961510/

### Information literacy & practice (not pure philosophy)

11. **ALA (2025).** *Reframing Information-Seeking in the Age of Generative AI* (PDF). https://www.ala.org/sites/default/files/2025-03/ReframingInformation-SeekingintheAgeofGenerativeAI.pdf

### Talks, podcasts & blog threads (starting points)

12. YouTube search title (verify speaker/context before citing): *“How ChatGPT is fueling an existential crisis in education”* — https://www.youtube.com/watch?v=JCLRz-tRZy0 — popular framing of “what is learning if answers are free?”

13. **Daily Nous** (2022): *“Talking philosophy with ChatGPT”* — early public philosophy thread on LLMs: https://dailynous.com/2022/12/02/talking-philosophy-with-chatgpt/

14. **Carl Hendricks** (UBC blog, 2023): *“Early thoughts on ChatGPT & writing philosophy”* — practitioner reflexivity: https://blogs.ubc.ca/chendricks/2023/01/11/early-thoughts-chatgpt-writing-philosophy/

15. **Cedarville CTL:** *ChatGPT’s Philosophy of Education* — synthesis for teaching (not peer-reviewed): https://ctl.cedarville.edu/wp/chatgpts-philosophy-of-education/

### Handy search strings

- `extended knowledge` Pritchard smartphone
- `cognitive offloading` memory education
- `Google-knowing` Lynch
- `ChatGPT` `understanding` `social epistemology`
- `generative AI` `epistemic agency`
