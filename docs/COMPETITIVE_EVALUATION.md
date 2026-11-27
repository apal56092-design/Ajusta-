# AJUSTA Capability & Evaluation Strategy

## Goal
Build a high-quality, trustworthy AI platform that can compete with leading applications in selected workflows. A claim such as "beats 95% of all applications" is not measurable until the comparison set, tasks, scoring method and test conditions are defined. AJUSTA will make evidence-based comparisons rather than promise a universal ranking.

## Learn from the ecosystem—responsibly
AJUSTA may study public product documentation, public APIs, published research, open-source projects and user-authorized feedback. It must respect licenses, terms of service, privacy, copyright and access controls.

It must not:
- Copy proprietary source code or protected product content without permission.
- Bypass access controls, paywalls or rate limits.
- Scrape private accounts or collect personal data without a lawful basis and appropriate consent.
- Present another product's work as AJUSTA's original work.

The objective is to learn general design patterns, identify unmet needs and build original, tested implementations.

## Benchmark framework
For each target workflow:
1. Define representative tasks and expected outcomes.
2. Select comparable products and versions.
3. Use the same prompts, inputs, tools and time limits where practical.
4. Score correctness, completeness, reliability, latency, usability, accessibility, privacy and cost.
5. Include human review for subjective quality.
6. Publish methodology, sample size, date and limitations.
7. Repeat after meaningful releases and track regressions.

## Quality dimensions
- Task success rate
- Factual accuracy and evidence quality
- Code correctness and test pass rate
- Robustness to ambiguous or malformed input
- Failure recovery
- Response latency
- Cost per successful task
- Accessibility and ease of use
- Privacy and security posture

## Improvement loop
Observe authorized feedback and benchmark failures → classify the gap → research permitted public evidence → propose an original improvement → write tests → implement → evaluate against baseline → document results → release only when quality gates pass.

## Competitive focus
Do not attempt to build every feature at once. Start with a narrow set of workflows where AJUSTA can be measurably excellent, then expand based on evidence, user value, maintainability and available resources.

## Public claims
Only publish numerical superiority claims when supported by reproducible benchmark results and a clearly stated comparison scope. Never imply that all competing apps have been tested when they have not.
