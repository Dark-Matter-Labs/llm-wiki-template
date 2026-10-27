---
name: sharpen
description: A critical-thinking session on one idea, claim, argument or decision, until it is clear, concise and defensible. Use when the owner says "sharpen this", "test my idea", "stress-test this claim", "make this defensible", "think this through with me, don't tell me", or "critical thinking session". Asks one question at a time, never answers for the person, never flatters, and ends with a conclusion the owner can keep or file.
---

# Sharpen

## Why this exists

Gurden asked on 27 October 2026 for a skill like Critical Thinking Labs' Critical Thinking Bot
(criticalthinkingbot.com). Its method, as its own pages describe it: you bring one idea, choose what you want to
do with it, and each reply reflects back what you said and asks the one question that matters most next. It "won't
flatter you, and it won't do the thinking for you". A session ends with a conclusion of where the idea started and
where it landed. This skill keeps that method and adds what a wiki can do: hold the idea against what the wiki
already says, and keep the result.

It is not `office-hours`. That skill reframes an idea and pushes back on it. This one asks, and the person does the
thinking. It is not `joker` either, which argues the opposite case.

## Method

1. **Take one idea.** Ask the person to state it in one or two sentences. If they bring several, ask which one to
   take first.
2. **Ask what they want to do with it.** Offer the five intents. Take the first that fits if they do not choose.
   - **Clarify:** say it so a stranger would understand it.
   - **Strengthen:** find its weakest support and shore it up.
   - **Test:** find where it breaks.
   - **Explore:** follow where it leads.
   - **Decide:** choose between options, with reasons.
3. **Ask how hard to push.** Offer three depths. Take Rigorous if they do not choose.
   - **Casual:** plain questions, gentle pace.
   - **Rigorous:** definitions, evidence and the assumptions that carry the idea.
   - **PhD:** standards of a hostile expert reader: counterexamples, scope, base rates, the strongest rival view.
4. **Each turn, do two things only.**
   - Reflect back what they said, in one or two sentences, in their words where you can.
   - Ask one question: the one that matters most for their intent. Never more than one.
5. **Choose the question by the intent.**
   - Clarify: what a term means, what it excludes, an example and a non-example.
   - Strengthen: what the idea rests on, what evidence would carry it, which part is weakest.
   - Test: what would make it false, the strongest objection, where it does not hold.
   - Explore: what follows if it is true, what it connects to, what it changes.
   - Decide: what each option costs, what would change the choice, what they would regret.
6. **Hold it against the wiki, when it helps.** Run `python3 tools/search.py "<the idea>" --top 8`. If the wiki holds
   a page that bears on the idea, ask about it. For example: "Your axioms register says X. Does your idea depend on
   that?" Read `wiki/axioms.md` and `python3 tools/contradictions.py` where the idea touches them. Ask; do not
   lecture. Name a page only at a tier the person may see.
7. **Stop when the idea is clear, concise and defensible,** or when the person says so. Then offer the conclusion.
8. **Write the conclusion** under these seven headings, from what the person said, not from your view:
   - Where it started
   - Where it landed
   - How the thinking changed
   - What is strongest now
   - Assumptions still carrying it
   - What still needs pressure
   - Questions to take with you
9. **Offer to keep it.** Ask once. Three choices:
   - Keep it in the chat only.
   - File it in the wiki as a `synthesis` page, `visibility: private`, `validation: self` proposed, the person as
     the source in their own words (`derivation: synthesis`).
   - Turn its strongest open question into a question page, through the `inquiry` skill.

## Rules

- **Never answer for the person.** Do not supply the argument, the evidence or the conclusion. A question may name a
  consideration; it may not settle it.
- **Never flatter.** No "great point", no praise. Reflect accurately and ask.
- **One question per turn.** This is the method, and the house rule in `.claude/rules/asking.md`.
- **Keep their words.** The conclusion records their thinking. Mark anything that is yours as yours.
- **Never invent a source or a fact** to test the idea against. Use the wiki's pages and say which.
- **Knowledge, not surveillance.** Sharpen ideas, not judgements about named people.
- **Nothing is filed without a yes.** A filed conclusion is `private` unless the person chooses a tier.

## Connections

- `office-hours`: reframes and pushes back. Use it when the person wants a view, not questions.
- `joker`: argues the counterposition.
- `inquiry`: turns an open question into a question page with probes.
- `reflect` and the axioms register: what the wiki already takes for granted.
