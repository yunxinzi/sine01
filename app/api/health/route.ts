import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    ok: true,
    app: "sine01",
    version: "0.1.0",
    capabilities: {
      interactiveWorkflow: true,
      localPersistence: true,
      projectJsonExport: true,
      printablePreview: true,
      aiProvider: false,
      editablePptx: false,
      rebuildQa: false
    }
  });
}
