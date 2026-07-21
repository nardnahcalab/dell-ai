---
name: dell-ai
description: Skill for interacting with Dell Enterprise Hub (DEH) - discovering models, exploring hardware platforms, generating deployment snippets, etc.
---

# Dell AI

dell-ai interacts with the Dell Enterprise Hub (DEH) — discovering models, exploring hardware platforms, generating deployment snippets, managing app catalog entries, checking system compatibility, etc.

## When to use

- User wants to find AI models available on Dell Enterprise Hub
- User wants to find AI models available on DEH for their hardware platform
- User needs to check which Dell hardware platforms support a given model
- User wants to generate Docker or Kubernetes deployment commands for a model and then run it.
- User wants a goodput-optimized deployment snippet (balanced, long-context, high-concurrency, performance).
- User wants to **deploy** a model or app directly onto the local node (not just generate a snippet)
- User wants to **tear down** / undeploy a running deployment
- User wants to **check the status** of deployed endpoints, checkpoints, and running containers/deployments
- User wants to explore or deploy applications from the Dell app catalog
- User needs to check system compatibility with Dell AI platforms
- User asks about Dell AI, Dell Enterprise Hub, or DEH
- User wants to authenticate with Dell AI using a Hugging Face token
- User wants to manage local/global **environment variables** for dell-ai
- User wants to check their system info or check system compatibility against Dell AI validated configs

## Installation

```bash
uv pip install dell-ai
```

## Authentication

Uses a Hugging Face token. Auto-loads from HF token cache, or accepts one directly.

```python
from dell_ai import DellAIClient

client = DellAIClient()                        # Uses cached HF token
client = DellAIClient(token="your_hf_token")   # Or explicit token

client.is_authenticated()  # Returns bool
client.get_user_info()     # Returns dict with name, email, orgs, etc.
```

## Models

### Search and list models

`list_models` returns `List[str]` of IDs. `search_models` accepts the same filters but returns full `Model` objects.

```python
# List model IDs (all filters are optional and combinable)
models = client.list_models(
    query="llama",                    # Search name/description
    multimodal=True,                  # True for multimodal, False for text-only
    min_size=7000,                    # Min params in millions
    max_size=70000,                   # Max params in millions
    license_filter="apache",          # License substring match
    platform_id="xe9680-nvidia-h200", # Only models compatible with this platform
)

# Full Model objects with same filters
results = client.search_models(query="llama", multimodal=True)
# Model fields: repo_name, description, license, size, is_multimodal,
#               has_system_prompt, creator_type, status, configs_deploy
```

### Get model details and compatible platforms

```python
# Returns Model object
model = client.get_model("meta-llama/Llama-4-Maverick-17B-128E-Instruct")

platforms = client.get_compatible_platforms("google/gemma-3-27b-it")
# Returns List[PlatformCompatibility] with platform_id and configs (List[ModelConfig])
for p in platforms:
    print(p.platform_id, [c.model_dump() for c in p.configs])
```

### Check model access (gated repos)

```python
# Returns True, or raises GatedRepoAccessError / AuthenticationError
client.check_model_access("meta-llama/Llama-4-Maverick-17B-128E-Instruct")
```

### Get model Deployment Snippets

Automatically validates model access and model-platform compatibility.

Provide **either** `num_gpus` (manual sizing) **or** `goodput` (server-optimized) —
the two are mutually exclusive, and exactly one is required.

```python
# Basic deployment snippet with manual GPU sizing
snippet = client.get_deployment_snippet(
    model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    platform_id="xe9680-nvidia-h200",
    engine="docker",       # "docker" or "kubernetes"
    num_gpus=8,
    num_replicas=1,
)
print(snippet)  # Ready-to-use docker command or k8s manifest

# Goodput-optimized: DEH returns the GPU count and optimized params for the
# scenario. Omit num_gpus when using goodput.
snippet = client.get_deployment_snippet(
    model_id="nvidia/MiniMax-M2.7-NVFP4",
    platform_id="xe9680-nvidia-h200",
    engine="docker",
    goodput="balanced",    # balanced | long-context | high-concurrency | performance
)
```

Not every (model, platform, scenario) combination has an optimized config; the
API is the source of truth and raises `ResourceNotFoundError` with a message
like `No optimized config for "balanced" scenario on this SKU.` when it doesn't.

### Goodput scenarios reference data

Global, static reference data: scenario definitions, SLO field docs, and SLO
targets per SKU. Cached on disk after the first call.

```python
ref = client.get_goodput_scenarios()
# GoodputReference fields:
#   scenarios            -> List[Scenario] (id, label, description)
#   slo_field_descriptions -> Dict[str, str]
#   slos_by_sku          -> Dict[SkuId, Dict[scenario, Slo]] (sparse)
# Slo fields: max_model_context, virtual_users, input_tokens [min,max], output_tokens [min,max]

slo = ref.slos_by_sku.get("xe9680-nvidia-h100", {}).get("balanced")
```

## Platforms

```python
platforms = client.list_platforms()  # Returns List[str] of SKU IDs

platform = client.get_platform("xe9680-nvidia-h200")
# Fields: id, name, platform_type, vendor, accelerator_type, accelerator,
#   gpuram, gpuinterconnect, totalgpucount, product_name

sys_infos = client.get_platform_system_info("xe9680-nvidia-h200")  # List[SystemInfo]
```

## Applications

### List and inspect apps

```python
apps = client.list_apps()  # Returns List[str] of app names

app = client.get_app("openwebui")
# App fields: id, name, license, description, features, instructions,
#   tags, recommendedModels, components
```

### Explore configurable parameters

```python
for component in app.components:
    for param in component.config:
        print(f"  {param.name}: {param.helmPath} ({param.type}), default={param.default}")
    for secret in component.secrets:
        print(f"  [secret] {secret.name}: {secret.helmPath}")
```

### Generate app deployment snippet

Each config item requires: `helmPath`, `type` (`"string"`, `"boolean"`, `"number"`, or `"json"`), and `value`.

```python
config = [
    {"helmPath": "main.config.storageClassName", "type": "string", "value": "gp2"},
    {"helmPath": "main.config.enableOpenAI", "type": "boolean", "value": True},
]
snippet = client.get_app_snippet("openwebui", config)
print(snippet)  # Helm install command
```

## Deploying models and applications (local execution)

Beyond generating snippets, dell-ai can **execute** them on the local node using
the locally available engine: `docker` (Docker CLI), `kubernetes` (`kubectl
apply`), or Helm (apps). The relevant tool must be installed and configured.

Deployments run **detached (background) by default**. For Docker, dell-ai
automatically:
- converts interactive flags (`-it`) to detached (`-d`) and captures the
  container ID and inferred endpoint URL,
- remaps the host port to a free one if the snippet's port is already in use,
- allocates and pins free GPU indices.

On success, metadata (endpoint, engine, container/deployment ID, assigned GPUs)
is written to the **deployment registry** (see below).

Provide **either** `num_gpus` **or** `goodput` — mutually exclusive, exactly one
required (same rule as snippet generation).

```python
# Deploy a model on the local node
result = client.deploy_model(
    model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    platform_id="xe9680-nvidia-h200",
    engine="docker",              # "docker" or "kubernetes"
    num_gpus=8,                   # or goodput="balanced" (omit num_gpus)
    num_replicas=1,
    detach=True,                  # False = run in foreground
    # local_dir="/data/weights",           # mount local weights (Docker only)
    # hf_cache_dir="~/.cache/huggingface",  # or reuse an HF cache (mutually exclusive)
)
# result dict: success(bool), engine, endpoint, container_id | k8s_deployment, error?

# Deploy an app (Helm)
result = client.deploy_app(app_id="openwebui", config=[...], detach=True)
```

`deploy_model` / `deploy_app` **do not raise on runtime failure** — they return
`{"success": False, "error": ...}`. They still raise `ValidationError`,
`ResourceNotFoundError`, or `GatedRepoAccessError` for bad parameters or access.

CLI equivalents:

```bash
# Manual GPU sizing / goodput
dell-ai models deploy -m <model_id> -p <platform_id> -e docker --gpus 8
dell-ai models deploy -m <model_id> -p <platform_id> -e docker --goodput balanced

# Kubernetes / foreground
dell-ai models deploy -m <model_id> -p <platform_id> -e kubernetes --gpus 8
dell-ai models deploy -m <model_id> -p <platform_id> -e docker --no-detach

# Serve local weights instead of downloading (Docker only; path must exist; mutually exclusive)
dell-ai models deploy -m <model_id> -p <platform_id> -e docker --gpus 8 --local-dir /data/weights
dell-ai models deploy -m <model_id> -p <platform_id> -e docker --gpus 8 --hf-cache-dir ~/.cache/huggingface

# App (Helm)
dell-ai apps deploy openwebui --config '{"config":[{"helmPath":"main.config.storageClassName","type":"string","value":"gp2"}]}'
```

## Deployment registry and teardown

Successful deployments are tracked in a registry so they can be listed,
inspected, and torn down. Two scopes:
- **Local** — `.dell-ai-deployments.json` (current working directory)
- **Global** — `~/.config/dell-ai/deployments.json`

Each entry is keyed by a **deployment ID** (defaults to the model ID; additional
instances of the same model are suffixed, e.g. `org/model_1`, each with its own
host port and GPU indices). Running DEH Docker containers are auto-discovered and
added; entries whose containers are gone are pruned automatically.

```python
from dell_ai import deployments

deployments.list_deployments()             # dict keyed by deployment ID
deployments.get_deployment("org/model_1")    # single entry or None
deployments.delete_deployment("org/model_1") # remove registry entry (no container stop)
```

Tear down a deployment — stops the Docker container / Kubernetes deployment **and**
removes its registry entry:

```bash
dell-ai models undeploy -d <deployment_id>
```

`undeploy` acts on **one deployment at a time**. Always run
`dell-ai status` first to see if the target deployment ID exists.

## Environment variables

dell-ai persists configuration as environment variables in two scopes,
auto-loaded into `os.environ` on CLI startup and `DellAIClient` init. Resolution
precedence: **shell env → local → global**.
- **Local** — `.dell-ai-env.json` (current working directory)
- **Global** — `~/.config/dell-ai/env.json`

```python
from dell_ai import env

env.set_env_var("DELL_AI_CHECKPOINT", "/data/ckpt", is_global=False)
env.get_env_var("DELL_AI_CHECKPOINT")
env.list_env_vars()   # is_global: None=combined, True=global only, False=local only
env.delete_env_var("DELL_AI_CHECKPOINT", is_global=False)
```

```bash
dell-ai env set DELL_AI_CHECKPOINT /data/ckpt   # add --global for the global scope
dell-ai env get DELL_AI_CHECKPOINT
dell-ai env list                                # --local / --global to scope
dell-ai env delete DELL_AI_CHECKPOINT           # --global to delete from global
```

## Checking deployment status

```bash
dell-ai status          # active deployments, checkpoints, running Docker/K8s
dell-ai status --clean  # also remove exited containers and stopped K8s deployments
```

Reports:
- **Active deployments** — reads the deployment registry, probes each endpoint
  (online + response time); auto-discovers running DEH containers.
- **Checkpoints** — existence, type, and size of paths in `DELL_AI_*_CHECKPOINT`
  environment variables.
- **Active Docker/K8s** — running DEH containers and Kubernetes deployments.

Docker/Kubernetes scanning is skipped gracefully when `docker` / `kubectl` are
not available on the node.

## System Utilities (CLI only, Linux)

```bash
dell-ai utils describe-system              # Get system info as JSON
dell-ai utils describe-system -o out.json  # Save to file
dell-ai utils describe-system | jq         # Pretty-print
dell-ai utils check-system                 # Check compatibility against Dell AI validated configs
```

Requires: `lscpu`, `lspci`, `lsblk`, `dmidecode`. For GPUs: `nvidia-smi`, `nvidia-ctk`. For K8s: `kubectl`.

## Exceptions

All in `dell_ai.exceptions`:
- `AuthenticationError` — Invalid or missing token
- `GatedRepoAccessError` — No access to a gated model repository
- `ResourceNotFoundError` — Model, platform, or app not found
- `ValidationError` — Invalid parameters (may include `valid_values`)
- `APIError` — General API errors
