# Cloud Concept Inventory — misconception codebook v1 (a priori)

Unit of analysis: one public Q&A thread = question + accepted answer.
A thread is CONCEPTUAL (conceptual = yes) when the accepted answer resolves the asker's problem by correcting or completing the asker's *model of how a cloud concept works* (e.g. how access decisions are made, how packets are routed, what a cache does), rather than by supplying syntax, a version/bug workaround, a console location, a quota increase, or product-specific trivia. If the asker's expectation was wrong in a way that a vendor-neutral principle explains, it is conceptual. Pure "how do I do X" requests with no wrong expectation are NOT conceptual (conceptual = no, code = NONE).

Domains (choose the ONE most central):
- SHR  Shared responsibility & service models: who (provider vs customer) secures/operates what under IaaS/PaaS/FaaS/SaaS.
- IAM  Identity & access: how authorisation decisions are computed from policies, principals, roles and credentials.
- NET  Network reachability: subnets, routing, gateways/NAT, stateful vs stateless filters, protocols/ports, DNS/endpoints, peering.
- LB   Load balancing & health checking: listener/target semantics, L4 vs L7, health checks, internet-facing vs internal.
- ELA  Elasticity, statelessness & fault domains: horizontal scaling, state externalisation, scaling signals, replacement, zones/redundancy.
- CAC  Caching & consistency: CDN/edge caching, TTL/expiry, invalidation, cache keys, replication/eventual consistency.
- CST  Cost: what is metered, cost drivers, idle/stopped resources, data transfer, pricing models.
- NONE not about these domains (or not conceptual).

Misconception codes (assign the single best code when conceptual = yes; use NEW with a short label if none fits):
SHR-1 Provider-secures-all: believes the provider is responsible for customer-side configuration, OS patching on IaaS, data classification or access control.
SHR-2 Misplaced customer burden: believes the customer must manage layers that the provider manages for that service model (hardware, hypervisor, managed runtime).
IAM-1 Allow-beats-deny: believes an Allow (or adding more Allow) can override an explicit Deny.
IAM-2 Default-allow: believes access is granted unless denied, or that being authenticated/being in the account/being an admin elsewhere implies access.
IAM-3 One-side-suffices: believes an identity-side grant alone is enough where a resource-side grant (resource/bucket/key policy, cross-account trust) is also needed, or vice versa.
IAM-4 Credential locus: confuses users, roles and temporary credentials; embeds long-lived keys where a role/managed identity is expected; misunderstands role assumption/trust.
IAM-5 Scope mismatch: action or resource scope wrong (container vs object resource, wrong resource identifier, wildcard semantics, condition semantics).
IAM-6 Guardrail-grants: believes a guardrail layer (permission boundary, organisation policy, deny-only control) grants permissions.
IAM-7 Instant-effect: expects policy/role changes or caches to take effect instantly everywhere, or misreads evaluation order/precedence beyond deny.
NET-1 Public-is-an-instance-property: believes 'public' means having a public IP or a flag, rather than a route to an internet gateway (or vice versa).
NET-2 NAT-is-bidirectional: believes NAT/egress gateways permit unsolicited inbound connections to private hosts.
NET-3 Statefulness confusion: treats stateful filters (security groups/NSGs) as stateless (adds rules for return traffic) or stateless ACLs as stateful (forgets ephemeral return ports).
NET-4 Layer/protocol confusion: tests TCP/HTTP reachability with ICMP ping, or equates an open port with a running/listening service, or confuses protocol layers.
NET-5 Filter semantics: believes allow-only filters can deny, rule order matters where it does not (or not where it does), or source/destination referencing is misread.
NET-6 Address-scope/transitivity: expects private addresses to be reachable across networks or the internet without peering/VPN/endpoints, or expects peering to be transitive or overlapping CIDRs to work.
NET-7 Name-resolution/endpoint: misunderstands private vs public DNS names, private endpoints, or which address a name resolves to from where.
LB-1 Health-check semantics: misunderstands what makes a target healthy (path/port/protocol/status codes, filter blocking the checker, grace periods).
LB-2 Exposure/placement: confuses internet-facing vs internal balancers or which subnets/addresses a balancer and its targets need.
LB-3 Layer features: expects L7 features (path/host routing, header rewrite, cookies) from an L4 balancer or vice versa; misunderstands TLS termination or client-IP preservation.
LB-4 Stickiness-as-state-fix: relies on sticky sessions to solve state/scaling problems, or misunderstands session affinity.
ELA-1 Local-state: keeps sessions, uploads or other state on individual instances that may be added/removed/replaced.
ELA-2 Scaling expectations: expects instantaneous or vertical scaling from horizontal policies; misunderstands min/desired/max, warm-up or cooldown.
ELA-3 Wrong signal: scales on a metric that does not reflect load, or misunderstands how the metric is aggregated/evaluated.
ELA-4 Replacement/health: misunderstands when and why scaling groups terminate/replace instances (health-check type, lifecycle, scale-in selection).
ELA-5 Redundancy/fault domain: believes multiple instances in one zone/host give high availability, or misunderstands zone/region failure scope.
CAC-1 Origin-change-visible: expects changes at the origin to be visible immediately through a cache despite TTL; misunderstands invalidation/versioning.
CAC-2 Cache-key: misunderstands what is part of the cache key (query strings, headers, cookies), leading to wrong or uncacheable content.
CAC-3 Consistency: assumes strong/read-after-write consistency on replicated or eventually consistent stores or across replicas/regions.
CAC-4 Cacheability/headers: misunderstands which responses are cached (Cache-Control precedence, errors, methods, private content).
CST-1 Idle-is-free: believes stopped/idle/unused resources (volumes, addresses, gateways, snapshots, reserved capacity) cost nothing.
CST-2 Transfer-cost: misunderstands data-transfer charges (egress vs ingress, inter-zone/region, NAT processing, CDN).
CST-3 Pricing-model: misunderstands per-request/per-second/reserved/spot/free-tier pricing or what triggers a charge.
NEW  Conceptual misconception not covered above (give a <=8-word label).
NONE Not conceptual / not in scope.

Decision rules:
R1 Code the misconception that the ACCEPTED ANSWER corrects, not every confusion in the question.
R2 If the asker is merely unaware of a product feature but holds no wrong expectation, conceptual = no.
R3 Bugs, outages, quota limits, console/SDK syntax, versions and deprecated APIs: conceptual = no, unless the answer explains that the asker's expectation was wrong in principle.
R4 Provider-specific terms map to the vendor-neutral code (security group/NSG/firewall rule -> NET filters; bucket policy/key policy -> resource-side policy; managed identity/service account -> role/credential locus).
R5 When two codes fit, prefer the more specific one in the domain of the answer's main correction.
