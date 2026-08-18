# VS Code plugin and customization discovery — investigation, 2026-08-18

Reverse-engineered from the shipped bundles of VS Code 1.133.0 at
`.../Microsoft VS Code/a5b5009513/resources/app/out/`. Nothing here came from documentation, and
nothing here was observed in a running editor. Minified identifiers are quoted as found so a future
session can re-locate them; they will be renamed by any rebuild.

Owner of the resulting decisions: `docs/superpowers/specs/2026-08-18-multi-host-plugin-architecture-design.md`.

## Why this was opened

A measured dual-load: with `cwd` set to the repository, Claude Code offered 22 agents for 11 roles.
The investigation widened when the same tracked staging directory turned out to be read by VS Code too.

## Where the code lives

Two bundles matter, and confusing them produced one wrong conclusion during this investigation:

- `vs/platform/agentHost/node/agentHostMain.js` — the **runtime loader**: format table, component path
  resolution, discovery constants.
- `vs/workbench/workbench.desktop.main.js` — the **install/UI layer**: marketplace probing, plugin
  directory detection, settings and policy.

Marketplace handling exists only in the second. A grep of the first for `marketplace.json` returns one
hit — the VS Code CDN extension marketplace — which reads as a clean negative and is not one.

## Discovery constants (no manifest required)

Skills:

```js
[{path:".agents/skills",    source:"agents-workspace", storage:"local"},
 {path:".github/skills",    source:"github-workspace", storage:"local"},
 {path:".claude/skills",    source:"claude-workspace", storage:"local"},
 {path:"~/.agents/skills",  source:"agents-personal",  storage:"user"},
 {path:"~/.copilot/skills", source:"copilot-personal", storage:"user"},
 {path:"~/.claude/skills",  ...}]
```

Agents: `.github/agents`, `.claude/agents`, `~/.copilot/agents`, plus `.github/chatmodes` and
`.claude/rules`. The language contribution registers **any** `.md` under those directories:

```js
{id:"chatagent", extensions:[".agent.md",".chatmode.md"],
 filenamePatterns:["**/.github/agents/*.md","**/.claude/agents/*.md"]}
```

Measured in this repository on 2026-08-18: `.github/agents` present (11), `.claude/agents` present (11),
`.agents/skills` / `.github/skills` / `.claude/skills` all absent.

## Plugin formats and detection

```js
wRn = {format:0, manifestPath:"plugin.json",                hookConfigPath:"hooks.json"}
CRn = {format:1, manifestPath:".claude-plugin/plugin.json", hookConfigPath:"hooks/hooks.json"}
kRn = {format:2, manifestPath:".plugin/plugin.json",        hookConfigPath:"hooks/hooks.json"}
xRn = {format:3, manifestPath:"plugin.json", requiresManifest:true,
       componentPaths:{commands:"com.github.copilot/commands", skills:"skills",
                       agents:"com.github.copilot/agents",     rules:"com.github.copilot/rules",
                       hooks:"com.github.copilot/hooks/hooks.json", mcpServers:"mcp.json"},
       manifestExtensionNamespace:"com.github.copilot"}

async function ONi(s,o){ return await tNe(s,o) ? xRn
  : await Lrt(Ve(s,".plugin","plugin.json"),o) ? kRn
  : s.path.split("/").includes(".claude") || await Lrt(Ve(s,".claude-plugin","plugin.json"),o) ? CRn
  : wRn }
```

Format 3 — the documented Agent Plugins 1.0 contract — is gated on a strict `$schema` value:

```js
function yRn(s){ return typeof s=="string"
  && s.startsWith("https://agent-plugins.org/schemas/") && s.endsWith("/plugin.schema.json") }
```

Two non-obvious consequences:

1. **Any plugin path containing a `.claude` segment is forced to format 1**, regardless of manifests.
2. **Format 0 is the fallback**, reached only when the three preceding checks fail. A directory holding a
   bare `plugin.json` with no `$schema` lands here.

## Component path resolution

```js
Zp(r,i,"hooks", i.hookConfigPath, ...)   Zp(r,i,"mcpServers",".mcp.json", ...)
Zp(r,i,"skills","skills", ...)           Zp(r,i,"agents","agents", ...)
Zp(r,i,"rules","rules", ...)

function Zp(r,n,e,t,o,i){ let s=n.componentPaths?.[e];
  if (n.componentPaths && Object.hasOwn(n.componentPaths,e)) {          // format 3 only
    if (typeof s!="string") return [];
    if (!n.manifestExtensionNamespace) return Xy(r,s,ef,i);
    let a=fM(o), l=a.exclusive?[]:Xy(r,s,ef,i),
        d=ne(r,n.manifestExtensionNamespace),                           // root/com.github.copilot
        c=Xy(d,"",{paths:a.paths,exclusive:!0},d);                      // overrides forced under it
    return [...l,...c] }
  return Xy(r,t,fM(o),i) }                                              // formats 0/1/2

function Xy(r,n,e,t){ let o=t&&mo(r,t)?t:r, i=[];
  e.exclusive||i.push(ne(r,n));                                         // default = root/<default>
  for (let s of e.paths){ let a=hn(ne(r,s)); mo(a,o)&&i.push(a) }       // contained; ../ rejected
  return i }

function fM(r){ if(r==null)return ef;
  if(typeof r=="string"){ let n=r.trim(); return n?{paths:[n],exclusive:!1}:ef } ... }
```

- Formats 0/1/2 honour a **top-level** `agents`/`skills`/`hooks` field; format 3 requires them under
  `extensions["com.github.copilot"]`.
- **Format-3 overrides are re-based under `com.github.copilot/`** and containment-checked, so a format-3
  plugin cannot serve agents from `.github/agents`. This is why the "one directory, both routes" idea
  only worked on the format-0 fallback, and why it was rejected as a design.
- **A string override is additive, not replacing** (`exclusive:false`) — the default directory is still
  scanned. Only `{"paths":[...],"exclusive":true}` replaces it.

## Which manifest supplies overrides

```js
async function FNi(s,o,e){ if(o.format===3){ let i=await tNe(s,e); return i?{...i}:void 0 }
  let t=await nLo(Ve(s,o.manifestPath),e);          // format 1 -> .claude-plugin/plugin.json
  return t&&typeof t=="object"&&!Array.isArray(t)?t:void 0 }
```

For a non-format-3 plugin, overrides come from **that format's own manifest**, not from any other
`plugin.json` present in the tree. This is the mechanism behind the `copilot-hooks.json` finding below.

## Marketplace and plugin-directory probing (install layer)

```js
hLn = [{type:"openPlugin",path:"marketplace.json"},
       {type:"openPlugin",path:".plugin/marketplace.json"},
       {type:"copilot",   path:".github/plugin/marketplace.json"},
       {type:"claude",    path:".claude-plugin/marketplace.json"}]

ALo = [{type:"openPlugin",path:".plugin/plugin.json"},
       {type:"claude",    path:".claude-plugin/plugin.json"},
       {type:"copilot",   path:"plugin.json"}]

async _readPluginsFromDefinitions(e,t,i){
  for (let n of hLn) { let r = await t(n.path);
    if (!(!r?.plugins || !Array.isArray(r.plugins)))
      return this._parseMarketplacePlugins(r,e,n.type,i) }   // first match wins
  return [] }

async isPluginDirectory(e){ if(await tNe(e,this._fileService))return!0;
  for(let t of ALo) if(await this._fileService.exists(Ve(e,t.path))) return!0; return!1 }
```

Both lists are **first-match-wins**. VS Code therefore reads Claude marketplaces, and any directory
holding `.claude-plugin/plugin.json` presents to VS Code as an installable plugin directory. Since Claude
Code requires that file at the repository root, **the repository root will always look like a VS Code
plugin**, and `ONi` will always classify it as format 1. That cannot be closed from inside the repo.

Relevant settings: `chat.pluginLocations`, `chat.plugins.paths`, `chat.plugins.marketplaces`,
`chat.plugins.extraMarketplaces`, `chat.plugins.strictMarketplaces`, `chat.plugins.enabledPlugins`.

## `hooks/copilot-hooks.json` does not protect VS Code

`AGENTS.md` stated that this deliberately empty file "keeps Copilot and VS Code from loading the Claude
guard." The VS Code half is false. Its only reference is the `"hooks"` field of the **root**
`plugin.json`, which VS Code never reads: for format 1, `FNi` reads `.claude-plugin/plugin.json`, which
has no `hooks` field, so `Xp` returns `undefined` and `Zp` falls back to format 1's `hookConfigPath` —
`hooks/hooks.json`, the Claude read-only guard.

The empty override is read only by Copilot CLI. Verified 2026-08-18:
`.claude-plugin/plugin.json` `hooks` field is `None`; `hooks/hooks.json` exists; root `plugin.json`
`hooks` field is `'./hooks/copilot-hooks.json'`.

## The global suppression setting

```js
async getResolvedSourceFolders(e){
  return this.areStandalonePromptFilesBlocked(e) ? [] : this.fileLocator.getResolvedSourceFolders(e) }
areStandalonePromptFilesBlocked(e){ let t=this.configurationService.getValue(Uie);
  return eOi(t,e) || (e==="hook" && this.configurationService.getValue(zie)===!0) }
function eOi(s,o){ switch(o){ case"skill":case"agent":case"hook":case"instructions":
  return ZNi(s); default:return!1 } }
```

`chat.customizations.strictPluginOnlyCustomization` suppresses **all** workspace and user discovery
across agents, skills, hooks and instructions. It is all-or-nothing, hidden from the settings UI
(`included:!1`), and policy-driven. Recorded as a fact; no fleet design should depend on it.

## Detector failures made during this investigation

Both are recorded because the failure mode is the point, not the incident.

1. A grep of `resources/app/out` returned zero hits for every probe term. The path did not exist —
   the real tree is under a commit-hash directory (`a5b5009513/`). Caught by running a control term
   that had to be present.
2. A negative about Claude marketplace support was stated after grepping only `agentHostMain.js`.
   Marketplace code lives in `workbench.desktop.main.js`, so that grep could not have found it. The
   claim was published before the control was run.

The rule both cases support: a negative result is a claim about the instrument until the instrument is
shown to fire.

## Re-verification trigger

Every constant above is a shipped-binary fact for VS Code 1.133.0. Re-read this file's greps after any
VS Code upgrade before relying on a path, format, or precedence claim.
