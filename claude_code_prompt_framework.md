# **Enhanced Claude Code Sub-Agent Application Builder Framework**
## **One-Shot Prompt Template v2.0 - Enterprise Patterns Included**

```markdown
# Claude Code Sub-Agent Project Builder - Enterprise Edition

I need to build a [APPLICATION_TYPE] using the claude-code-sub-agents framework. Please analyze requirements, design architecture, and create a comprehensive task specification for optimal agent orchestration with enterprise-grade resilience.

## 📋 Project Requirements

### Core Application Details
**Application Type**: [API Gateway/Web App/CLI Tool/Service/etc.]
**Primary Purpose**: [One sentence description]
**Target Users**: [Who will use this application]
**Key Integrations**: [External APIs, services, frameworks needed]

### Technical Constraints
**Deployment Environment**: [Local/Cloud/Container/Hybrid]
**Technology Preferences**: [Python/Node/Go/etc., specific frameworks]
**Infrastructure Limits**: [Performance, scalability, resource constraints]
**Existing Dependencies**: [Legacy systems, current tools, configurations to preserve]

### Enterprise Requirements (NEW)
**Authentication Method**: [OAuth 2.0/JWT/API Keys/Custom - specify flow type]
**Rate Limiting Constraints**: [External API limits, org constraints, usage tiers]
**Environment Type**: [Production/Demo/Trial/Sandbox - affects rate limits and features]
**Resilience Requirements**: [Uptime expectations, failover needs, retry patterns]
**Monitoring Needs**: [Health checks, metrics, alerting requirements]

### External Service Integration (ENHANCED)
**API Rate Limits**: [Specific limits per service, shared vs per-user limits]
**Authentication Patterns**: [Token refresh, credential rotation, seamless re-auth]
**Error Handling**: [429 responses, auth failures, network issues]
**Service Dependencies**: [Critical vs optional integrations, fallback strategies]

### Functional Requirements
**Core Features**: [List 3-5 essential features]
**Secondary Features**: [Nice-to-have features for future iterations]
**Client Compatibility**: [Specific tools/platforms that must integrate]
**Seamless Operation**: [Zero-downtime requirements, background processes]

### Development Constraints
**Token Efficiency Priority**: [High/Medium/Low - affects complexity of solution]
**Timeline**: [Proof of concept/Production ready/Iterative development]
**Team Knowledge**: [Technologies team is familiar with]
**Maintenance Requirements**: [How simple does ongoing maintenance need to be]

## 🛡️ Enterprise Resilience Patterns (NEW SECTION)

### Authentication & Authorization
**Seamless Re-authentication**: [Requirements for zero-interruption credential refresh]
**Credential Management**: [Secure storage, rotation, environment variables]
**Multi-user Support**: [Shared credentials vs per-user, session management]

### Rate Limiting & Throttling
**Proactive Rate Management**: [Stay under limits vs reactive handling]
**Request Queuing**: [Queue requests during rate limit recovery]
**Backoff Strategies**: [Exponential backoff, jitter, circuit breakers]
**Usage Monitoring**: [Track utilization, predict limits, alert on thresholds]

### Error Recovery & Resilience
**Retry Patterns**: [Which errors to retry, max attempts, timeout strategies]
**Graceful Degradation**: [Fallback behaviors, partial functionality]
**Request Queuing**: [Handle requests during service recovery]
**Circuit Breaker**: [When to stop retrying, recovery detection]

### Monitoring & Observability
**Health Checks**: [Deep vs shallow health checks, dependency validation]
**Metrics Collection**: [Performance, errors, rate limits, authentication]
**Alerting**: [Critical failures, threshold warnings, trend monitoring]
**Debugging Support**: [Request tracing, error context, log correlation]

## 🤖 Agent Framework Analysis

Using the claude-code-sub-agents framework from https://github.com/lst97/claude-code-sub-agents

### Orchestration Requirements
**Primary Pattern Needed**: [Sequential/Parallel/Conditional routing]
**Quality Gates**: [Where validation/review steps are critical]
**Coordination Complexity**: [Simple handoffs vs complex multi-agent workflows]
**Enterprise Validation**: [Security review, performance validation, resilience testing]

### Specialized Expertise Needed
**Architecture**: [backend-architect, cloud-architect, etc.]
**Implementation**: [python-pro, golang-pro, frontend-developer, etc.]
**Quality Assurance**: [security-auditor, code-reviewer, test-automator]
**Operations**: [deployment-engineer, performance-engineer, etc.]
**Resilience**: [incident-responder, devops-incident-responder] (NEW)

## 📐 Architecture Decision Framework

Please analyze and provide:

### 1. Requirements Clarification
- Identify any ambiguous or missing requirements
- Propose optimal technical approaches considering enterprise constraints
- Flag potential architecture decisions that need validation
- **Rate limiting analysis**: Assess external service constraints and mitigation strategies
- **Authentication flow design**: Recommend optimal auth patterns for use case

### 2. Agent Orchestration Strategy
```
[Agent 1] → [Agent 2] → [Agent 3] → ...
     ↓           ↓           ↓
[Validator] [Reviewer] [Quality Gate]
                ↓
        [Resilience Review] (NEW)
```

**Sequential Tasks**: [Tasks that must be completed in order]
**Parallel Tasks**: [Tasks that can be done simultaneously]  
**Review Gates**: [Critical validation points]
**Resilience Gates**: [Rate limiting, auth, error handling validation] (NEW)
**Token Optimization**: [How to minimize back-and-forth]

### 3. Implementation Architecture
- **Core Components**: [Main application components needed]
- **Integration Points**: [External system interfaces]
- **Data Flow**: [How information moves through the system]
- **Error Handling**: [Critical failure modes to address]
- **Resilience Layers**: [Rate limiting, auth management, request queuing] (NEW)

## 📝 Enhanced Task Specification Generation

Create a comprehensive task specification following this structure:

### Task 1: Context & Architecture
**Agent**: context-manager → [primary architect agent]
**Objective**: [Establish context and design overall architecture with enterprise patterns]
**Deliverables**: [Architecture with resilience patterns, rate limiting strategy, auth flow design]
**Constraints**: [Technical, resource, and external service limitations]

### Task 2: Core Implementation
**Agent**: [primary implementation agent]
**Objective**: [Build core functionality with enterprise resilience]
**Deliverables**: [Core features + rate limiting + seamless auth + request queuing]
**Integration Requirements**: [APIs, tools, frameworks with error handling]

### Task 3: Resilience & Security (ENHANCED)
**Agent**: [security-auditor] → [performance-engineer]
**Objective**: [Implement enterprise-grade resilience and security]
**Deliverables**: [Security validation + rate limiting + retry logic + monitoring]
**Focus Areas**: [Auth security, rate limit compliance, error recovery, monitoring]

### Task 4: Testing & Validation (ENHANCED)
**Agent**: test-automator
**Objective**: [Verify functionality including resilience patterns]
**Deliverables**: [Core tests + rate limiting tests + auth resilience tests + error recovery tests]
**Test Categories**: [Functional, resilience, integration, load/stress]

### Task 5: Documentation & Review
**Agent**: api-documenter → code-reviewer
**Objective**: [Complete project with comprehensive documentation]
**Deliverables**: [Documentation + runbooks + monitoring guides + troubleshooting]

## 🎯 Enhanced Success Criteria

**Functional Requirements Met**: [How to verify core functionality works]
**Quality Standards**: [Code quality, security, performance benchmarks]
**Integration Validation**: [How to test external integrations]
**Deployment Readiness**: [What constitutes "ready to deploy"]
**Maintenance Considerations**: [Long-term viability factors]

**Enterprise Resilience Standards** (NEW):
**Rate Limiting Compliance**: [Stays under limits, handles 429s gracefully]
**Authentication Resilience**: [Zero-downtime credential refresh, auto-retry on auth failures]
**Error Recovery**: [Graceful handling of service failures, appropriate retry patterns]
**Monitoring Coverage**: [Health checks, metrics, alerting for all critical paths]
**Performance Under Stress**: [Maintains functionality during rate limits and auth refresh]

## ⚡ Token Efficiency Considerations

**Minimize Iterations**: [Design for single-pass success including enterprise patterns]
**Clear Specifications**: [Detailed enough to avoid clarification requests]
**Agent Expertise Alignment**: [Match tasks to agent capabilities]
**Context Preservation**: [How to maintain context across agent handoffs]
**Enterprise Pattern Reuse**: [Leverage common resilience patterns to reduce custom design]

## 🔧 Service-Specific Considerations (NEW SECTION)

If integrating with specific services, include:

**Salesforce Integration**:
- Rate limits: [Production: 500 RPM, Demo/Trial: 150 requests/hour]
- Auth: [OAuth 2.0 Username-Password flow recommended]
- Org type considerations: [Demo orgs have shared rate limits]

**OpenAI/Anthropic Integration**:
- Rate limits: [Tier-based, token-based billing]
- Auth: [API key rotation, usage monitoring]

**AWS/Cloud Services**:
- Rate limits: [Service-specific, region-based]
- Auth: [IAM roles, credential chains]

**Add relevant service patterns for your specific integrations**

---

## Output Format Requested

Please provide:

1. **Requirements Analysis**: Clarify ambiguous requirements and propose enterprise-grade solutions
2. **Architecture Recommendation**: Optimal technical approach with resilience patterns
3. **Agent Orchestration Plan**: Specific agent sequence with enterprise validation gates
4. **Detailed Task Specifications**: Ready-to-execute tasks including resilience requirements
5. **Success Validation Framework**: How to verify completion including enterprise standards
6. **Rate Limiting Strategy**: Specific approach for external service constraints
7. **Authentication Flow**: Seamless credential management approach
8. **Monitoring Plan**: Health checks, metrics, and alerting strategy

Focus on creating a token-efficient, single-execution plan that maximizes specialized expertise while including enterprise resilience patterns to minimize post-deployment issues.
```
