# DevOps Interview Q&A — Advanced & Scenario-Based

Senior DevOps / platform questions: CI/CD design, IaC, containers and
Kubernetes, observability, incident response, and cloud deployment patterns.
Concise talking points with snippets where they help.

---

## 60-second talking points

- **"Everything as code, everything reproducible."** Infra, pipelines, and config
  in version control so environments are rebuildable, not hand-crafted.
- **"Immutable deployments beat in-place mutation."** Build an artifact once,
  promote the same artifact through environments.
- **"Automate the path to prod, gate it with checks."** Fast feedback in CI,
  controlled promotion to prod with approvals and rollbacks.

---

## CI/CD

=== "Build once, promote the artifact"

    ```text
    build → test → package (immutable image, tagged by commit)
          → deploy dev → validate
          → promote same image → test → prod
    ```

=== "Pipeline stages"

    ```groovy
    stages { lint → unit tests → build image → push to registry
             → deploy dev → integration tests → manual approval → deploy prod }
    ```

??? question "Design a CI/CD pipeline for a containerized service."
    On PR: lint, unit tests, security scan, build. On merge to main: build an
    **immutable image tagged by commit SHA**, push to the registry, deploy to dev,
    run integration/smoke tests, then **promote the same image** to test and prod
    behind approvals. Prod deploy uses a safe strategy (blue/green or canary) with
    automated health checks and one-command rollback. Never rebuild per
    environment — promote the tested artifact.

??? question "How do you promote across environments without config drift?"
    Same artifact, **externalized config** per environment (env vars, parameter
    store, secrets manager) — never bake environment specifics into the image.
    Infra defined as code and applied per environment from the same templates.
    Branch/tag strategy controls what's eligible for each environment so promotion
    is deterministic.

??? question "A deploy broke prod. Walk me through response and prevention."
    Response: **roll back first** (redeploy last-good artifact / flip blue-green),
    confirm recovery via health checks and dashboards, then investigate. Prevention:
    smaller/more frequent deploys, canary with automated rollback on error-rate/
    latency thresholds, better pre-prod test coverage, feature flags to decouple
    deploy from release, and a blameless postmortem to fix the systemic gap.

---

## Infrastructure as Code

??? question "How do you keep IaC safe and reviewable?"
    **Plan before apply** (review the diff in PR), remote **state** with locking to
    prevent concurrent corruption, modularize for reuse, pin provider/module
    versions, and separate state per environment. Gate `apply` behind approval for
    prod. Detect **drift** on a schedule. Never edit cloud resources by hand outside
    IaC or you lose reproducibility.

??? question "Someone changed a resource in the console and now IaC wants to revert it. What happened?"
    **Drift**: the live state no longer matches the code, so the next plan proposes
    to reconcile (often destructively). Fix: import the manual change into code, or
    revert the console change, then re-plan. Prevent it by locking down console
    write access in prod and requiring all changes through IaC + PR.

??? question "Blue/green vs canary vs rolling — trade-offs?"
    **Rolling**: replace instances gradually; simple, but mixed versions during
    rollout and slower rollback. **Blue/green**: full standby environment, instant
    switch and rollback, but double the resources briefly. **Canary**: route a small
    % of traffic to the new version, watch metrics, ramp up or abort; safest for
    risk but needs good traffic routing + metrics. Choose by risk tolerance and
    infra cost.

---

## Containers & Kubernetes

=== "Right-size and self-heal"

    ```yaml
    resources:
      requests: {cpu: "250m", memory: "256Mi"}
      limits:   {cpu: "500m", memory: "512Mi"}
    livenessProbe:  {httpGet: {path: /healthz, port: 8080}}
    readinessProbe: {httpGet: {path: /ready,   port: 8080}}
    ```

??? question "A pod keeps restarting (CrashLoopBackOff). How do you debug?"
    `kubectl describe pod` (events: OOMKilled? failed probe? image pull?),
    `kubectl logs --previous` for the crashed container. Common causes: failing
    **liveness probe** (too aggressive timing), **OOMKilled** (memory limit too
    low), missing config/secret, or a real startup crash. Fix the root cause —
    adjust probe timing, raise limits, supply config — don't just bump restarts.

??? question "Requests vs limits — why do both matter?"
    **Requests** drive scheduling (guaranteed resources, bin-packing). **Limits**
    cap usage (CPU throttled, memory over-limit → OOMKilled). Set requests to
    typical usage and limits to a safe ceiling. No requests → poor scheduling; no
    limits → a noisy neighbor can starve the node. Watch for CPU throttling from
    limits that are too tight.

??? question "How do you manage secrets in Kubernetes properly?"
    Don't commit secrets or bake them into images. Use a secrets manager (cloud
    KMS-backed) with an operator/CSI driver to mount them, or sealed/encrypted
    secrets in Git. Enable encryption at rest for etcd, scope RBAC so pods only
    read what they need, and rotate regularly.

---

## Observability & reliability

??? question "What do you monitor, and how do you avoid alert fatigue?"
    The three pillars: **metrics** (rates, errors, latency, saturation — RED/USE),
    **logs** (structured, correlated), **traces** (request flow across services).
    Alert on **symptoms users feel** (SLO burn, error rate, latency) not every
    low-level metric. Page only on actionable, urgent conditions; everything else
    is a dashboard or ticket. Tie alerts to SLOs and error budgets.

??? question "Explain SLI/SLO/error budget and how it changes behavior."
    **SLI** = a measured indicator (e.g. % successful requests). **SLO** = the
    target (e.g. 99.9%). **Error budget** = allowed failure (0.1%). When the budget
    is healthy, ship fast; when it's burning, slow down and prioritize reliability.
    It turns "how much reliability" into a shared, data-driven decision instead of
    an argument.

---

## Rapid-fire

| Q | A |
|---|---|
| Immutable infra? | replace instances/images rather than mutating in place |
| Blue/green? | two envs, instant switch + rollback |
| Canary? | small % of traffic to new version, ramp on good metrics |
| IaC drift? | live state diverges from code |
| CrashLoopBackOff top causes? | failed probe, OOMKilled, bad config, startup crash |
| Requests vs limits? | scheduling vs capping (throttle/OOM) |
| RED metrics? | Rate, Errors, Duration |
| Error budget? | allowed unreliability = 1 − SLO |

---

## Pitfalls interviewers probe

- Rebuilding artifacts per environment instead of promoting one.
- Baking environment config/secrets into images.
- Editing prod resources in the console (drift).
- Liveness probes too aggressive → false restarts.
- Alerting on causes not symptoms → fatigue.
- No rollback plan; investigating before restoring service.
