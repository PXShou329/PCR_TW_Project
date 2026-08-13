import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const clientPath = process.env.PCR_API_CLIENT_TYPES
  ? resolve(process.env.PCR_API_CLIENT_TYPES)
  : join(root, "packages", "api-client", "src", "types.ts");

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
  "sys.path[:0]=['apps/api','data_pipeline','database']",
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
const typeAliasNodes = new Map();
for (const statement of sourceFile.statements) {
  if (ts.isInterfaceDeclaration(statement)) interfaceNodes.set(statement.name.text, statement);
  if (ts.isTypeAliasDeclaration(statement)) typeAliasNodes.set(statement.name.text, statement);
}

const schemaToInterface = {
  BaselineCounts: "BaselineCounts",
  BaselineData: "Baseline",
  ClaimData: "Claim",
  EvidenceData: "Evidence",
  GachaCommunitySourceData: "GachaCommunitySource",
  GachaTimelineEventData: "GachaTimelineEvent",
  ArenaCounterData: "PvpCounter",
  ArenaMemberData: "ArenaMember",
  PvpCharacterData: "PvpCharacter",
  ParenaEnvironmentData: "ParenaEnvironment",
  ParenaSolveRequest: "ParenaSolveRequest",
  ArenaSourceRecordData: "ArenaSourceRecord",
  ParenaMatchupData: "ParenaMatchup",
  ParenaCaseData: "ParenaCase",
  ParenaSolveData: "ParenaSolveData",
  ResponseMeta: "ApiMetadata",
  SourceMeta: "SourceMetadata",
  StageCoverage: "Coverage",
  StageDetail: "StageDetail",
  StageSummary: "StageSummary",
  TeamDetail: "TeamDetail",
  TeamMemberData: "TeamMember",
  TeamSummary: "TeamSummary",
  SlotRequirementData: "SlotRequirement",
  SlotRequirementsData: "SlotRequirements",
  TeamSupportData: "TeamSupport",
  OperationModeClaimData: "OperationModeClaim",
  TeamRequirementsData: "TeamRequirements",
  TimelineData: "TeamTimeline",
  TimelineReference: "TimelineReference",
  TimelineStepData: "TimelineStep",
  StructuredTimelineSource: "StructuredTimelineSource",
  GapTimelineSource: "GapTimelineSource",
  GateSummary: "GateSummary",
  PveLibrarySourceWorkbook: "PveLibrarySourceWorkbook",
  PveLibraryMeta: "PveLibraryMeta",
  PveStageRef: "PveStageRef",
  PveProvenance: "PveProvenance",
  PveStageSummary: "PveStageSummary",
  PveOperationVariant: "PveOperationVariant",
  PveOperation: "PveOperation",
  PveAxis: "PveAxis",
  PvePortrait: "PvePortrait",
  PveTeam: "PveTeam",
  PveStageDetail: "PveStageDetail",
};
const interfaceToSchema = new Map(
  Object.entries(schemaToInterface).map(([schemaName, interfaceName]) => [interfaceName, schemaName])
);

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

function serializedShape(shape) {
  return JSON.stringify(shape);
}

function unionShape(shapes) {
  const flattened = [];
  for (const shape of shapes) {
    if (shape.kind === "union") flattened.push(...shape.options);
    else flattened.push(shape);
  }
  const unique = new Map(flattened.map((shape) => [serializedShape(shape), shape]));
  const options = [...unique.values()].sort((left, right) =>
    serializedShape(left).localeCompare(serializedShape(right))
  );
  if (options.length === 0) return { kind: "never" };
  if (options.length === 1) return options[0];
  return { kind: "union", options };
}

function withoutNull(shape) {
  if (shape.kind === "null") return { kind: "never" };
  if (shape.kind !== "union") return shape;
  return unionShape(shape.options.filter((option) => option.kind !== "null"));
}

function openApiShape(property) {
  if (property.$ref) {
    return { kind: "ref", name: property.$ref.split("/").at(-1) };
  }
  const alternatives = property.anyOf ?? property.oneOf;
  if (alternatives) return unionShape(alternatives.map(openApiShape));
  if (Object.hasOwn(property, "const")) return { kind: "literal", value: property.const };
  if (Array.isArray(property.enum)) {
    return unionShape(property.enum.map((value) => ({ kind: "literal", value })));
  }
  if (property.type === "null") return { kind: "null" };
  if (property.type === "array") {
    if (property.maxItems === 0) return { kind: "empty-array" };
    return { kind: "array", item: openApiShape(property.items ?? {}) };
  }
  if (property.type === "integer" || property.type === "number") return { kind: "number" };
  if (property.type === "string") return { kind: "string" };
  if (property.type === "boolean") return { kind: "boolean" };
  if (property.type === "object" || property.properties || property.additionalProperties) {
    return { kind: "object" };
  }
  return { kind: "unknown" };
}

function typeName(typeNode) {
  if (ts.isIdentifier(typeNode)) return typeNode.text;
  return typeNode.getText(sourceFile);
}

function typeScriptShape(typeNode, resolving = new Set()) {
  if (ts.isParenthesizedTypeNode(typeNode)) return typeScriptShape(typeNode.type, resolving);
  if (ts.isUnionTypeNode(typeNode)) {
    return unionShape(typeNode.types.map((part) => typeScriptShape(part, resolving)));
  }
  if (ts.isArrayTypeNode(typeNode)) {
    return { kind: "array", item: typeScriptShape(typeNode.elementType, resolving) };
  }
  if (ts.isTupleTypeNode(typeNode)) {
    if (typeNode.elements.length === 0) return { kind: "empty-array" };
    return { kind: "tuple", items: typeNode.elements.map((part) => typeScriptShape(part, resolving)) };
  }
  if (ts.isLiteralTypeNode(typeNode)) {
    if (typeNode.literal.kind === ts.SyntaxKind.NullKeyword) return { kind: "null" };
    if (ts.isStringLiteral(typeNode.literal) || ts.isNumericLiteral(typeNode.literal)) {
      return {
        kind: "literal",
        value: ts.isNumericLiteral(typeNode.literal) ? Number(typeNode.literal.text) : typeNode.literal.text,
      };
    }
    if (typeNode.literal.kind === ts.SyntaxKind.TrueKeyword) return { kind: "literal", value: true };
    if (typeNode.literal.kind === ts.SyntaxKind.FalseKeyword) return { kind: "literal", value: false };
  }
  if (ts.isTypeLiteralNode(typeNode)) return { kind: "object" };
  if (ts.isTypeReferenceNode(typeNode)) {
    const name = typeName(typeNode.typeName);
    const arguments_ = typeNode.typeArguments ?? [];
    if ((name === "Array" || name === "ReadonlyArray") && arguments_.length === 1) {
      return { kind: "array", item: typeScriptShape(arguments_[0], resolving) };
    }
    if (name === "Record") return { kind: "object" };
    if (name === "Exclude" && arguments_.length === 2) {
      const source = withoutNull(typeScriptShape(arguments_[0], resolving));
      const excluded = withoutNull(typeScriptShape(arguments_[1], resolving));
      const sourceOptions = source.kind === "union" ? source.options : [source];
      const excludedKeys = new Set(
        (excluded.kind === "union" ? excluded.options : [excluded]).map(serializedShape)
      );
      return unionShape(sourceOptions.filter((option) => !excludedKeys.has(serializedShape(option))));
    }
    const alias = typeAliasNodes.get(name);
    if (alias) {
      if (resolving.has(name)) throw new Error(`Recursive TypeScript alias: ${name}`);
      const next = new Set(resolving);
      next.add(name);
      return typeScriptShape(alias.type, next);
    }
    return { kind: "ref", name: interfaceToSchema.get(name) ?? name };
  }
  if (typeNode.kind === ts.SyntaxKind.StringKeyword) return { kind: "string" };
  if (typeNode.kind === ts.SyntaxKind.NumberKeyword) return { kind: "number" };
  if (typeNode.kind === ts.SyntaxKind.BooleanKeyword) return { kind: "boolean" };
  if (typeNode.kind === ts.SyntaxKind.NullKeyword) return { kind: "null" };
  if (typeNode.kind === ts.SyntaxKind.AnyKeyword || typeNode.kind === ts.SyntaxKind.UnknownKeyword) {
    return { kind: "unknown" };
  }
  return { kind: "unsupported", syntax: typeNode.getText(sourceFile) };
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

    const apiShape = withoutNull(openApiShape(apiProperties[name]));
    const tsShape = withoutNull(typeScriptShape(tsProperty.type));
    if (serializedShape(apiShape) !== serializedShape(tsShape)) {
      failures.push(
        `${schemaName}.${name} type differs: OpenAPI=${serializedShape(apiShape)} TypeScript=${serializedShape(tsShape)}`
      );
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
