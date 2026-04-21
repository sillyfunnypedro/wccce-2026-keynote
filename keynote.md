---
title: From Anvils to APIs
subtitle: Two Transitions, One Pattern
author: WCCCE 2026
footer: WCCCE 2026
---

--- title

# From Anvils to APIs

**Two Transitions, One Pattern**

**WCCCE 2026**

---

# Why Computer Science?

**So we can build things that delight customers** — real people with real problems, who should leave **glad** we existed.

Everything else is in service of that.

---

# Where We Drifted

We began to treat **incantations** — syntax, rituals, the canon — as if they were **the degree**.

We **forgot** (or stopped saying out loud) that the mission was **teaching students to build**.

**Knowing the spells is not the same as shipping something that matters.**

---

# What We Taught Was Incantations

Computers demanded **precise spells** before anything useful happened: **source → machine language** — hence the **compiler** and toolchain.

Year one: **semicolons, tabs, initialization** — if you're lucky, what happens to **data in memory**.

We rarely started from **the problem we were solving**.

---

# The Ladder Goes Up

**Algorithms, Big-O** — domain incantations. You learn the **classics**; **previous magicians** wrote them.

**Databases / SQL** — store data so you can **reach it fast** and **ask questions**. The spells get **closer to English**: *select… where…*

---

# The Pinnacle — and the Trap

Then the **big magic**: **low-level to machine-level** — compilers, translation — often the **crown** of the undergrad program.

We **digest** the book; you **give it back** looking like our template. Grades reward **mimicry**.

By **year three**, many students still haven't **built** anything except **proof they echoed the spellbook**.

---

# Counselors Know the Gap

They push **final-year** courses where you **finally ship** something the world might want — as if the first three years were **rehearsal**.

The job market still asks for people who **delight customers** — not **only** people who ace the canon.

---

# CS Was Never Only About Coding

We taught it that way when we weren't **builders**.

**You** know the incantations. **So does every LLM.**

The job is no longer **teaching incantations**. It's **teaching how to build**.

---

# I've Always Been a Builder

What follows isn't random biography. It's the same instinct over and over: **make something** that **changes what happens next**.

Institutions kept foregrounding **incantations**. I kept reaching for **builds** — games, workarounds, tools for real work.

---

# Grade 2 — Multiplication Tables

The teacher kept the tables on her desk. I went home and taught myself to **read upside down**.

My mother asked why. I said: she's showing me the answers — I'll read upside down so I don't have to drill the tables.

I still read upside down. I never really memorized the tables. It hasn't hurt my career.

---

# My First "ChatGPT"

It wasn't magic — it was figuring out the **prompt**: what to learn, how to position myself, to get the data I needed.

---

# 1977 — A Game on a Casio

**Programmable calculator.** A **random** target on a **100×100** grid. You type **x** and **y**; it answers with **distance** to the ship. You **close in** until you hit it.

Crude **Minesweeper**-style deduction — tight memory, tiny screen — and **fun** to play.

---

# "That Isn't a Real Computer"

University of Windsor — I wanted to do coursework on my **Z-80** instead of the lab **IBM 360**.

A professor said I didn't have a **real** machine: if it wasn't **32-bit**, it didn't count.

Part of my training, he said, was **punch cards** — because that's how you drove the **IBM 360**.

---

# A Better Machine — Same Ritual

Year three: Computing Services bought a **DEC VAX 780** — better than the 360, a **room of terminals**.

The **same professor** had the VAX wired as a **line-editor front end to the 360**: edit like punch cards, **batch to the 360**, pick up printouts at the **IOL window**.

The **VAX still wasn't "real."** The **360** stayed the center of gravity.

---

# The Pattern Didn't Stop

**IDEs:** some faculty banned them — unless you used **vi** and **make**, it wasn't "real CS."

**Tab completion:** a senior engineer wanted it **off** for juniors — too easy to tell who had **memorized the library incantations**.

Same mistake: **confusing ritual with skill** — difficulty as a **proxy for merit**.

---

# A Colleague, Early in My Career

I asked why he didn't program anymore.

**"I don't need to practice. I already know it."**

In his model, teaching CS was teaching **incantations** — A's meant you'd learned them — so you **were** a computer scientist. **Done.**

---

# Magicians and Wizards

The world doesn't want **magicians who repeat the old magic**.

It wants **wizards** who **see problems**, build **solutions**, and leave **people glad**.

---

# That Summer — Lead–Acid Batteries

My uncle broke down **forklift batteries** for recycling. We weighed cells (**50–160 kg**), counted cells, tallied, billed the **plant**.

I was the tally. I wrote **BASIC** on a **TRS-80 Model I** — end-of-day totals, **saved**, **auditable** if we mistyped.

---

# First Time I Delighted a "Customer"

**Me** — less pain doing the books. My **uncle** — faster, more accurate billing.

The machine the professor said wasn't for **real** CS was for **real** work — checkable, useful, **human**.

---

# A Morning in 1905

A blacksmith didn't wake up one morning to find horses gone and Model Ts parked outside his shop.

The change **crept in**.

First it was a neighbor asking if he could straighten a bent axle.
Then it was fabricating a bracket that didn't exist yet because no parts catalog did either.

---

# Running example: a real person with a real problem

**Summer job — my uncle’s shop.** Forklift batteries in for recycling.

The actual work: **weigh** each unit on the scale, **record how many cells**, **tally** everything for the day, **submit the bill** to the recycling plant — and deal with the fact that people **mistype** and still need the books to **close**.

Not a programming problem on day one. A **human** losing time and trust to arithmetic and paperwork.

---

# Understand the problem

What does **done** look like? Faster tally, fewer errors, and numbers you can **defend** if the plant or your own crew asks “where did this come from?”

What are the **constraints**? Who runs it, on what machine, with what patience — **no IT department**, no appetite for cleverness that only the author understands.

You don’t open an editor yet. You **interview the work** until the success criteria are boringly clear.

---

# Understand how to automate it — that creates sub-problems

Automation isn’t one miracle button. It’s **decomposition**.

Typical threads: **capture** weights and counts safely → **accumulate** totals correctly → **end-of-day report** the business trusts → **persist / correct** enough to back out a bad entry without replaying everything.

Each thread is a **small bet** you can test against reality before you pretend you’re “done.”

---

# For each sub-problem: code. Then put the pieces together.

Ship the **smallest proof** per piece (input loop, running totals, printable tally, save or “fix last line” — tune to your story on stage).

**Integration is the product:** shared data, clear handoffs, and **one error** shouldn’t corrupt the whole day.

Goal: something **they** can run — and **defend** to the plant — not a program only you understand.

---

# Happy customer

My uncle wasn’t grading my **style**. He wanted the **day closed clean**: less time reconciling, numbers that held up.

**First time I felt what this work is for** — a **delighted customer** (even when the customer was family).

That’s the bar we skip when we teach **incantations** instead of **building for someone**.

---

# The Part We Get Wrong

The **horseshoe** was a known problem — heat, shape, nail it on.

The **automobile** was something else: combustion, drivetrain, electrical systems, tolerances the smith had never seen.

---

# The Thing Being Built Got Harder

The **complexity** forced the transition — not the mere arrival of a new machine.

Understanding metal and stress didn't become **less** important. It became **more** — the automobile demanded a **deeper** version of the same insight.

---

# Tools That Match the Problem

The pneumatic press. The torque wrench. The diagnostic gauge.

They didn't replace expertise. They were **necessary** because the problem **outgrew** the hammer and anvil.

---

# The Blacksmith Who Thrived

Not the one who kept shoeing horses from **stubbornness**.

Not the one who **panicked** and threw away what he knew.

The one who saw the real skill was **how metal behaves under force** — carried into a **harder** problem with **new tools**.

--- quote

# We're living through that same kind of morning right now.

---

# The Developer in 2026

An LLM can emit a function from a prompt — that doesn't make the work **simple**.

What we're asked to build is **more ambitious**: distributed, integrated, cross-platform, **always on**.

---

# The Pattern Repeats

LLM tooling can make you **faster**.

The **artifact** still demands **deeper** understanding — not shallower.

New tools because the **problem got harder** — and the tools **require more** judgment, not less.

--- quote

# Mistake the tool for the skill → build fast, debug forever.

# Refuse the tool entirely → build carefully, ship never.

---

# Who Will Thrive

Not those who think **typing syntax** was the job.

Not those who think **prompting** replaces **knowing what the system does**.

The skill was always **decomposing problems**, **seeing systems**, knowing what **correct** looks like.

---

# The Garage

The shop became a **garage**. It didn't need **fewer** skills — it needed **different** ones, same foundation, **harder** brief.

Same for every IDE with an **AI tab** next to the terminal.

--- quote

# The question isn't only "how do we teach when students have AI?"

# It's how we prepare them for work that is **fundamentally more complex** than a decade ago.

---

# Reframing

**Not:** How do we teach when students have AI?

**But:** How do we teach **building** for problems that won't fit last decade's homework shapes?

The transition is **deeper understanding** — with tools that match the **real** problem.

That's the transition. That's **always** been the transition.
