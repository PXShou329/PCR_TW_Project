import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const clientPath = join(root, "packages", "api-client", "src", "types.ts");

const pythonCandidates = [
  process.env.PCR_OPENAPI_PYTHON,
  join(root, ".venv", "Scripts", "python.exe"),
  join(root, ".venv", "bin", "python"),
  "python",
  "python3",
].filter(Boolean);

const openApiCommand = [
  "import json,os,sys",
  "os.environ.setdefault('PCR_DATABASE_URL','sqlite://')",
  "sys.path[:0]=['apps/api','database']",
  "from pcr_api.main import app",
  "print(json.dumps(app.openapi(), separators=(',',':')))"
].join(";");

let openApiResult;
let pythonExecutable;
for (const candidate of pythonCandidates) {
  if (candidate.includes(root) && !existsSync(candidate)) continue;
  const result = spawnSync(candidate, ["-c", openApiCommand], {
    cwd: root,
    encoding: "utf8",
    windowsHide: true,
  });
  if (!result.error && result.status === 0) {
    openApiResult = result;
    pythonExecutable = candidate;
    break;
  }
}

if (!openApiResult) {
  throw new Error(
    "Unable to generate FastAPI OpenAPI. Install Python dependencies or set PCR_OPENAPI_PYTHON."
  );
}

const openapi = JSON.parse(openApiResult.stdout);
const sourceText = readFileSync(clientPath, "utf8");
const sourceFile = ts.createSourceFile(clientPath, sourceText, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);

const interfaceNodes = new Map();
for (const statement of sourceFile.statements) {
  if (ts.isInterfaceDeclaration(statement)) interfaceNodes.set(statement.name.text, statement);
}

const schemaToInterface = {
  BaselineCounts: "BaselineCounts",
  BaselineData: "Baseline",
  ClaimData: "Claim",
  EvidenceData: "Evidence",
  SourceMeta: "SourceMetadata",
  StageCoverage: "Coverage",
  StageDetail: "StageDetail",
  StageSummary: "StageSummary",
  TeamDetail: "TeamDetail",
  TeamMemberData: "TeamMember",
  TeamSummary: "TeamSummary",
};

function collectInterfaceProperties(interfaceName, seen = new Set()) {
  if (seen.has(interfaceName)) return new Map();
  seen.add(interfaceName);
  const node = interfaceNodes.get(interfaceName);
  if (!node) throw new Error(`Missing TypeScript interface: ${interfaceName}`);

  const properties = new Map();
  for (const clause of node.heritageClauses ?? []) {
    for (const inherited of clause.types) {
      for (const [name, property] of collectInterfaceProperties(inherited.expression.getText(sourceFile), seen)) {
        properties.set(name, property);
      }
    }
  }
  for (const member of node.members) {
    if (ts.isPropertySignature(member) && member.name && member.type) {
      properties.set(member.name.getText(sourceFile).replaceAll(/^["']|["']$/g, ""), member);
    }
  }
  return properties;
}

function openApiNullable(property) {
  if (property.type === "null") return true;
  if (Array.isArray(property.type) && property.type.includes("null")) return true;
  return [...(property.anyOf ?? []), ...(property.oneOf ?? [])].some(openApiNullable);
}

function typeScriptNullable(typeNode) {
  return typeNode.kind === ts.SyntaxKind.NullKeyword
    || (ts.isLiteralTypeNode(typeNode) && typeNode.literal.kind === ts.SyntaxKind.NullKeyword)
    || (ts.isUnionTypeNode(typeNode) && typeNode.types.some(typeScriptNullable));
}

const failures = [];
const schemas = openapi.components?.schemas ?? {};

for (const [schemaName, interfaceName] of Object.entries(schemaToInterface)) {
  const schema = schemas[schemaName];
  if (!schema) {
    failures.push(`OpenAPI schema missing: ${schemaName}`);
    continue;
  }

  const apiProperties = schema.properties ?? {};
  const required = new Set(schema.required ?? []);
  const tsProperties = collectInterfaceProperties(interfaceName);
  const apiNames = Object.keys(apiProperties).sort();
  const tsNames = [...tsProperties.keys()].sort();

  if (JSON.stringify(apiNames) !== JSON.stringify(tsNames)) {
    failures.push(`${schemaName}/${interfaceName} property set differs: OpenAPI=${apiNames} TypeScript=${tsNames}`);
    continue;
  }

  for (const name of apiNames) {
    const tsProperty = tsProperties.get(name);
    const apiRequired = required.has(name);
    const tsRequired = !tsProperty.questionToken;
    if (apiRequired !== tsRequired) {
      failures.push(`${schemaName}.${name} required=${apiRequired}, TypeScript required=${tsRequired}`);
    }

    const apiAllowsNull = openApiNullable(apiProperties[name]);
    const tsAllowsNull = typeScriptNullable(tsProperty.type);
    if (apiAllowsNull !== tsAllowsNull) {
      failures.push(`${schemaName}.${name} nullable=${apiAllowsNull}, TypeScript nullable=${tsAllowsNull}`);
    }
  }
}

if (failures.length > 0) {
  console.error("OpenAPI / TypeScript contract drift detected:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(
  `OPENAPI_CLIENT_PARITY_OK schemas=${Object.keys(schemaToInterface).length} python=${pythonExecutable}`
);
