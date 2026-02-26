import re

with open('/Users/maikermota/DevLocal/abides_marl/blog/02_from_poc_to_modular_engine.md', 'r') as f:
    content = f.read()

# Replace Header and Intro
header_original = """# Rebuilding ABIDES from Scratch: A Developer's Journey into Market Microstructure

> I decided to rebuild the ABIDES simulator from the ground up. Not a fork. Not a wrapper. A full reimplementation—matching engine, kernel, agents, visualization—guided by the original paper but written line by line with my own hands. This is the story of what I learned, what broke, and what eventually clicked across four intense release cycles.

---

## Table of Contents

1. [Why Rebuild?](#1-why-rebuild)
2. [v0.1.2 — The Matching Engine That Kept Crashing](#2-v012--the-matching-engine-that-kept-crashing)
3. [v0.1.3 — Making Time Feel Real](#3-v013--making-time-feel-real)
4. [v0.1.4 — The Day I Deleted Direct Access](#4-v014--the-day-i-deleted-direct-access)
5. [v0.1.5 — When the Terminal Couldn't Keep Up](#5-v015--when-the-terminal-couldnt-keep-up)
6. [Where It Stands Now](#6-where-it-stands-now)
7. [What's Next](#7-whats-next)

---

## 1. Why Rebuild?

ABIDES is an impressive piece of academic software. The original codebase, developed at J.P. Morgan AI Research, provides a rich multi-agent simulation environment for financial markets. But when I tried to use it for my own MARL experiments, I kept hitting walls. The code was tightly coupled, hard to extend, and—most importantly—I didn't _understand_ it well enough to trust it.

So I made a decision that most people would call reckless: I would rebuild the entire thing from zero. Not because the original was bad, but because I wanted to internalize every invariant, every design trade-off, every subtle interaction between the matching engine and the agents. If I was going to train RL agents in this environment, I needed to know exactly what was happening under the hood.

What follows is a chronicle of that rebuild, told version by version."""

header_new = """# Market Microstructure Engineering: Building an ABIDES-MARL Simulator from Scratch (Part 2)

**Status:** _Work in Progress_
**Stack:** Python, Discrete Event Simulation, DearPyGui

---

> In [Part 1](./01_starting_journey_abides_marl.md), we established the foundational architecture of a Discrete Event Multi-Agent Simulation (DEMAS) to mirror the framework proposed in the **ABIDES-MARL** paper. We built a basic `v0.1.0` Proof of Concept (PoC) with a simple matching engine and heuristic agents. 
> 
> Moving from a basic PoC to a production-ready, modular engine meant throwing out the shortcuts. Not a fork of the original J.P. Morgan code, nor just a wrapper. A full reimplementation from the ground up. This article is the story of what I learned, what broke, and what eventually clicked across four intense release cycles (v0.1.2 to v0.1.5) as we laid the formal groundwork before plugging in the neural networks.

---

## Table of Contents

1. [From PoC to a Robust Engine](#1-from-poc-to-a-robust-engine)
2. [v0.1.2 — The Matching Engine That Kept Crashing](#2-v012--the-matching-engine-that-kept-crashing)
3. [v0.1.3 — Making Time Feel Real](#3-v013--making-time-feel-real)
4. [v0.1.4 — Phase 1: Formalizing Agents and Deleting Direct Access](#4-v014--phase-1-formalizing-agents-and-deleting-direct-access)
5. [v0.1.5 — When the Terminal Couldn't Keep Up](#5-v015--when-the-terminal-couldnt-keep-up)
6. [Where It Stands Now](#6-where-it-stands-now)
7. [What's Next: The RL Interface](#7-whats-next-the-rl-interface)

---

## 1. From PoC to a Robust Engine

In Part 1, I showed a minimal `v0.1.0` implementation. It worked, but it was fragile. ABIDES is an impressive piece of academic software, but trying to scale the initial naive PoC for my own MARL experiments led me to hit walls. The code was tightly coupled, hard to extend, and—most importantly—I didn't _understand_ deeply enough every invariant and subtle interaction between the matching engine and the agents.

If I was going to train Reinforcement Learning (RL) agents in this environment, I needed an engine that could handle asynchronous delays, realistic network latency, and sophisticated heuristic agents (like Bayesian Value Agents and Adaptive Market Makers) that act as the true "market context." 

What follows is a chronicle of migrating our PoC into a modular, high-performance engine, fulfilling the **Phase 1: Agent Formalization** of our roadmap, told release by release."""

content = content.replace(header_original, header_new)

content = content.replace(
    "## 4. v0.1.4 — The Day I Deleted Direct Access",
    "## 4. v0.1.4 — Phase 1: Formalizing Agents and Deleting Direct Access"
)

val_agent_original = """### The Value Agent: My First Bayesian Filter

With the infrastructure solid, I turned to building more sophisticated agents. The `ValueAgent` was the most intellectually rewarding part of this entire project. It maintains a Bayesian belief about the asset's fundamental value, which follows a mean-reverting Ornstein-Uhlenbeck process:"""

val_agent_new = """### The Value Agent: My First Bayesian Filter

With the infrastructure solid, it was time to tackle **Phase 1: Agent Formalization** from our roadmap—replacing simple heuristic thresholds with formal economic models. The `ValueAgent` (our informed tracker) was the most intellectually rewarding part of this entire project. It maintains a Bayesian belief about the asset's fundamental value, which follows a mean-reverting Ornstein-Uhlenbeck process:"""

content = content.replace(val_agent_original, val_agent_new)

liq_agent_original = """### The Liquidity Trader: Urgency Under Pressure

The `LiquidityTrader` models institutional execution: it must acquire $Q$ units by a deadline $T$, balancing execution quality against the risk of not completing. I modeled urgency as:"""

liq_agent_new = """### The Liquidity Trader: Urgency Under Pressure

Also as planned in Phase 1, the `LiquidityTrader` models institutional execution constraint by a quadratic risk penalty $\\phi$. It must acquire $Q$ units by a deadline $T$, balancing execution quality against the risk of not completing. I modeled urgency as:"""

content = content.replace(liq_agent_original, liq_agent_new)


conclusion_original = """## 7. What's Next

The architecture is deliberately designed for what comes next: **reinforcement learning agents**. The `Agent` ABC already exposes `get_observation()` and `get_reward()`—abstract methods waiting for a real implementation. When I drop in a PPO or SAC agent, it will inherit from `Agent` directly, receive the same messages through the same Kernel, and trade against the heuristic population I've spent four versions building and hardening.

That's the whole point of this rebuild. I didn't fork ABIDES to add a feature. I _reconstructed_ it from first principles so that every component—from the heap tuple format to the Kalman gain equation—is something I understand deeply enough to explain, debug, and extend.

The matching engine is hardened. The agents are formalized. The visualization is live.

Now it's time to let the machines learn.
"""

conclusion_new = """## 7. What's Next: The RL Interface

The architecture is deliberately designed for what comes next in our roadmap (**Phase 2: RL Interface**): **reinforcement learning agents**. The `Agent` ABC already exposes `get_observation()` and `get_reward()`—abstract methods waiting for a real implementation. 

When I drop in a PPO or SAC algorithm via a Gymnasium Wrapper, the agent will inherit from `Agent` directly, receive the same async messages through the same Kernel, and trade against the formal heuristic population I've spent four versions building and hardening.

That's the whole point of this rebuild. I didn't fork ABIDES to add a feature. I _reconstructed_ it from first principles so that every component—from the heap tuple format to the Kalman gain equation—is something I understand deeply enough to explain, debug, and extend.

The matching engine is hardened. The heuristic agents are formalized. The visualization is live.

Now that the simulator is robust, we are ready to build the Gymnasium environment. _Stay tuned for Part 3, where we will bridge this discrete-event system with standard Deep RL libraries._
"""

content = content.replace(conclusion_original, conclusion_new)

# Table summary replace
table_row_old = "| v0.1.4  | **Information Opacity** | Request-Response protocol, Kalman Filter agents, state machines, cancellation security |"
table_row_new = "| v0.1.4  | **Information Opacity** | Request-Response protocol, Phase 1 Agent Formalization (Kalman, Urgency), state machines |"
content = content.replace(table_row_old, table_row_new)

with open('/Users/maikermota/DevLocal/abides_marl/blog/02_from_poc_to_modular_engine.md', 'w') as f:
    f.write(content)

print("Done")
